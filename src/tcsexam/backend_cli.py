"""Prepare a local Docker judging service and bind its plan to Harbor jobs."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

from .layout import load, within
from .setup import artifacts, docker_command, save_record


def effective_capacity(root, rows, args):
    """Read the local execution host's effective limits without starting workers."""
    command = docker_command(args)
    endpoint = os.environ.get('DOCKER_HOST') if not getattr(args, 'docker_context', None) else None
    if not endpoint:
        output = subprocess.run(command + ['context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'],
                                capture_output=True, text=True, timeout=30, check=True)
        endpoint = output.stdout.strip()
    if not endpoint.startswith('unix://'):
        raise ValueError('Configure the service on the execution host using its local Docker Unix socket')
    daemon = json.loads(subprocess.run(command + ['info', '--format', '{{json .}}'],
                       capture_output=True, text=True, timeout=30, check=True).stdout)
    pids = []
    for path in Path('/proc').iterdir():
        if path.name.isdecimal():
            try:
                if (path / 'comm').read_text().strip() == 'dockerd':
                    pids.append(int(path.name))
            except OSError:
                continue
    if len(pids) != 1:
        raise ValueError('Configure on a Linux host with exactly one visible Docker daemon and its cgroups')
    name = '_tcsexam_capacity_resources'
    path = root / 'assets/environments/solver/offline-runtime/resources.py'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        host = module.discover(pid=pids[0], disk=daemon['DockerRootDir'])
        controller = module.discover(disk=daemon['DockerRootDir'])
    except (RuntimeError, OSError) as exc:
        raise ValueError('Cannot verify effective Docker host cgroup limits: ' + str(exc)) from exc
    finally:
        sys.modules.pop(name, None)
    development = [tomllib.loads((within(root, row['path']) / 'task.toml').read_text())['environment']
                   for row in rows]
    reserved_cpu = 1 + max(int(env.get('cpus', 1)) for env in development)
    reserved_memory = 512 + max(int(env.get('memory_mb', 0)) for env in development)
    cpu = min(host.cpu_count, controller.cpu_count, int(daemon['NCPU'])) - reserved_cpu
    memory = min(host.memory_bytes, controller.memory_bytes, host.available_bytes,
                 controller.available_bytes, int(daemon['MemTotal'])) // 1048576 - reserved_memory
    if cpu < 1 or memory < 1:
        raise ValueError('No worker capacity remains after reserving the model development container and controller')
    return {'effective_limits_verified': True, 'daemon': host.json(), 'controller': controller.json(),
            'docker_endpoint': endpoint, 'reserved_cpu_count': reserved_cpu,
            'reserved_memory_mb': reserved_memory, 'available_cpu_count': cpu,
            'available_memory_mb': memory, 'concurrent_trials': 1}


def configure(root, rows, args):
    """Write nonsecret configuration and per-task resource settings; do not serve."""
    from .backend_setup import backend_yaml, plan_docker_backend
    rows = [row for row in rows if row['track'] == 'solver' and row['variant'] == 'online']
    if not rows:
        raise ValueError('Select Online Solver tasks to configure a backend')
    if not getattr(args, 'artifacts', None):
        raise ValueError('Build the selected tasks first, or provide --artifacts with their prepared image records')
    _, evidence = artifacts(args.artifacts, root=root)
    references = {row['id']: ref for ref, row in evidence.items() if row.get('id')}
    capacity = effective_capacity(root, rows, args)
    url = args.judge_url or os.environ.get('TCSEXAM_BASE_URL')
    if not url:
        raise ValueError('Set --judge-url to an HTTP(S) origin reachable from model and worker containers')
    storage = args.storage_limit
    if storage != 'standard':
        storage = None if storage == 'none' else int(storage)
    plan = plan_docker_backend(root, rows, references,
        available_cpu_count=capacity['available_cpu_count'],
        available_memory_mb=capacity['available_memory_mb'], capacity_evidence=capacity,
        public_base_url=url, client_base_url=url, port=args.port or 8420,
        state_dir=str(args.state_dir.resolve()), docker_socket=capacity['docker_endpoint'][7:],
        storage_mb=storage)
    plan['product_references'] = references
    plan['config_path'] = str(args.config.resolve())
    args.config.parent.mkdir(parents=True, exist_ok=True)
    args.config.write_text(backend_yaml(plan))
    path = args.config.with_suffix('.plan.json')
    save_record(path, plan)
    return {'config': str(args.config), 'backend_plan': str(path), 'tasks': sorted(plan['tasks']),
            'scheduling': plan['scheduling'], 'service_started': False, 'model_started': False}


def client_plan(root, rows, args):
    """Validate an explicit local-service plan; external services need no plan."""
    path = getattr(args, 'backend_plan', None) or os.environ.get('TCSEXAM_BACKEND_PLAN')
    online = [r for r in rows if r['variant'] == 'online']
    if not path or not online:
        return None
    from .solver_capacity import solver_task_spec
    from .setup import resolved_images
    document = load(Path(path))
    if document.get('format_version') != 1 or document.get('scheduling', {}).get('max_concurrent_trials') != 1:
        raise ValueError('Unsupported backend plan; regenerate with tcsexam backend configure')
    if not document.get('capacity_evidence', {}).get('effective_limits_verified'):
        raise ValueError('Backend plan has no effective host-capacity evidence')
    mapping, _ = resolved_images(root, online, args)
    planned_url = document['config']['public_base_url']
    specified_url = getattr(args, 'judge_url', None) or os.environ.get('TCSEXAM_BASE_URL')
    if specified_url and specified_url.rstrip('/') != planned_url.rstrip('/'):
        raise ValueError('The selected backend URL differs from the prepared backend plan')
    for row in online:
        splits = document['tasks'].get(row['id'])
        if not splits:
            raise ValueError('Backend plan does not include ' + row['id'])
        for split in ('public', 'hidden'):
            if splits[split]['source'] != solver_task_spec(root, row['id'], split):
                raise ValueError('Backend plan uses an older task specification; configure it again: ' + row['id'])
        if mapping.get(row['path'], {}).get('backend') != splits['hidden']['effective_worker_image']:
            raise ValueError('Backend plan and task backend image differ: ' + row['id'])
    args.judge_url = planned_url
    return document
