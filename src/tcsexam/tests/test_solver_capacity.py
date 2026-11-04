import pytest
from tcsexam.solver_capacity import InsufficientSolverCapacity, plan_solver_capacity


def standard(**kwargs):
    args=dict(standard_shards=10, worker_cpu_count=1, worker_memory_mb=8192,
              available_cpu_count=8, available_memory_mb=24576, instance_count=100,
              per_instance_seconds=600, build_seconds=600, check_seconds=300)
    args.update(kwargs)
    return plan_solver_capacity(**args)


def test_small_host_reduces_concurrency_and_extends_lifecycle_not_solver_time():
    result=standard()
    assert result['effective']['shards'] == 3
    assert result['effective']['instances_per_shard_max'] == 34
    assert result['standard']['worker_resources'] == result['effective']['worker_resources']
    assert result['standard']['per_instance_seconds'] == result['effective']['per_instance_seconds'] == 600
    timeouts=result['timeouts']
    assert timeouts['judge_timeout_seconds'] >= 600 + 34*(600+300)
    assert timeouts['worker_ttl_seconds'] > timeouts['judge_timeout_seconds']
    assert timeouts['poll_timeout_seconds'] > timeouts['session_ttl_seconds'] > timeouts['judge_timeout_seconds']
    assert result['requires_image_timeout_update']
    assert result['solver_budget_changed'] is False
    assert result['enforcement']['isolation'] == 'required'
    assert result['enforcement']['configured_limits_verified'] is False


def test_pool_cannot_be_split_or_lose_cross_instance_time():
    result=standard(standard_shards=1, worker_cpu_count=4, instance_count=39,
                    per_instance_seconds=30, pool=True, total_pool_seconds=1170)
    assert result['effective']['shards'] == 1
    assert result['effective']['total_pool_seconds'] == 1170
    assert result['effective']['instances_per_shard_max'] == 39
    with pytest.raises(ValueError, match='complete shard'):
        standard(pool=True)
    with pytest.raises(ValueError, match='complete shard'):
        standard(standard_shards=1, requested_shards=2, pool=True)


def test_host_below_single_worker_fails_without_reducing_resources():
    with pytest.raises(InsufficientSolverCapacity, match='One Solver worker requires'):
        standard(available_memory_mb=8191)
    with pytest.raises(InsufficientSolverCapacity):
        standard(worker_cpu_count=4, available_cpu_count=3.9)


def test_baked_timeout_and_explicit_parallelism_are_reported():
    baseline=standard(available_memory_mb=102400)
    smaller=standard(requested_shards=1, baked_judge_timeout_seconds=baseline['timeouts']['judge_timeout_seconds'])
    assert smaller['effective']['shards'] == 1
    assert smaller['requires_image_timeout_update']
    enough=standard(requested_shards=1, baked_judge_timeout_seconds=smaller['timeouts']['judge_timeout_seconds'])
    assert not enough['requires_image_timeout_update']
    assert enough['effective']['shards'] == enough['requested']['shards'] == 1
    assert enough['standard']['shards'] == 10


def test_short_sets_do_not_create_empty_shards_and_bad_numbers_fail():
    assert standard(instance_count=2)['effective']['shards'] == 2
    for change in ({'worker_cpu_count':0}, {'available_cpu_count':float('nan')},
                   {'instance_count':True}, {'per_instance_seconds':-1}, {'pool':1}):
        with pytest.raises(ValueError):
            standard(**change)


def test_specs_distinguish_container_request_and_single_solver_allocation():
    from pathlib import Path
    from tcsexam.solver_capacity import solver_task_spec
    root=Path(__file__).resolve().parents[3]
    ce=solver_task_spec(root,'ce-pace2021','hidden')
    assert ce['legacy_container_request'] == {'cpu':16,'mem':8192}
    assert ce['scoring_unit'] == {'cpu_count':1,'memory_mb':8192,'storage_mb':8192}
    bpp=solver_task_spec(root,'bpp-bpplib','public')
    assert bpp['pool'] and bpp['standard_shards'] == 1
    assert bpp['total_pool_seconds'] == 30*bpp['instance_count']
    assert bpp['scoring_unit']['cpu_count'] == 4


def test_every_final_client_accepts_prepared_resource_and_timeout_values(monkeypatch):
    import ast
    import os
    from pathlib import Path
    root=Path(__file__).resolve().parents[3]
    monkeypatch.setenv('TCSEXAM_N_SHARDS','2')
    monkeypatch.setenv('TCSEXAM_SESSION_TTL','99999')
    monkeypatch.setenv('TCSEXAM_WORKER_CPUS','3')
    monkeypatch.setenv('TCSEXAM_WORKER_MEMORY_MB','12345')
    for path in (root/'tasks/solver/online').glob('*/tests/fetch_final.py'):
        tree=ast.parse(path.read_text())
        assignments=[node for node in tree.body if isinstance(node,ast.Assign)
                     and any(isinstance(t,ast.Name) and t.id in {'N_SHARDS','SESSION_TTL','RESOURCES'} for t in node.targets)]
        namespace={'os':os}
        exec(compile(ast.Module(body=assignments,type_ignores=[]),str(path),'exec'),namespace)
        assert namespace['N_SHARDS'] == 2
        assert namespace['SESSION_TTL'] == 99999
        assert namespace['RESOURCES'] == {'cpu':3,'mem':12345}
