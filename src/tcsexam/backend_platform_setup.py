"""Plan separately hosted workers through the existing module:factory adapter.

No platform SDK is imported here. A deployment supplies an adapter, verified
worker request limits, and a service URL reachable from development and worker
hosts. The control service and development containers must be on separate hosts
from the judging workers; their memory is not subtracted from worker requests.
"""
from __future__ import annotations

import copy
import re

from .backend_setup import plan_docker_backend
from .solver_capacity import solver_task_spec


def plan_platform_backend(root, online_rows, product_references, *, adapter,
                          worker_slots, worker_cpu_limit, worker_memory_mb_limit,
                          capacity_evidence, public_base_url, client_base_url=None,
                          profile='', port=8420, state_dir='/tmp/tcsexam-backend',
                          per_task_worker_slots=None,
                          storage_mb='standard'):
    """Keep original worker requests and timers while capping independent hosts.

    Limits describe requests accepted by the platform, not guest MemTotal or an
    exclusive solver allocation. Whole-sandbox memory also includes the worker
    agent/checker and guest overhead. Evidence must explicitly establish this
    execution contract; a nominal catalog specification alone is insufficient.
    """
    if not isinstance(adapter, str) or not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*', adapter):
        raise ValueError('Use an explicit platform adapter module:factory')
    for name, value in [('worker_slots', worker_slots), ('worker_cpu_limit', worker_cpu_limit),
                        ('worker_memory_mb_limit', worker_memory_mb_limit)]:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(name + ' must be a positive integer')
    evidence = copy.deepcopy(capacity_evidence)
    if not isinstance(evidence, dict) or not all(evidence.get(k) is True for k in
            ('worker_requests_verified', 'control_host_separate', 'development_host_separate')):
        raise ValueError('Verified worker requests and separate control/development hosts are required')
    scope = evidence.get('resource_contract')
    if scope not in {'whole_worker_sandbox', 'worker_process_cgroup'} or not evidence.get('contract_evidence'):
        raise ValueError('Record the worker resource contract and its source evidence')
    rows = list(online_rows)
    if not rows:
        raise ValueError('Select at least one Online Solver task')
    if len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate Online Solver task')
    requested_slots = dict(per_task_worker_slots or {})
    if set(requested_slots) - {r['id'] for r in rows}:
        raise ValueError('Worker-slot override names an unselected task')
    plans = []
    task_slots = {}
    for row in rows:
        specs = [solver_task_spec(root, row['id'], split)['scoring_unit'] for split in ('public', 'hidden')]
        if any((s['cpu_count'], s['memory_mb']) != (specs[0]['cpu_count'], specs[0]['memory_mb']) for s in specs):
            raise ValueError('Public/hidden worker requests need separate platform plans')
        cpu, memory = specs[0]['cpu_count'], specs[0]['memory_mb']
        slots = requested_slots.get(row['id'], worker_slots)
        if isinstance(slots, bool) or not isinstance(slots, int) or slots < 1:
            raise ValueError('Per-task worker slots must be positive integers')
        if solver_task_spec(root, row['id'], 'hidden')['pool']:
            slots = 1
        task_slots[row['id']] = slots
        if cpu > worker_cpu_limit or memory > worker_memory_mb_limit:
            raise ValueError('Platform cannot honor the original worker request for ' + row['id'])
        # Per-task arithmetic prevents smaller workers from multiplying a
        # physical worker-slot cap when several task specifications differ.
        local = plan_docker_backend(root, [row], product_references,
            available_cpu_count=cpu * slots, available_memory_mb=memory * slots,
            capacity_evidence={'effective_limits_verified': True, **evidence},
            public_base_url=public_base_url, client_base_url=client_base_url,
            port=port, state_dir=state_dir, storage_mb=storage_mb)
        for split in local['tasks'][row['id']].values():
            split['plan']['enforcement'].update(cpu='platform_worker_request',
                memory=scope, isolation='platform_worker_boundary',
                capacity_scope='independent_worker_slots', configured_limits_verified=False)
        plans.append(local)
    result = copy.deepcopy(plans[0])
    result['tasks'] = {task: value for p in plans for task, value in p['tasks'].items()}
    config = result['config']
    config['adapter'] = adapter
    for key in list(config):
        if key.startswith('docker_'):
            config.pop(key)
    config['public_image_map'] = {k: v for p in plans for k, v in p['config']['public_image_map'].items()}
    backend = config['backend']
    for key in ('create_concurrency', 'session_create_concurrency', 'max_sandboxes_global'):
        backend[key] = sum(task_slots.values())
    backend['max_sandbox_memory_mb'] = sum(task_slots.values()) * worker_memory_mb_limit
    session = backend['judge_sessions']
    session.update(profile=profile, max_shards=max(task_slots.values()), max_sessions=len(rows),
        max_session_cpu_count=max(task_slots.values()) * worker_cpu_limit,
        max_session_memory_mb=max(task_slots.values()) * worker_memory_mb_limit)
    session['spec']['cpu_count'] = max(p['config']['backend']['judge_sessions']['spec']['cpu_count'] for p in plans)
    session['spec']['memory_mb'] = max(p['config']['backend']['judge_sessions']['spec']['memory_mb'] for p in plans)
    for key in ('ttl_seconds', 'max_ttl_seconds', 'idle_ttl_seconds', 'read_timeout_seconds'):
        session[key] = max(p['config']['backend']['judge_sessions'][key] for p in plans)
    session['routes'] = [r for p in plans for r in p['config']['backend']['judge_sessions']['routes']]
    result['capacity_evidence'] = {'effective_limits_verified': True, **evidence,
        'scope': 'independent_platform_worker_requests', 'worker_slots_per_task': task_slots,
        'service_capacity_scope': 'selected_independent_runs_not_a_platform_global_limit',
        'worker_cpu_limit': worker_cpu_limit, 'worker_memory_mb_limit': worker_memory_mb_limit,
        'guest_MemTotal_is_not_the_requested_limit': True}
    result['scheduling'].update(max_live_sessions=len(rows),
        max_concurrent_trials=1, trial_limit_scope='per_development_host_or_run',
        independent_runs_may_execute_concurrently=True)
    result['deployment'] = {'mode': 'external_platform_adapter', 'adapter': adapter,
        'resource_contract': scope, 'platform_sdk_dependency_bundled': False,
        'docker_native_acceptance': False}
    return result
