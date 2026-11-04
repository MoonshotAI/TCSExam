"""Resolve complete runtime images and prepare the selected Docker host."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib

from .layout import load, require_paths, within

ROLES = ('development', 'verifier', 'backend')
PIN = re.compile(r'[^\s<>]+@sha256:[0-9a-f]{64}')
IMAGE_ID = re.compile(r'sha256:[0-9a-f]{64}')
LOCAL_ID = re.compile(r'[a-z0-9][a-z0-9_.-]*')


def local_reference(row, ref):
    if not isinstance(row, dict) or row.get('local') is not True:
        return False
    identity = row.get('id', '')
    signature = row.get('build_signature', '')
    return (LOCAL_ID.fullmatch(identity) and IMAGE_ID.fullmatch(row.get('image_id', ''))
            and IMAGE_ID.fullmatch(signature)
            and ref == f'tcsexam/{identity}:{signature[7:23]}')


def image_map(path):
    data = load(path) if path else {}
    if not isinstance(data, dict):
        raise ValueError('Image map must contain task paths and image roles')
    for task, roles in data.items():
        if not isinstance(roles, dict):
            raise ValueError(f'Invalid image roles: {task}')
        for role, value in roles.items():
            if role not in ROLES:
                raise ValueError(f'Unknown image role: {role}')
            if not isinstance(value, str) or not PIN.fullmatch(value):
                raise ValueError(f'Pin {task}/{role} to an image digest')
    return data


def artifacts(path, root=None):
    """Read published image pins or records produced by the local builder."""
    if not path:
        return {}, {}
    data = load(path)
    records = data.get('images', data.get('artifacts', []))
    if isinstance(records, dict):
        records = [dict(value, id=key) for key, value in records.items()]
    if root is not None and any(row.get('local') for row in records):
        from .build import validate_manifest
        validate_manifest(root, data)
    by_id, evidence, mapping = {}, {}, {}
    for row in records:
        ref = row.get('reference') or row.get('image') or row.get('destination')
        if row.get('local'):
            if not local_reference(row, ref):
                raise ValueError(f'Invalid local build record: {row.get("id", "unnamed")}')
        else:
            digest = row.get('image_digest') or row.get('manifest_digest') or row.get('digest')
            if ref and digest and '@' not in ref:
                repository = ref.rsplit(':', 1)[0] if ref.rfind(':') > ref.rfind('/') else ref
                ref = repository + '@' + digest
            if not ref or not PIN.fullmatch(ref):
                raise ValueError(f'Artifact has no pinned image: {row.get("id", "unnamed")}')
            if digest and ref.split('@', 1)[1] != digest:
                raise ValueError(f'Artifact digest conflicts with reference: {row.get("id")}')
        if row.get('id'):
            if row['id'] in by_id and by_id[row['id']] != ref:
                raise ValueError(f'Duplicate artifact identity: {row["id"]}')
            by_id[row['id']] = ref
        evidence[ref] = {**row, 'image': ref, 'reference': ref}
        if row.get('task') and row.get('role') in ROLES:
            previous = mapping.get(row['task'], {}).get(row['role'])
            if previous and previous != ref:
                raise ValueError(f'Conflicting task image: {row["task"]}/{row["role"]}')
            mapping.setdefault(row['task'], {})[row['role']] = ref
    assignments = data.get('image_map', data.get('tasks', {}))
    if isinstance(assignments, str):
        assignments = load(Path(path).parent / assignments)
    for task, roles in assignments.items():
        for role, identity in roles.items():
            value = identity.get('image') if isinstance(identity, dict) else identity
            mapping.setdefault(task, {})[role] = by_id.get(value, value)
    for task, roles in mapping.items():
        for role, ref in roles.items():
            if (role not in ROLES or not isinstance(ref, str)
                    or not (PIN.fullmatch(ref) or local_reference(evidence.get(ref), ref))):
                raise ValueError(f'Invalid artifact assignment: {task}/{role}')
    return mapping, evidence


def resolved_images(root, rows, args):
    mapping, evidence = artifacts(getattr(args, 'artifacts', None), root=root)
    explicit = image_map(getattr(args, 'image_map', None))
    for task, roles in explicit.items():
        mapping.setdefault(task, {}).update(roles)
    declared = load(root / 'assets/images.json')['images']
    for row in rows:
        if not row['path']:
            continue
        data = tomllib.loads((within(root, row['path']) / 'task.toml').read_text())
        roles = mapping.setdefault(row['path'], {})
        defaults = {
            'development': data['environment'].get('docker_image'),
            'verifier': data['verifier'].get('environment', {}).get('docker_image'),
        }
        for record in declared:
            ref = record.get('public_image') or record.get('replacement')
            role = record.get('runtime_role')
            if row['path'] in record.get('consumers', []) and role in ROLES and ref:
                defaults[role] = ref
                evidence.setdefault(ref, record)
        for role, ref in defaults.items():
            if role not in roles and ref:
                roles[role] = ref
    return mapping, evidence


def required_image_roles(root, row):
    """Require a compiled image for each container Harbor will create."""
    data = tomllib.loads((within(root, row['path']) / 'task.toml').read_text())
    verifier = data.get('verifier', {})
    mode = verifier.get('environment_mode')
    separate = mode == 'separate' or (mode is None and verifier.get('environment') is not None)
    return ('development', 'verifier') if separate else ('development',)


def docker_command(args):
    command = ['docker']
    context = getattr(args, 'docker_context', None)
    if context:
        command += ['--context', context]
    return command


def upstream_matches(image, record, ref):
    if not PIN.fullmatch(ref) or record.get('upstream_manifest_digest') != ref.split('@', 1)[1]:
        return False
    expected = record.get('upstream_config')
    if not isinstance(expected, dict) or not IMAGE_ID.fullmatch(record.get('image_id', '')):
        return False
    if image['Id'] != record['image_id'] or image['RootFS']['Layers'] != expected['rootfs']['diff_ids']:
        return False
    if image['Os'] != expected['os'] or image['Architecture'] != expected['architecture']:
        return False
    config = expected.get('config', {})
    if not isinstance(config, dict):
        return False
    ignored = {'Hostname', 'Domainname', 'Image'}
    for key in (set(config) | set(image['Config'])) - ignored:
        if image['Config'].get(key) != config.get(key):
            return False
    return True


def inspect_image(ref, args, record=None):
    source = record.get('local_image') if record and record.get('side_loaded') else ref
    try:
        result = subprocess.run(docker_command(args) + ['image', 'inspect', source],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    try:
        image = json.loads(result.stdout)[0]
        if record and record.get('side_loaded'):
            if not upstream_matches(image, record, ref):
                return None
        elif record and record.get('local'):
            if not local_reference(record, ref) or image['Id'] != record['image_id']:
                return None
        else:
            if not PIN.fullmatch(ref):
                return None
            expected = ref.split('@', 1)[1]
            if not any(r.endswith('@' + expected) for r in image.get('RepoDigests', [])):
                return None
        return {'id': image['Id'], 'platform': image['Os'] + '/' + image['Architecture'],
                'reference': ref}
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def cache_path(args):
    configured = getattr(args, 'cache', None)
    if configured is None:
        configured = os.environ.get('TCSEXAM_CACHE', '').strip() or '~/.cache/tcsexam'
    return Path(configured).expanduser()


def inspect_tag_id(tag, args):
    try:
        result = subprocess.run(docker_command(args) + ['image', 'inspect', '--format', '{{.Id}}', tag],
                                capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def save_record(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            json.dump(value, f, indent=2, ensure_ascii=False)
            f.write('\n')
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def host_support_targets(evidence, args=None):
    """Match prebuilt Harbor support images to the installed package context."""
    support = [r for r in evidence.values() if r.get('type') == 'host_support']
    if not support:
        raise ValueError('The product manifest must include the prebuilt Harbor helper and kernel probe; '
                         '--image-map alone does not prepare Harbor host support')
    context = getattr(args, 'docker_context', None) or os.environ.get('DOCKER_CONTEXT')
    endpoint = os.environ.get('DOCKER_HOST') if not context else None
    if not endpoint:
        command = docker_command(args) + ['context', 'inspect']
        if context:
            command += [context]
        try:
            inspected = subprocess.run(command + ['--format', '{{.Endpoints.docker.Host}}'],
                                       capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError('Cannot inspect the execution Docker context') from exc
        endpoint = inspected.stdout.strip() if inspected.returncode == 0 else None
    if not endpoint or not endpoint.startswith('unix://'):
        raise ValueError('Run the CLI on the Docker execution host using its local Unix socket; '
                         'remote SSH/TCP contexts do not provide Harbor shared filesystem paths')
    try:
        daemon = subprocess.run(docker_command(args) + ['version', '--format', '{{.Server.Os}}/{{.Server.Arch}}'],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('Cannot determine the execution Docker host platform') from exc
    if daemon.returncode or daemon.stdout.strip() != 'linux/amd64':
        raise ValueError('Prepared Harbor host support requires a linux/amd64 Docker host')
    from harbor.environments.docker.docker import DockerEnvironment
    from .harbor_support import normalized_context
    helper_context, key = normalized_context(cache_path(args))
    DockerEnvironment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH = helper_context
    helpers = [r for r in support if r.get('support_kind') == 'harbor_egress_control'
               and r.get('harbor_context_hash') == key]
    if not helpers:
        raise ValueError('No prebuilt Harbor helper matches this package context: ' + key)
    probes = [r for r in support if r.get('support_kind') == 'harbor_kernel_probe'
              and (r.get('image') or r.get('reference')) == DockerEnvironment._EGRESS_CONTROL_KERNEL_PROBE_IMAGE]
    if not probes:
        raise ValueError("The product manifest lacks Harbor fixed kernel-probe image")
    return [dict(helpers[0], local_tag=DockerEnvironment._EGRESS_CONTROL_SIDECAR_DOCKER_NAME+'--'+key),
            probes[0]]


def offline_host_capacity(root, rows, mapping, args):
    """Check original resource minima before an offline agent can start.

    The read-only probe uses the same cgroup discovery as judging. Docker's
    reported CPU count alone can exceed a nested execution host's actual quota.
    No submission, worker or Docker socket is passed to the probe.
    """
    offline = [row for row in rows if row.get('path') and row['variant'] == 'offline']
    if not offline:
        return []
    probe = mapping.get(offline[0]['path'], {}).get('verifier')
    if not probe:
        raise ValueError('Offline resource checks require a complete verifier image')
    program = ('import json,sys;sys.path.insert(0,"/opt/public_judge");'
               'from admission import daemon_capacity;'
               'print(json.dumps(daemon_capacity().json()))')
    command = docker_command(args) + [
        'run', '--rm', '--pull=never', '--network', 'none', '--pid', 'host',
        '--cgroupns', 'host', '--mount',
        'type=bind,src=/sys/fs/cgroup,dst=/host-cgroup,readonly',
        '--entrypoint', 'python3', probe, '-c', program]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise ValueError('Offline capacity probe failed; run on a Linux Docker host '
                             'with visible process and cgroup limits')
        capacity = json.loads(result.stdout)
        cpu = int(capacity['cpu_count'])
        memory = int(capacity['memory_bytes']) // (1024**2)
        disk = int(capacity['disk_free_bytes']) // (1024**2)
    except (OSError, subprocess.TimeoutExpired, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Cannot verify offline execution-host capacity') from exc
    checks = []
    for row in offline:
        task = within(root, row['path'])
        config = load(task/'tests/runtime/task.json')
        development = tomllib.loads((task/'task.toml').read_text())['environment']
        minimum = {
            'cpus': max(int(development.get('cpus', 1)), int(config['cpus']) + 1),
            'memory_mb': max(int(development.get('memory_mb', 0)), int(config['memory_mb']) + 512),
            'free_disk_mb': int(config['disk_mb']) + 2048,
        }
        available = {'cpus': cpu, 'memory_mb': memory, 'free_disk_mb': disk}
        ok = all(available[key] >= value for key, value in minimum.items())
        check = {'task': row['path'], 'kind': 'offline_host_capacity', 'ok': ok,
                 'minimum': minimum, 'available': available,
                 'reason': 'Original development limits and one judging worker plus controller reserve'}
        checks.append(check)
    return checks


def setup_selection(root, rows, args):
    """Pull or verify complete images before Harbor starts an agent or its budget."""
    require_paths(rows)
    mapping, evidence = resolved_images(root, rows, args)
    policy = getattr(args, 'pull_policy', 'missing')
    prepared, checks = {}, []
    for row in rows:
        roles = mapping.get(row['path'], {})
        for role in required_image_roles(root, row):
            if not roles.get(role):
                raise ValueError(f'No complete {role} image for {row["path"]}; '
                                 'run tcsexam build or supply a complete artifact manifest')
        for role, ref in roles.items():
            if not PIN.fullmatch(ref) and not local_reference(evidence.get(ref), ref):
                raise ValueError(f'Image is not a prepared product: {row["path"]}/{role}')
    support = host_support_targets(evidence, args)

    def acquire(ref, label):
        if ref in prepared:
            return prepared[ref]
        record = evidence.get(ref, {})
        local = inspect_image(ref, args, record)
        if record.get('local'):
            if not local:
                raise ValueError(f'Locally built image is missing or differs: {label}; run tcsexam build')
        elif policy == 'always' or not local:
            if policy == 'never':
                raise ValueError(f'Complete image is absent from the selected Docker host: {ref}')
            print(f'Preparing complete image for {label}', flush=True)
            try:
                result = subprocess.run(docker_command(args) + ['pull', ref],
                                        capture_output=True, text=True)
            except OSError as exc:
                raise ValueError('Docker is unavailable on the selected execution host') from exc
            if result.returncode:
                raise ValueError(f'Image pull failed for {label}; '
                                 'check the registry address and host authentication')
            local = inspect_image(ref, args, record)
        if not local:
            raise ValueError(f'Image identity cannot be verified: {label}')
        expected_platform = record.get('platform')
        if expected_platform and local['platform'] != expected_platform:
            raise ValueError(f'Image platform differs from the artifact record: {ref}')
        prepared[ref] = local
        return local

    for row in rows:
        for role, ref in mapping[row['path']].items():
            if role == 'backend' and not local_reference(evidence.get(ref), ref):
                checks.append({'task': row['path'], 'role': role, 'image': ref,
                               'status': 'backend_host_pull_required'})
                continue
            local = acquire(ref, row['path']+'/'+role)
            checks.append({'task': row['path'], 'role': role, 'image': ref,
                           'status': 'host_prepared', **local})
    host_checks = []
    for row in support:
        ref = row.get('image') or row.get('reference')
        local = acquire(ref, row['id'])
        target = row.get('local_tag') if row.get('support_kind') == 'harbor_egress_control' else None
        if target:
            tagged = subprocess.run(docker_command(args) + ['tag', ref, target],
                                    capture_output=True, text=True)
            if tagged.returncode:
                raise ValueError('Cannot prepare the Harbor helper tag on the execution host')
        host_checks.append({'artifact_id': row['id'], 'image': ref, 'status': 'host_prepared',
                            'support_kind': row.get('support_kind'),
                            'local_image': row.get('local_image'), 'local_tag': target, **local})
    capacity = offline_host_capacity(root, rows, mapping, args)
    failed = [check for check in capacity if not check['ok']]
    if failed:
        first = failed[0]
        raise ValueError(f'Execution host lacks resources for {first["task"]}: '
                         f'need {first["minimum"]}; found {first["available"]}')
    report = {'schema_version': 1, 'host_prepared': True, 'image_map': mapping,
              'docker_context': getattr(args, 'docker_context', None) or os.environ.get('DOCKER_CONTEXT'),
              'images': checks, 'host_support': host_checks, 'host_capacity': capacity,
              'model_started': False,
              'note': 'Host availability does not replace content, isolation or Harbor runtime acceptance.'}
    host = json.dumps([report['docker_context'], os.environ.get('DOCKER_HOST', '')])
    key = hashlib.sha256(host.encode()).hexdigest()[:16]
    save_record(cache_path(args) / 'hosts' / (key + '.json'), report)
    return report
