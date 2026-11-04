"""Generate reviewed local Online Solver service plans; never start processes."""
from __future__ import annotations

import math
import os
from pathlib import Path
from urllib.parse import urlsplit

from .layout import load
from .solver_capacity import plan_solver_capacity, solver_task_spec
from .solver_recipes import solver_public_image_map

REQUIRED_ENVIRONMENT = ('TCSEXAM_TOKEN_ID', 'TCSEXAM_TOKEN_SECRET', 'TCSEXAM_ARCHIVE_TOKEN')


def require_backend_environment(environ=None):
    """Fail before serving if any environment-only credential is unavailable."""
    environ = os.environ if environ is None else environ
    missing = [name for name in REQUIRED_ENVIRONMENT if not str(environ.get(name, '')).strip()]
    if missing:
        raise ValueError('Backend credentials must be supplied through the environment: ' + ', '.join(missing))


def plan_docker_backend(root, online_rows, product_references, *, available_cpu_count,
                        available_memory_mb, capacity_evidence, public_base_url,
                        client_base_url=None, port=8420,
                        state_dir='/tmp/tcsexam-local-backend',
                        docker_socket='/var/run/docker.sock', storage_mb='standard'):
    """Return a YAML-ready config and public/final client plans for selected tasks.

    Host capacities must already intersect daemon, cgroup and CPU-affinity
    limits, and deduct controller reservations. This function deliberately does
    not inspect a bare daemon NCPU/MemTotal or silently assume those are usable.

    The service admits exactly one live session. Generated public clients close
    their session after every self-test; final clients release their own declared
    public sessions before final judging. Archives and accounting are retained.
    Launchers must also use the returned one-trial-at-a-time execution policy.
    """
    root = Path(root).resolve()
    rows = list(online_rows)
    if not rows:
        raise ValueError('Select at least one Online Solver task')
    if not isinstance(capacity_evidence, dict) or not capacity_evidence:
        raise ValueError('Effective host/cgroup capacity evidence is required')
    if not capacity_evidence.get('effective_limits_verified'):
        raise ValueError('Host capacity must be verified against effective cgroup/affinity limits')
    for row in rows:
        if row.get('track') != 'solver' or row.get('variant') != 'online':
            raise ValueError('Backend preparation accepts selected Online Solver rows only')
    tasks = {row['id'] for row in rows}
    if len(tasks) != len(rows):
        raise ValueError('Duplicate Online Solver task')
    parsed = urlsplit(public_base_url)
    if (parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'','/'}):
        raise ValueError('Use a worker-reachable backend HTTP(S) origin without credentials')
    if parsed.hostname in {'localhost','127.0.0.1','::1'}:
        raise ValueError('Docker bridge workers cannot reconnect to the host through container loopback')
    if not Path(state_dir).is_absolute() or not Path(docker_socket).is_absolute():
        raise ValueError('Backend state and Docker socket paths must be absolute')
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError('Invalid backend port')
    document = load(root/'assets/images.json')
    refs = {identity:(value.get('reference') or value.get('image') if isinstance(value,dict) else value)
            for identity,value in product_references.items()}
    image_map = solver_public_image_map(root, document, refs, tasks=tasks)
    indexed = {row['id']:row for row in document['images'] if row.get('id')}
    def product(task, role):
        matches=[row['id'] for row in indexed.values() if row.get('runtime_role') == role
                 and f'tasks/solver/online/{task}' in row.get('consumers',[])]
        if len(matches) != 1:
            raise ValueError(f'Expected one {role} image for {task}')
        return matches[0]
    task_plans = {}
    routes = []
    all_plans = []
    disks = set()
    for task in sorted(tasks):
        splits = {}
        hidden_ref = refs[product(task,'backend')]
        for split in ('public','hidden'):
            spec = solver_task_spec(root, task, split)
            unit = spec['scoring_unit']
            disk = unit['storage_mb'] if storage_mb == 'standard' else storage_mb
            if disk is not None and (isinstance(disk,bool) or not isinstance(disk,int) or disk < 1):
                raise ValueError('storage_mb must be standard, positive integer MiB, or explicit None')
            disks.add(disk)
            planned = plan_solver_capacity(
                standard_shards=spec['standard_shards'], worker_cpu_count=unit['cpu_count'],
                worker_memory_mb=unit['memory_mb'], available_cpu_count=available_cpu_count,
                available_memory_mb=available_memory_mb, instance_count=spec['instance_count'],
                per_instance_seconds=spec['per_instance_seconds'], pool=spec['pool'],
                total_pool_seconds=spec['total_pool_seconds'], build_seconds=spec['build_seconds'],
                check_seconds=spec['check_seconds'],
                baked_judge_timeout_seconds=spec['baked_judge_timeout_seconds'])
            if planned['requires_image_timeout_update']:
                raise ValueError(f'Prepared {task}/{split} worker JUDGE_TIMEOUT is too short; rebuild its image')
            timing = planned['timeouts']
            env = {'TCSEXAM_JUDGE_IMAGE':hidden_ref,
                   'TCSEXAM_N_SHARDS':str(planned['effective']['shards']),
                   'TCSEXAM_WORKER_CPUS':str(unit['cpu_count']),
                   'TCSEXAM_WORKER_MEMORY_MB':str(unit['memory_mb']),
                   'TCSEXAM_WORKER_STORAGE_MB':'null' if disk is None else str(disk),
                   'TCSEXAM_SESSION_TTL':str(timing['worker_ttl_seconds']),
                   'TCSEXAM_POLL_TIMEOUT':str(timing['poll_timeout_seconds']),
                   'TCSEXAM_CLOSE_SESSION_AFTER_SUBMIT':'1',
                   'TCSEXAM_CLOSE_AGENT_SESSIONS':'1'}
            if client_base_url:
                env['TCSEXAM_BASE_URL'] = client_base_url
            planned['standard']['legacy_container_request'] = spec['legacy_container_request']
            planned['standard']['storage_mb'] = unit['storage_mb']
            planned['requested']['storage_mb'] = disk
            planned['effective']['storage_mb'] = disk
            planned['enforcement']['storage'] = 'explicitly_disabled' if disk is None else 'required_docker_quota'
            role = 'public_backend' if split == 'public' else 'backend'
            reference = refs[product(task,role)]
            routes.append({'match':{'image_contains':reference},
                           'ready_timeout_seconds':timing['ready_timeout_seconds'],
                           'create_ready_timeout_seconds':timing['ready_timeout_seconds'],
                           'ttl_seconds':timing['worker_ttl_seconds'],
                           'idle_ttl_seconds':timing['worker_ttl_seconds']})
            splits[split] = {'env':env, 'plan':planned, 'source':spec,
                             'effective_worker_image':reference,
                             'verifier_timeout_seconds':timing['verifier_timeout_seconds']}
            all_plans.append(planned)
        task_plans[task] = splits
    positive_disks = [disk for disk in disks if disk is not None]
    fallback_disk = min(positive_disks) if positive_disks else None
    largest_ttl=max(p['timeouts']['worker_ttl_seconds'] for p in all_plans)
    largest_read=max(p['timeouts']['poll_timeout_seconds'] for p in all_plans)
    max_shards=max(p['effective']['shards'] for p in all_plans)
    maximum_cpu=max(p['effective']['worker_resources']['cpu_count'] for p in all_plans)
    maximum_memory=max(p['effective']['worker_resources']['memory_mb'] for p in all_plans)
    config = {'host':'0.0.0.0', 'port':port, 'public_base_url':public_base_url.rstrip('/'),
              'state_dir':state_dir, 'adapter':'docker', 'docker_socket':docker_socket,
              'docker_network':'bridge', 'docker_host_gateway':True,
              'docker_pull_missing_images':False,
              'auth':{'run_id_mode':'required', 'require_environment_credentials':True},
              'public_image_map':image_map,
              'backend':{'create_retries':0, 'create_concurrency':max_shards,
                         'session_create_concurrency':max_shards,
                         'max_sandboxes_global':max_shards,
                         'max_sandbox_memory_mb':available_memory_mb,
                         'ready_timeout_seconds':600,
                         'judge_sessions':{'max_sessions':1, 'profile':'docker',
                            'spec':{'cpu_count':maximum_cpu, 'memory_mb':maximum_memory,
                                    'storage_mb':fallback_disk},
                            'max_shards':max_shards,
                            'max_session_cpu_count':math.floor(available_cpu_count),
                            'max_session_memory_mb':available_memory_mb,
                            'ttl_seconds':largest_ttl, 'max_ttl_seconds':largest_ttl,
                            'idle_ttl_seconds':largest_ttl,
                            'read_timeout_seconds':largest_read,
                            'ready_timeout_seconds':600,
                            'hibernate_enabled':False,
                            'min_ready_ratio':1.0, 'routes':routes}}}
    return {'format_version':1, 'config':config, 'tasks':task_plans,
            'capacity_evidence':dict(capacity_evidence),
            'required_environment':list(REQUIRED_ENVIRONMENT),
            'startup_precondition':'tcsexam.backend_setup.require_backend_environment',
            'scheduling':{'max_live_sessions':1,'max_concurrent_trials':1,
                          'public_session_cleanup':'after_each_self_test',
                          'final_session_cleanup':'existing_finally_and_declared_public_cleanup'},
            'model_started':False, 'service_started':False}


def backend_yaml(plan):
    """Serialize only nonsecret configuration. Credential values are never read."""
    import yaml
    return '# Set TCSEXAM_TOKEN_ID, TCSEXAM_TOKEN_SECRET and TCSEXAM_ARCHIVE_TOKEN in the service environment.\n' + yaml.safe_dump(plan['config'], sort_keys=False)
