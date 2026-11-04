from argparse import Namespace
import json
from pathlib import Path
import tomllib
from unittest.mock import patch

import pytest

from tcsexam.backend_cli import client_plan, configure
from tcsexam.backend_setup import plan_docker_backend
from tcsexam.cli import main
from tcsexam.layout import selection

ROOT = Path(__file__).resolve().parents[3]
HIDDEN = 'example.invalid/ce-hidden@sha256:' + 'a' * 64
PUBLIC = 'example.invalid/ce-public@sha256:' + 'b' * 64


def fixtures(tmp_path):
    _, rows = selection(ROOT, 'full', task='ce-pace2021', solver_protocol='online')
    refs = {'backend-online-ce-pace2021': HIDDEN,
            'backend-public-online-ce-pace2021': PUBLIC}
    plan = plan_docker_backend(ROOT, rows, refs, available_cpu_count=7,
        available_memory_mb=16384, capacity_evidence={'effective_limits_verified': True},
        public_base_url='http://judge.example.invalid:8420',
        client_base_url='http://judge.example.invalid:8420', storage_mb=None)
    path = tmp_path / 'backend.plan.json'
    path.write_text(json.dumps(plan))
    image_map = tmp_path / 'images.json'
    image_map.write_text(json.dumps({rows[0]['path']: {'backend': HIDDEN}}))
    return rows, refs, plan, path, image_map


def test_prepare_applies_public_and_hidden_capacity_and_records_concurrency(tmp_path, monkeypatch):
    rows, _, plan, path, image_map = fixtures(tmp_path)
    monkeypatch.delenv('TCSEXAM_BASE_URL', raising=False)
    monkeypatch.setenv('TCSEXAM_ARCHIVE_TOKEN', 'not-for-the-development-environment')
    output = tmp_path / 'job.json'
    assert main(['prepare', '--root', str(ROOT), '--suite', 'full', '--task', rows[0]['id'],
        '--base-url', 'https://model.example.invalid/v1', '--model', 'example-model',
        '--image-map', str(image_map), '--backend-plan', str(path), '--concurrency', '4',
        '--output', str(output)]) == 0
    job = json.loads(output.read_text())
    provenance = json.loads(output.with_suffix('.selection.json').read_text())
    assert job['n_concurrent_trials'] == 1
    assert provenance['requested_concurrency'] == 4
    assert provenance['effective_concurrency'] == 1
    data = tomllib.loads((Path(job['tasks'][0]['path']) / 'task.toml').read_text())
    for split, phase in [('public', 'environment'), ('hidden', 'verifier')]:
        for key, value in plan['tasks'][rows[0]['id']][split]['env'].items():
            assert data[phase]['env'][key] == value
    assert 'TCSEXAM_ARCHIVE_TOKEN' not in data['environment']['env']
    assert data['verifier']['env']['TCSEXAM_ARCHIVE_TOKEN'] == '${TCSEXAM_ARCHIVE_TOKEN}'
    assert data['agent']['timeout_sec'] == 43200
    original = tomllib.loads((ROOT / rows[0]['path'] / 'task.toml').read_text())
    required = plan['tasks'][rows[0]['id']]['hidden']['verifier_timeout_seconds']
    assert data['verifier']['timeout_sec'] == max(original['verifier']['timeout_sec'], required)
    assert required > original['verifier']['timeout_sec']
    assert 'not-for-the-development-environment' not in output.read_text()


def test_old_task_spec_or_different_endpoint_rejects_plan(tmp_path, monkeypatch):
    rows, _, plan, path, image_map = fixtures(tmp_path)
    monkeypatch.delenv('TCSEXAM_BASE_URL', raising=False)
    args = Namespace(backend_plan=path, image_map=image_map, judge_url=None)
    plan['tasks'][rows[0]['id']]['hidden']['source']['instance_count'] += 1
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match='older task specification'):
        client_plan(ROOT, rows, args)
    args.judge_url = 'http://different.example.invalid:8420'
    with pytest.raises(ValueError, match='URL differs'):
        client_plan(ROOT, rows, args)


def test_configure_only_writes_nonsecret_service_plan(tmp_path):
    rows, refs, _, _, _ = fixtures(tmp_path)
    evidence = {ref: {'id': identity} for identity, ref in refs.items()}
    args = Namespace(artifacts=tmp_path / 'artifacts.json', judge_url='http://judge.example.invalid:8420',
        config=tmp_path / 'backend.yaml', state_dir=tmp_path / 'state', port=8420, storage_limit='none')
    capacity = {'effective_limits_verified': True, 'available_cpu_count': 7,
                'available_memory_mb': 16384, 'docker_endpoint': 'unix:///var/run/docker.sock'}
    with patch('tcsexam.backend_cli.effective_capacity', return_value=capacity), \
         patch('tcsexam.backend_cli.artifacts', return_value=({}, evidence)):
        report = configure(ROOT, rows, args)
    assert not report['service_started'] and not report['model_started']
    assert Path(report['backend_plan']).is_file()
    assert 'require_environment_credentials: true' in args.config.read_text()
