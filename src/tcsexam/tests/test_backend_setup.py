import json
from pathlib import Path
import pytest
from tcsexam.backend_setup import backend_yaml, plan_docker_backend, require_backend_environment
from tcsexam.backend.config import load_config

ROOT=Path(__file__).resolve().parents[3]


def plan(**kw):
    rows=[{'id':'ce-pace2021','track':'solver','variant':'online'},
          {'id':'bpp-bpplib','track':'solver','variant':'online'}]
    refs={'backend-online-ce-pace2021':'tcsexam/ce-hidden:prepared',
          'backend-public-online-ce-pace2021':'tcsexam/ce-public:prepared',
          'bpp-bpplib-online-backend':'tcsexam/bpp-hidden:prepared',
          'backend-public-online-bpp-bpplib':'tcsexam/bpp-public:prepared'}
    args=dict(available_cpu_count=15, available_memory_mb=24576,
              capacity_evidence={'effective_limits_verified':True, 'scope':'daemon+cgroup+affinity-controller'},
              public_base_url='http://host.docker.internal:8420',client_base_url='http://backend.example:8420')
    args.update(kw)
    return plan_docker_backend(ROOT,rows,refs,**args)


def test_serial_admission_and_complete_split_timeouts():
    generated=plan()
    cfg=generated['config']['backend']['judge_sessions']
    assert cfg['max_sessions']==1 and not cfg['hibernate_enabled']
    assert generated['scheduling']['max_concurrent_trials']==1
    for task,splits in generated['tasks'].items():
        for split,record in splits.items():
            assert record['env']['TCSEXAM_CLOSE_SESSION_AFTER_SUBMIT']=='1'
            assert record['env']['TCSEXAM_CLOSE_AGENT_SESSIONS']=='1'
            assert cfg['max_ttl_seconds'] >= int(record['env']['TCSEXAM_SESSION_TTL'])
            assert cfg['idle_ttl_seconds'] >= record['plan']['timeouts']['judge_timeout_seconds']
            assert cfg['read_timeout_seconds'] >= record['plan']['timeouts']['judge_timeout_seconds']
            assert not record['plan']['requires_image_timeout_update']
    ce=generated['tasks']['ce-pace2021']['hidden']
    assert ce['env']['TCSEXAM_WORKER_CPUS']=='1'
    assert ce['plan']['standard']['legacy_container_request']['cpu']==16
    assert ce['env']['TCSEXAM_N_SHARDS']=='3'
    assert generated['tasks']['bpp-bpplib']['hidden']['env']['TCSEXAM_N_SHARDS']=='1'


def test_generated_yaml_has_no_credential_values_and_loads(tmp_path,monkeypatch):
    monkeypatch.setenv('TCSEXAM_TOKEN_ID','test-identity')
    monkeypatch.setenv('TCSEXAM_TOKEN_SECRET','test-secret-never-write')
    monkeypatch.setenv('TCSEXAM_ARCHIVE_TOKEN','verifier-secret-never-write')
    generated=plan(storage_mb=None)
    text=backend_yaml(generated)
    assert 'test-secret-never-write' not in text and 'verifier-secret-never-write' not in text
    assert 'test-identity' not in text
    path=tmp_path/'backend.yaml';path.write_text(text)
    config=load_config(path)
    assert config.adapter=='docker'
    assert config.archive_token=='verifier-secret-never-write'
    assert config.backend.judge_sessions.max_sessions==1
    assert config.backend.judge_sessions.spec['storage_mb'] is None
    assert config.public_image_map['tcsexam/ce-hidden:prepared']=='tcsexam/ce-public:prepared'
    require_backend_environment()


def test_missing_credentials_and_unverified_capacity_fail_without_exposing_values():
    with pytest.raises(ValueError,match='TCSEXAM_ARCHIVE_TOKEN'):
        require_backend_environment({'TCSEXAM_TOKEN_ID':'secret-id','TCSEXAM_TOKEN_SECRET':'do-not-log'})
    with pytest.raises(ValueError,match='effective cgroup'):
        plan(capacity_evidence={'effective_limits_verified':False})
    with pytest.raises(ValueError,match='loopback'):
        plan(public_base_url='http://127.0.0.1:8420')


def test_mixed_task_storage_uses_explicit_per_request_values(monkeypatch):
    import tcsexam.backend_setup as setup
    original=setup.solver_task_spec
    def altered(root, task, split):
        value=original(root,task,split)
        value['scoring_unit']['storage_mb']=4096 if task=='ce-pace2021' else 8192
        return value
    monkeypatch.setattr(setup,'solver_task_spec',altered)
    generated=plan()
    assert generated['config']['backend']['judge_sessions']['spec']['storage_mb']==4096
    for split in ('public','hidden'):
        assert generated['tasks']['ce-pace2021'][split]['env']['TCSEXAM_WORKER_STORAGE_MB']=='4096'
        assert generated['tasks']['bpp-bpplib'][split]['env']['TCSEXAM_WORKER_STORAGE_MB']=='8192'
