from pathlib import Path
import pytest
from tcsexam.backend_platform_setup import plan_platform_backend
from tcsexam.backend_setup import backend_yaml
from tcsexam.backend.config import load_config

ROOT=Path(__file__).resolve().parents[3]

def plan(tasks=('celar-rlfap','gp-dimacs10'), **overrides):
    rows=[{'id': t, 'track':'solver', 'variant':'online'} for t in tasks]
    refs={f'backend-{role}-online-{t}':f'tcsexam/{t}-{role}:fixed' for t in tasks for role in ['public']}
    refs.update({f'backend-online-{t}':f'tcsexam/{t}-hidden:fixed' for t in tasks})
    params=dict(adapter='deployment.platform:create', worker_slots=2, worker_cpu_limit=4,
        worker_memory_mb_limit=32768, capacity_evidence={'worker_requests_verified':True,
            'control_host_separate':True,'development_host_separate':True,
            'resource_contract':'whole_worker_sandbox','contract_evidence':['fixed-source-receipt.json']},
        public_base_url='http://control.example:8420', storage_mb=None)
    params.update(overrides)
    return plan_platform_backend(ROOT, rows, refs, **params)

def test_separate_hosts_keep_original_limits_pool_and_ttl(tmp_path, monkeypatch):
    for key in ('TCSEXAM_TOKEN_ID','TCSEXAM_TOKEN_SECRET','TCSEXAM_ARCHIVE_TOKEN'):
        monkeypatch.setenv(key, 'unit-test-placeholder')
    generated=plan()
    assert generated['deployment']['docker_native_acceptance'] is False
    assert not any(k.startswith('docker_') for k in generated['config'])
    for task, splits in generated['tasks'].items():
        for split in splits.values():
            p=split['plan']
            assert p['effective']['shards'] == (1 if task=='gp-dimacs10' else 2)
            assert p['standard']['worker_resources']==p['effective']['worker_resources']
            assert not p['solver_budget_changed']
            assert split['env']['TCSEXAM_WORKER_MEMORY_MB']=='16384'
            assert generated['config']['backend']['judge_sessions']['max_ttl_seconds'] >= p['timeouts']['worker_ttl_seconds']
    path=tmp_path/'config.yaml';path.write_text(backend_yaml(generated));config=load_config(path)
    assert config.adapter=='deployment.platform:create'
    assert config.backend.max_sandboxes_global==3
    assert config.backend.judge_sessions.max_sessions==2

def test_whole_sandbox32_is_not_compared_to_guest_memtotal():
    generated=plan(tasks=('dfvs-pace2022',), capacity_evidence={
        'worker_requests_verified':True,'control_host_separate':True,'development_host_separate':True,
        'resource_contract':'whole_worker_sandbox','contract_evidence':['original-request-chain'],
        'guest_memory_bytes_observed':33500000000})
    assert generated['tasks']['dfvs-pace2022']['hidden']['env']['TCSEXAM_WORKER_MEMORY_MB']=='32768'
    assert generated['capacity_evidence']['guest_MemTotal_is_not_the_requested_limit']

@pytest.mark.parametrize('bad', [
    {'worker_slots':True}, {'adapter':'docker'}, {'worker_memory_mb_limit':8192},
    {'capacity_evidence':{'worker_requests_verified':True,'control_host_separate':False}},
    {'capacity_evidence':{'worker_requests_verified':True,'control_host_separate':True,
        'development_host_separate':True,'resource_contract':'unknown','contract_evidence':['x']}}])
def test_reject_missing_contract_or_downgrade(bad):
    with pytest.raises(ValueError):plan(**bad)

def test_per_task_concurrency_is_not_a_platform_global_cap():
    generated=plan(per_task_worker_slots={'celar-rlfap':15,'gp-dimacs10':20})
    assert generated['tasks']['celar-rlfap']['public']['plan']['effective']['shards']==10
    assert generated['config']['backend']['judge_sessions']['max_shards']==15
    assert generated['tasks']['gp-dimacs10']['public']['plan']['effective']['shards']==1
    assert generated['config']['backend']['max_sandboxes_global']==16
    assert generated['scheduling']['independent_runs_may_execute_concurrently']
