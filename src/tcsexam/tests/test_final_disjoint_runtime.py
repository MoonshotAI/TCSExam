"""Keep selected final inputs consistent across both execution protocols."""
import ast
import hashlib
import json
import os
from pathlib import Path

import pytest

from tcsexam.solver_capacity import plan_solver_capacity, solver_task_spec


ROOT = Path(__file__).resolve().parents[3]
SELECTION = ROOT / 'assets/data/solver/final-evaluation-selection.json'
TASKS = {
    'maxsat-mse': (200, 11, 300, 32768, 177),
    'radiation-mznchallenge': (36, 15, 1200, 16384, 25),
}
# The public self-test contract is unchanged by the final-set selection.
PUBLIC_SHA256 = {
    'maxsat-mse/environment/app/public_reference.json':
        '7068253fbbb027babbcb6bbdd8f84b10558442b087c2bf92168b368df80d7896',
    'maxsat-mse/environment/submit.sh':
        '64abf45b90cda25af64bd97d2547433f8edc305e7153af43d8c2b34d1a864424',
    'radiation-mznchallenge/environment/app/public_reference.json':
        'aec3a17b9cf30212acdf272677f1ada5550b9f0227d7a616708a0481da2dbb7d',
    'radiation-mznchallenge/environment/submit.sh':
        'b9820302b276eb32877d7a6e7a57b199dfddebc28c64d20f0c7131b849d4d0fd',
}


def load(path):
    return json.loads(path.read_text())


@pytest.mark.parametrize('task', TASKS)
def test_final_execution_and_metric_keys_match_the_declared_selection(task):
    selection = load(SELECTION)
    selected = selection['tasks'][task]
    retained = set(selected['retained_keys'])
    excluded = set(selected['excluded_keys'])
    count, public_count, seconds, memory, denominator = TASKS[task]
    assert len(retained) == count
    assert len(excluded) == 11
    assert retained.isdisjoint(excluded)
    online = ROOT / 'tasks/solver/online' / task
    offline = ROOT / 'tasks/solver/offline' / task
    for directory in (online, offline):
        reference = load(directory / 'tests/reference.json')
        anchors = load(directory / 'tests/anchors.json')
        assert reference['evaluation_selection'] == selection['id']
        assert set(reference['instances']) == retained
        assert set(anchors['B']) == set(anchors['K']) == retained
        for name, values in reference['instances'].items():
            assert (anchors['B'][name], anchors['K'][name]) == (values['B'], values['K'])
        assert sum(value['B'] > value['K'] for value in reference['instances'].values()) == denominator
        if task == 'radiation-mznchallenge':
            assert reference['per_instance_seconds'] == seconds
    for leaf in ('reference.json', 'anchors.json', 'checker.py', 'metric_config.json',
                 'metric/engine.py', 'metric/config.py'):
        assert (online / 'tests' / leaf).read_bytes() == (offline / 'tests' / leaf).read_bytes()
    runtime = load(offline / 'tests/runtime/task.json')
    assert runtime['instance_count'] == count
    assert (runtime['seconds'], runtime['cpus'], runtime['memory_mb'], runtime['pool']) == (
        seconds, 1, memory, False)
    metadata = load(online / 'metadata.json')['judging']
    assert (metadata['n_hidden'], metadata['shipped_judged'], metadata['n_public']) == (
        count, 0, public_count)
    adapter = load(offline / 'offline-adapter.json')
    assert adapter['evaluation_selection'] == selection['id']
    for entry in adapter['preserved_judge_inputs']:
        source = (ROOT / entry['source']).read_bytes()
        assert source == (ROOT / entry['target']).read_bytes()
        assert hashlib.sha256(source).hexdigest() == entry['sha256']


@pytest.mark.parametrize('task', TASKS)
def test_final_count_changes_keep_public_inputs_and_single_worker_budgets(task):
    count, public_count, seconds, memory, _ = TASKS[task]
    hidden = solver_task_spec(ROOT, task, 'hidden')
    public = solver_task_spec(ROOT, task, 'public')
    assert (hidden['instance_count'], public['instance_count']) == (count, public_count)
    assert hidden['standard_shards'] == public['standard_shards'] == 10
    for spec in (hidden, public):
        assert spec['per_instance_seconds'] == seconds
        assert spec['scoring_unit']['cpu_count'] == 1
        assert spec['scoring_unit']['memory_mb'] == memory
        # A small host may run just one shard; its lifecycle must still fit.
        for shards in (1, 10):
            plan = plan_solver_capacity(
                standard_shards=10, requested_shards=shards,
                worker_cpu_count=1, worker_memory_mb=memory,
                available_cpu_count=shards, available_memory_mb=shards * memory,
                instance_count=spec['instance_count'], per_instance_seconds=seconds,
                build_seconds=spec['build_seconds'], check_seconds=spec['check_seconds'],
                baked_judge_timeout_seconds=spec['baked_judge_timeout_seconds'])
            assert plan['effective']['shards'] == shards
            assert plan['effective']['per_instance_seconds'] == seconds
            assert not plan['requires_image_timeout_update']
            assert not plan['solver_budget_changed']
    for relative, digest in PUBLIC_SHA256.items():
        if relative.startswith(task + '/'):
            assert hashlib.sha256((ROOT / 'tasks/solver/online' / relative).read_bytes()).hexdigest() == digest


def test_maxsat_size_balanced_sharding_covers_retained_keys_with_numbering_gaps(tmp_path):
    task = 'maxsat-mse'
    keys = load(SELECTION)['tasks'][task]['retained_keys']
    assert 'ex098.wcnf' in keys and 'ex100.wcnf' in keys and 'ex099.wcnf' not in keys
    for index, name in enumerate(keys):
        (tmp_path / name).write_bytes(b'x' * (1 + index % 17))
    path = ROOT / 'tasks/solver/online' / task / 'tests/checker.py'
    definition = next(node for node in ast.parse(path.read_text()).body
                      if isinstance(node, ast.FunctionDef) and node.name == '_shard_slice')
    namespace = {'os': os, 'INSTANCES_DIR': str(tmp_path), 'INSTANCE_SHARD': 'test'}
    exec(compile(ast.Module(body=[definition], type_ignores=[]), str(path), 'exec'), namespace)
    slices = [namespace['_shard_slice'](keys, index, 10)[0] for index in range(10)]
    flattened = [key for part in slices for key in part]
    assert len(flattened) == len(set(flattened)) == 200
    assert set(flattened) == set(keys)
    assert all(len(part) == 20 for part in slices)
