"""Plan Docker Solver concurrency and lifecycle limits without changing budgets.

Callers supply available host capacity after their controller reservations. A
worker always retains the declared CPU/memory and the original solver budget.
Reducing concurrency changes queueing and shard wall time, never that budget.
"""
from __future__ import annotations

import math


class InsufficientSolverCapacity(ValueError):
    """The host cannot run even one worker with the requested resources."""


def _integer(name, value, *, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def _seconds(name, value, *, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0 or (positive and value == 0)):
        raise ValueError(f'{name} must be a finite {"positive" if positive else "nonnegative"} number')
    return float(value)


def plan_solver_capacity(*, standard_shards: int, worker_cpu_count: int,
                         worker_memory_mb: int, available_cpu_count: float,
                         available_memory_mb: int, instance_count: int,
                         per_instance_seconds: float, pool: bool = False,
                         total_pool_seconds: float | None = None,
                         build_seconds: float = 600, check_seconds: float = 300,
                         preparation_seconds: float = 600,
                         worker_margin_seconds: float = 300,
                         ready_timeout_seconds: float = 600,
                         archive_margin_seconds: float = 300,
                         requested_shards: int | None = None,
                         baked_judge_timeout_seconds: float | None = None) -> dict:
    """Return capacities and all timeouts required for the effective shard count.

    ``check_seconds`` is a per-instance checking allowance for independent
    instances and a whole-pool checking allowance for pool tasks. Preparation,
    compilation and certificate checking remain outside solver time. The
    reported timeouts bound process/service lifetimes; they do not replace the
    scoring program's per-instance or shared time-pool timer.

    ``baked_judge_timeout_seconds`` is the timeout in the prepared worker image.
    If it is absent or too small, ``requires_image_timeout_update`` is true:
    the caller must build/configure and verify that value before running.
    """
    standard_shards = _integer('standard_shards', standard_shards)
    cpu = _integer('worker_cpu_count', worker_cpu_count)
    memory = _integer('worker_memory_mb', worker_memory_mb)
    count = _integer('instance_count', instance_count)
    available_cpu = _seconds('available_cpu_count', available_cpu_count, positive=True)
    available_memory = _integer('available_memory_mb', available_memory_mb)
    solver_seconds = _seconds('per_instance_seconds', per_instance_seconds, positive=True)
    build = _seconds('build_seconds', build_seconds)
    checks = _seconds('check_seconds', check_seconds)
    preparation = _seconds('preparation_seconds', preparation_seconds)
    worker_margin = _seconds('worker_margin_seconds', worker_margin_seconds)
    readiness = _seconds('ready_timeout_seconds', ready_timeout_seconds)
    archive_margin = _seconds('archive_margin_seconds', archive_margin_seconds)
    requested = standard_shards if requested_shards is None else _integer('requested_shards', requested_shards)
    if type(pool) is not bool:
        raise ValueError('pool must be a boolean')
    if pool and (standard_shards != 1 or requested != 1):
        raise ValueError('A shared time pool must run as one complete shard')
    capacity = min(math.floor(available_cpu / cpu), available_memory // memory)
    if capacity < 1:
        raise InsufficientSolverCapacity(
            f'One Solver worker requires {cpu} CPUs/{memory} MiB; '
            f'available {available_cpu:g} CPUs/{available_memory} MiB')
    effective = 1 if pool else min(requested, capacity, count)
    instances_per_shard = count if pool else math.ceil(count / effective)
    if pool:
        pool_budget = (solver_seconds * count if total_pool_seconds is None
                       else _seconds('total_pool_seconds', total_pool_seconds, positive=True))
        evaluation = pool_budget
        checking = checks
    else:
        if total_pool_seconds is not None:
            raise ValueError('total_pool_seconds is only valid for a shared time pool')
        pool_budget = None
        evaluation = instances_per_shard * solver_seconds
        checking = instances_per_shard * checks
    judge_timeout = math.ceil(preparation + build + evaluation + checking + worker_margin)
    # Worker expiration includes worker readiness. Session expiration starts at
    # READY in the existing store; polling also includes provisioning/queueing.
    worker_ttl = math.ceil(readiness + judge_timeout + archive_margin)
    session_ttl = math.ceil(judge_timeout + archive_margin)
    poll_timeout = math.ceil(readiness + session_ttl + archive_margin)
    verifier_timeout = math.ceil(poll_timeout + readiness + archive_margin)
    baked = (None if baked_judge_timeout_seconds is None else
             _seconds('baked_judge_timeout_seconds', baked_judge_timeout_seconds, positive=True))
    resources = {'cpu_count':cpu, 'memory_mb':memory}
    return {
        'format_version':1,
        'standard':{'shards':standard_shards, 'worker_resources':dict(resources),
                    'per_instance_seconds':solver_seconds, 'total_pool_seconds':pool_budget},
        'requested':{'shards':requested, 'worker_resources':dict(resources)},
        'effective':{'shards':effective, 'worker_resources':dict(resources),
                     'instances_per_shard_max':instances_per_shard,
                     'per_instance_seconds':solver_seconds, 'total_pool_seconds':pool_budget},
        'host_available':{'cpu_count':available_cpu, 'memory_mb':available_memory},
        'host_worker_capacity':capacity,
        'pool':pool,
        'timeouts':{'judge_timeout_seconds':judge_timeout, 'worker_ttl_seconds':worker_ttl,
                    'session_ttl_seconds':session_ttl, 'poll_timeout_seconds':poll_timeout,
                    'ready_timeout_seconds':readiness,
                    'verifier_timeout_seconds':verifier_timeout,
                    'baked_judge_timeout_seconds':baked},
        'requires_image_timeout_update':baked is None or baked < judge_timeout,
        'enforcement':{'cpu':'required_docker_quota', 'memory':'required_docker_limit',
                       'solver_time':'original_scoring_timer', 'isolation':'required',
                       'capacity_scope':'caller_supplied_available_capacity',
                       'configured_limits_verified':False},
        'concurrency_reduced':effective < requested,
        'solver_budget_changed':False,
    }


def solver_task_spec(root, task: str, split: str) -> dict:
    """Read declared scoring units and client defaults without importing clients.

    Historical container requests can contain multiple independent scoring
    units (for example CE requested 16 CPUs but pinned each solver to one).
    Both specifications are retained so callers can report the distinction.
    """
    import ast
    import hashlib
    import json
    from pathlib import Path
    if split not in {'public', 'hidden'}:
        raise ValueError('split must be public or hidden')
    root = Path(root).resolve()
    directory = root / 'tasks/solver/online' / task
    if directory.parent != root / 'tasks/solver/online' or not directory.is_dir():
        raise ValueError('Unknown Solver task')
    cfg_path = root / 'tasks/solver/offline' / task / 'tests/runtime/task.json'
    cfg = json.loads(cfg_path.read_text())
    fetch_path = directory / 'tests/fetch_final.py'
    def default(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Dict):
            return {default(k):default(v) for k,v in zip(node.keys,node.values)}
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {'int','float'}:
                return {'int':int, 'float':float}[node.func.id](default(node.args[0]))
            if isinstance(node.func, ast.Attribute) and node.func.attr in {'get','getenv'} and len(node.args) >= 2:
                return default(node.args[1])
        raise ValueError('Unsupported client-default declaration')
    values = {}
    for node in ast.parse(fetch_path.read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {'N_SHARDS','RESOURCES','SESSION_TTL'}:
                    values[target.id] = default(node.value)
    # The independent verifier's reference is the current judging split.
    # Some tasks retain an older online reference.json for historical tools.
    hidden_ref = cfg_path.parent.parent / 'reference.json'
    ref_path = directory / 'environment/app/public_reference.json' if split == 'public' else hidden_ref
    count = len(json.loads(ref_path.read_text())['instances'])
    hidden_count = len(json.loads(hidden_ref.read_text())['instances'])
    per_instance = cfg['seconds']/hidden_count if cfg['pool'] else cfg['seconds']
    checks = cfg['check_seconds']*count/hidden_count if cfg['pool'] else cfg['check_seconds']
    dockerfile = root / 'assets/environments/solver' / task / 'judge' / f'Dockerfile.{split}'
    import re
    found = re.search(r'\bJUDGE_TIMEOUT=(\d+)\b', dockerfile.read_text())
    if not found:
        raise ValueError('Judge image has no declared lifecycle timeout')
    return {'task':task, 'split':split, 'instance_count':count,
            'standard_shards':values['N_SHARDS'],
            'scoring_unit':{'cpu_count':cfg['cpus'], 'memory_mb':cfg['memory_mb'],
                            'storage_mb':cfg['disk_mb']},
            'legacy_container_request':values['RESOURCES'],
            'legacy_session_ttl_seconds':values['SESSION_TTL'],
            'per_instance_seconds':per_instance, 'pool':cfg['pool'],
            'total_pool_seconds':per_instance*count if cfg['pool'] else None,
            'build_seconds':cfg['build_seconds'], 'check_seconds':checks,
            'baked_judge_timeout_seconds':int(found[1]),
            'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in dict.fromkeys((cfg_path, fetch_path, ref_path, hidden_ref, dockerfile))}}


def standard_client_timing(root, task: str, split: str) -> dict:
    """Keep external-service clients long enough for their standard shard count.

    This is a timing assumption, not evidence of remote capacity. Operators
    must provision the standard workers or supply a verified backend plan.
    Longer existing client waits are retained, including public-session reuse
    across the development period. Scoring budgets and resources are unchanged.
    """
    import hashlib
    from pathlib import Path
    import re

    spec = solver_task_spec(root, task, split)
    unit = spec['scoring_unit']
    shards = spec['standard_shards']
    plan = plan_solver_capacity(
        standard_shards=shards, worker_cpu_count=unit['cpu_count'],
        worker_memory_mb=unit['memory_mb'], available_cpu_count=shards * unit['cpu_count'],
        available_memory_mb=shards * unit['memory_mb'], instance_count=spec['instance_count'],
        per_instance_seconds=spec['per_instance_seconds'], pool=spec['pool'],
        total_pool_seconds=spec['total_pool_seconds'], build_seconds=spec['build_seconds'],
        check_seconds=spec['check_seconds'],
        baked_judge_timeout_seconds=spec['baked_judge_timeout_seconds'])
    if plan['requires_image_timeout_update']:
        raise ValueError(f'Prepared {task}/{split} worker JUDGE_TIMEOUT is too short; rebuild its image')
    path = Path(root) / 'tasks/solver/online' / task / (
        'environment/submit.sh' if split == 'public' else 'tests/fetch_final.py')
    text = path.read_text()
    defaults = {}
    for name in ('SESSION_TTL', 'POLL_TIMEOUT'):
        if split == 'public':
            pattern = rf'^{name}="\$\{{TCSEXAM_{name}:-([0-9]+)\}}"'
        else:
            pattern = rf'^{name}\s*=\s*(?:int|float)\(os\.environ\.get\("TCSEXAM_{name}", "([0-9]+)"\)\)'
        matches = re.findall(pattern, text, re.MULTILINE)
        if len(matches) != 1:
            raise ValueError(f'Cannot determine {task}/{split} default {name}')
        defaults[name] = int(matches[0])
    timing = plan['timeouts']
    poll = max(defaults['POLL_TIMEOUT'], timing['poll_timeout_seconds'])
    session = max(defaults['SESSION_TTL'], timing['worker_ttl_seconds'])
    return {
        'assumption': 'external_service_provisions_standard_shards',
        'service_requirements': {
            'concurrent_workers': shards,
            'worker_resources': spec['legacy_container_request'],
            'minimum_max_ttl_seconds': session,
            'worker_image_judge_timeout_seconds': spec['baked_judge_timeout_seconds'],
            'capacity_verified': False,
        },
        'source': spec,
        'client_source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'client_defaults_seconds': defaults,
        'standard_timeouts_seconds': timing,
        'env': {
            'TCSEXAM_SESSION_TTL': str(session),
            'TCSEXAM_POLL_TIMEOUT': str(poll),
        },
        'verifier_timeout_seconds': poll + timing['verifier_timeout_seconds'] - timing['poll_timeout_seconds'],
        'solver_budget_changed': False,
    }
