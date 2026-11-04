"""Materialize Harbor task attempts without modifying source packages."""
import os
import shutil
from urllib.parse import urlsplit
from uuid import uuid4

from .layout import load, within
from .setup import image_map, resolved_images
from .agent_config import INSTALL_HOSTS, selected_agent


BACKEND_KEYS = ('TCSEXAM_TOKEN_ID', 'TCSEXAM_TOKEN_SECRET', 'TCSEXAM_BASE_URL')

KIMI_INSTALL_HOSTS = INSTALL_HOSTS['kimi-code']


def prepare_agent_install_network(data, agent='kimi-code'):
    """Allow the selected installer while retaining original phase policies."""
    from harbor.models.task.config import TaskConfig
    from harbor.models.task.verifier_mode import resolve_task_verifier_mode
    from harbor.models.trial.config import AgentConfig, EnvironmentConfig
    from harbor.trial.network_policy import resolve_trial_network_plan
    original = TaskConfig.model_validate(data)
    plan = resolve_trial_network_plan(original, AgentConfig(name=agent),
        EnvironmentConfig(type='docker'), None, verifier_mode=resolve_task_verifier_mode(original))
    for phase, policy in (('agent', plan.agent_phase), ('verifier', plan.verifier_phase)):
        config = data.setdefault(phase, {})
        config['network_mode'] = policy.network_mode.value
        if policy.allowed_hosts:
            config['allowed_hosts'] = list(policy.allowed_hosts)
        else:
            config.pop('allowed_hosts', None)
    data['environment']['network_mode'] = 'allowlist'
    data['environment']['allowed_hosts'] = list(INSTALL_HOSTS[agent])


def http_host(url):
    p = urlsplit(url)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError('Use an HTTP(S) base URL without credentials, query or fragment')
    return p.hostname


def native_config(data):
    # Import lazily: listing and score aggregation do not need Harbor.
    from harbor.models.task.config import TaskConfig
    import toml
    # Reject misspelled top-level/phase keys, which pydantic normally ignores.
    for key in data:
        if key not in TaskConfig.model_fields:
            raise ValueError(f'Unknown Harbor task field: {key}')
    result = TaskConfig.model_validate(data)
    for phase in ('agent', 'verifier', 'environment'):
        config = getattr(result, phase)
        unknown = set(data.get(phase, {})) - set(type(config).model_fields)
        if unknown:
            raise ValueError(f'Unknown Harbor {phase} field: {sorted(unknown)}')
    return toml.dumps(data), result


def resource_image_ids(root, row, images):
    consumers = {row['path']}
    adapter = within(root, row['path']) / 'offline-adapter.json'
    if adapter.is_file():
        origin = load(adapter)['online_source']
        within(root, origin)
        consumers.add(origin)
    return sorted({image['id'] for image in images if image.get('type') == 'data'
                   and consumers.intersection(image.get('consumers', []))})


def materialize(root, rows, args):
    import tomllib
    from .backend_cli import client_plan
    planned_backend = client_plan(root, rows, args)
    images, image_evidence = resolved_images(root, rows, args)
    declared_images = load(root / 'assets/images.json')['images']
    generation = uuid4().hex
    staging = args.output.resolve().parent / ('tasks-' + generation)
    staging.mkdir(parents=True, exist_ok=False)
    tasks, provenance = [], []
    backend = getattr(args, 'judge_url', None) or os.environ.get('TCSEXAM_BASE_URL')
    host = http_host(backend) if backend else None
    for attempt in range(args.attempts):
        for row in rows:
            run_id = 'tcsexam-' + uuid4().hex
            source = within(root, row['path'])
            destination = staging / (row['id'] + '-' + run_id[-16:])
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'archive_token'))
            data = tomllib.loads((source / 'task.toml').read_text())
            original_verifier_timeout = data['verifier']['timeout_sec']
            standard_timing = None
            overrides = images.get(row['path'], {})
            if 'development' in overrides:
                data['environment']['docker_image'] = overrides['development']
            if 'verifier' in overrides:
                data['verifier'].setdefault('environment', {})['docker_image'] = overrides['verifier']
            if row['variant'] == 'online':
                env = data['environment'].setdefault('env', {})
                for key, value in list(env.items()):
                    if key not in BACKEND_KEYS and value == '${' + key + '}':
                        env[key] = '${' + key + ':-}'
                env.update({key: '${' + key + '}' for key in BACKEND_KEYS})
                env['TCSEXAM_RUN_ID'] = run_id
                if backend:
                    env['TCSEXAM_BASE_URL'] = backend
                final = data['verifier'].setdefault('env', {})
                final.update({key: env[key] for key in BACKEND_KEYS})
                final['TCSEXAM_RUN_ID'] = run_id
                final['TCSEXAM_ARCHIVE_TOKEN'] = '${TCSEXAM_ARCHIVE_TOKEN}'
                if 'backend' in overrides:
                    env['TCSEXAM_JUDGE_IMAGE'] = overrides['backend']
                    final['TCSEXAM_JUDGE_IMAGE'] = overrides['backend']
                if planned_backend:
                    resource_plan = planned_backend['tasks'][row['id']]
                    allowed = {'TCSEXAM_JUDGE_IMAGE', 'TCSEXAM_N_SHARDS', 'TCSEXAM_WORKER_CPUS',
                               'TCSEXAM_WORKER_MEMORY_MB', 'TCSEXAM_WORKER_STORAGE_MB',
                               'TCSEXAM_SESSION_TTL', 'TCSEXAM_POLL_TIMEOUT',
                               'TCSEXAM_CLOSE_SESSION_AFTER_SUBMIT', 'TCSEXAM_CLOSE_AGENT_SESSIONS',
                               'TCSEXAM_BASE_URL'}
                    for split, target in (('public', env), ('hidden', final)):
                        values = resource_plan[split]['env']
                        if set(values) - allowed:
                            raise ValueError('Unexpected environment fields in the backend resource plan')
                        target.update(values)
                    required_timeout = resource_plan['hidden']['verifier_timeout_seconds']
                    if not isinstance(required_timeout, int) or required_timeout <= 0:
                        raise ValueError('Backend plan has an invalid verifier lifecycle timeout')
                    data['verifier']['timeout_sec'] = max(original_verifier_timeout, required_timeout)
                else:
                    from .solver_capacity import standard_client_timing
                    standard_timing = {split: standard_client_timing(root, row['id'], split)
                                       for split in ('public', 'hidden')}
                    env.update(standard_timing['public']['env'])
                    final.update(standard_timing['hidden']['env'])
                    data['verifier']['timeout_sec'] = max(
                        original_verifier_timeout, standard_timing['hidden']['verifier_timeout_seconds'])
                for phase in ('agent', 'verifier'):
                    phase_config = data[phase]
                    if host:
                        phase_config['network_mode'] = 'allowlist'
                        phase_config['allowed_hosts'] = sorted(set(phase_config.get('allowed_hosts', []) + [host]))
            prepare_agent_install_network(data, selected_agent(args))
            rendered, parsed = native_config(data)
            if parsed.agent.timeout_sec != 43200 or '/app' not in parsed.artifacts:
                raise ValueError('Generated task lost budget or artifact preservation')
            (destination / 'task.toml').write_text(rendered)
            tasks.append({'path': str(destination), 'source': f"tcsexam-{args.suite}-{row['variant']}"})
            provenance.append({'original_task_path': row['path'], 'task': row['id'], 'protocol': row['variant'],
                               'attempt': attempt+1, 'run_id': run_id, 'runtime_path': str(destination),
                               'development_image': data['environment'].get('docker_image'),
                               'verifier_image': data['verifier'].get('environment', {}).get('docker_image'),
                               'backend_image': overrides.get('backend'),
                               'original_verifier_timeout_sec': original_verifier_timeout,
                               'effective_verifier_timeout_sec': parsed.verifier.timeout_sec,
                               'standard_client_timing': standard_timing,
                               'resource_plan': planned_backend['tasks'][row['id']] if planned_backend and row['variant'] == 'online' else None,
                               'data_images': resource_image_ids(root, row, declared_images)})
    return tasks, provenance
