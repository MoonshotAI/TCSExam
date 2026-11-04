"""Check TCSExam budgets against Harbor's actual timeout resolution and clock."""
import asyncio
from argparse import Namespace
from contextlib import asynccontextmanager, nullcontext
import json
import os
from pathlib import Path
import shutil
import time
import tomllib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from harbor.models.job.config import JobConfig
from harbor.models.task.config import TaskConfig
from harbor.models.trial.config import TrialConfig
from harbor.trial.errors import AgentTimeoutError
from harbor.trial.single_step import SingleStepTrial

from tcsexam.cli import main
from tcsexam.layout import repository


@pytest.mark.parametrize('agent', ('kimi-code', 'claude-code', 'codex', 'grok-build'))
def test_prepared_jobs_use_actual_seconds_for_all_task_budgets(tmp_path, agent):
    root = repository()
    paths = sorted((root / 'tasks').rglob('task.toml'))
    assert len(paths) == 130
    output = tmp_path / 'job.json'
    # Materialization is irrelevant to the clock and may require image inputs.
    # Keep the real CLI, generated job schema and Harbor timeout resolver.
    tasks = [{'path': str(paths[0].parent)}]
    with patch.dict(os.environ, {}, clear=True), patch(
            'tcsexam.runtime.materialize', return_value=(tasks, [])):
        main(['prepare', '--root', str(root), '--suite', 'lite',
              '--agent', agent, '--model', 'clock-test-model',
              '--task', 'discrete-bidding-games', '--cache', str(tmp_path / 'cache'),
              '--output', str(output)])
    job = JobConfig.model_validate(json.loads(output.read_text()))
    assert job.timeout_multiplier == 1.0
    for path in paths:
        definition = TaskConfig.model_validate(tomllib.loads(path.read_text()))
        trial = object.__new__(SingleStepTrial)
        trial.config = TrialConfig(task={'path': path.parent}, agent=job.agents[0],
                                   verifier=job.verifier, timeout_multiplier=job.timeout_multiplier)
        trial.task = SimpleNamespace(config=definition)
        assert definition.agent.timeout_sec == 43200, path
        assert trial._compute_agent_timeout_sec() == 43200, path
        assert trial._compute_verifier_timeout_sec() == definition.verifier.timeout_sec, path
        assert trial._compute_environment_build_timeout_sec() == definition.environment.build_timeout_sec, path
        assert trial._compute_agent_setup_timeout_sec() == 360, path


@asynccontextmanager
async def _no_network_transition(*args, **kwargs):
    yield


def test_harbor_agent_timeout_uses_elapsed_seconds_and_cancels_execution():
    async def exercise():
        finished = asyncio.Event()

        async def execution(**kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                finished.set()

        trial = object.__new__(SingleStepTrial)
        trial.agent = SimpleNamespace(extra_env={}, run=execution)
        trial.user_agent = None
        trial.agent_environment = SimpleNamespace(
            with_default_user=lambda user: nullcontext(),
            scoped_exec_env=lambda env: nullcontext())
        trial._emit = AsyncMock()
        trial._network_plan = lambda step: SimpleNamespace(agent_env_baseline=None, agent_phase=None)
        trial._phase_network_policy = _no_network_transition
        trial._log_context = lambda *args: nullcontext()
        result = SimpleNamespace()
        start = time.monotonic()
        with pytest.raises(AgentTimeoutError, match='0.2 seconds'):
            await trial._run_agent_phase(target=result, instruction='', timeout_sec=0.2, user=None)
        elapsed = time.monotonic() - start
        assert finished.is_set(), 'The timed-out agent must be cancelled'
        # Generous scheduling tolerance, while rejecting a tenfold time scale.
        assert 0.15 <= elapsed < 1.8, elapsed
        assert result.agent_execution.finished_at is not None

    asyncio.run(exercise())


def test_external_service_materialization_preserves_budgets_and_all_client_waits(tmp_path):
    from tcsexam.layout import selection
    from tcsexam.runtime import materialize
    from tcsexam.solver_capacity import standard_client_timing

    root = repository()
    _, rows = selection(root, 'full', track='solver', solver_protocol='online')
    assert len(rows) == 30

    def copy_task_config(source, destination, **kwargs):
        # This test exercises task rendering, without copying unrelated payloads.
        destination.mkdir(parents=True)
        shutil.copy2(source / 'task.toml', destination / 'task.toml')

    args = Namespace(output=tmp_path / 'job.json', attempts=1, suite='full',
                     cache=tmp_path / 'cache', judge_url='https://judge.example.invalid',
                     image_map=None)
    with patch.dict(os.environ, {}, clear=True), patch('tcsexam.runtime.resolved_images', return_value=({}, {})), patch(
            'tcsexam.runtime.shutil.copytree', side_effect=copy_task_config):
        tasks, records = materialize(root, rows, args)
    for row, task, record in zip(rows, tasks, records):
        original = tomllib.loads((root / row['path'] / 'task.toml').read_text())
        rendered = tomllib.loads((Path(task['path']) / 'task.toml').read_text())
        assert rendered['agent']['timeout_sec'] == 43200
        assert rendered['environment']['cpus'] == original['environment']['cpus']
        assert rendered['environment']['memory_mb'] == original['environment']['memory_mb']
        assert rendered['verifier']['timeout_sec'] >= original['verifier']['timeout_sec']
        assert record['resource_plan'] is None
        for split, phase in (('public', 'environment'), ('hidden', 'verifier')):
            timing = record['standard_client_timing'][split]
            defaults = timing['client_defaults_seconds']
            env = rendered[phase]['env']
            assert int(env['TCSEXAM_SESSION_TTL']) >= defaults['SESSION_TTL']
            assert int(env['TCSEXAM_POLL_TIMEOUT']) >= defaults['POLL_TIMEOUT']
            assert int(env['TCSEXAM_SESSION_TTL']) >= timing['standard_timeouts_seconds']['worker_ttl_seconds']
            assert int(env['TCSEXAM_POLL_TIMEOUT']) >= timing['standard_timeouts_seconds']['poll_timeout_seconds']
            assert 'TCSEXAM_N_SHARDS' not in env
            assert 'TCSEXAM_WORKER_CPUS' not in env
            assert timing['solver_budget_changed'] is False
        assert rendered['verifier']['timeout_sec'] > float(rendered['verifier']['env']['TCSEXAM_POLL_TIMEOUT'])
    # Both independent instances and a shared time pool exceeded old hidden TTLs.
    dfvs = standard_client_timing(root, 'dfvs-pace2022', 'hidden')
    assert dfvs['source']['per_instance_seconds'] == 1800
    assert dfvs['source']['standard_shards'] == 10
    assert int(dfvs['env']['TCSEXAM_SESSION_TTL']) >= 39600
    assert dfvs['client_defaults_seconds']['SESSION_TTL'] == 21600
    logic = standard_client_timing(root, 'logic-syn-iwls2023', 'hidden')
    assert logic['source']['pool'] and logic['source']['standard_shards'] == 1
    assert int(logic['env']['TCSEXAM_SESSION_TTL']) > logic['source']['total_pool_seconds']


def test_prepared_backend_plan_keeps_its_own_capacity_specific_timeouts(tmp_path):
    from tcsexam.layout import selection
    from tcsexam.runtime import materialize

    root = repository()
    _, rows = selection(root, 'full', task='ce-pace2021', solver_protocol='online')
    plan = {'tasks': {'ce-pace2021': {
        split: {'env': {'TCSEXAM_N_SHARDS': '2', 'TCSEXAM_SESSION_TTL': '100000',
                        'TCSEXAM_POLL_TIMEOUT': '101000'}, 'verifier_timeout_seconds': 102000}
        for split in ('public', 'hidden')}}}
    args = Namespace(output=tmp_path / 'job.json', attempts=1, suite='full',
                     cache=tmp_path / 'cache', judge_url='https://judge.example.invalid', image_map=None)
    with patch.dict(os.environ, {}, clear=True), patch('tcsexam.backend_cli.client_plan', return_value=plan), patch(
            'tcsexam.runtime.resolved_images', return_value=({}, {})):
        tasks, records = materialize(root, rows, args)
    rendered = tomllib.loads((Path(tasks[0]['path']) / 'task.toml').read_text())
    assert rendered['verifier']['timeout_sec'] == 102000
    assert rendered['verifier']['env']['TCSEXAM_N_SHARDS'] == '2'
    assert rendered['environment']['env']['TCSEXAM_POLL_TIMEOUT'] == '101000'
    assert records[0]['standard_client_timing'] is None
    assert records[0]['resource_plan'] == plan['tasks']['ce-pace2021']
