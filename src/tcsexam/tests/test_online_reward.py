"""Harbor's numeric reward and the full judging evidence use separate files."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
import pytest
from harbor.models.verifier.result import VerifierResult
from tcsexam.layout import repository
from tcsexam.online_reward import sync

WRITERS = {'_write_json_atomic', '_write_harbor_result', 'write_reward', 'write_violation'}
PATHS = sorted((repository() / 'tasks/solver/online').glob('*/tests/fetch_final.py'))


def scope(path, output):
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in WRITERS]
    namespace = {'os': os, 'json': json, 'tempfile': tempfile,
                 'REWARD_JSON': str(output / 'reward.json'), 'REWARD_TXT': str(output / 'reward.txt')}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


@pytest.mark.parametrize('path', PATHS, ids=lambda p: p.parent.parent.name)
def test_every_online_writer_preserves_full_detail_and_harbor_numeric_reward(path, tmp_path):
    namespace = scope(path, tmp_path)
    extra = {'counts': {'valid': 1}, 'per_instance': {'a': {'A': 24, 'status': 'ok'}},
             'history': [{'submission': 0}], 'metric_version': 'fixed', 'final_score': -0.25}
    namespace['write_reward'](-0.25, 'ok', extra=extra)
    reward = json.loads((tmp_path / 'reward.json').read_text())
    assert reward == {'reward': -0.25}
    assert VerifierResult(rewards=reward).rewards == reward
    assert (tmp_path / 'reward.txt').read_text() == '-0.25'
    detail = json.loads((tmp_path / 'score-details.json').read_text())
    assert detail == {'reward': -0.25, 'best': -0.25, 'note': 'ok', **extra}


def test_violation_keeps_numeric_zero_and_complete_reason_chain(tmp_path):
    namespace = scope(PATHS[0], tmp_path)
    namespace['write_violation'](3, 1, note='checked', chain=['agent', 'verifier'], agent_hidden=2)
    reward = json.loads((tmp_path / 'reward.json').read_text())
    assert reward == {'reward': 0.0}
    assert VerifierResult(rewards=reward).rewards == reward
    detail = json.loads((tmp_path / 'score-details.json').read_text())
    assert detail['violation'] == 'hidden_channel_used_by_agent'
    assert detail['chain'] == ['agent', 'verifier'] and detail['agent_hidden_submissions'] == 2


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), True, '0'])
def test_invalid_reward_never_creates_a_success_file(tmp_path, value):
    namespace = scope(PATHS[0], tmp_path)
    with pytest.raises(ValueError, match='finite number'):
        namespace['_write_harbor_result']({'reward': value, 'note': 'not completed'})
    assert not (tmp_path / 'reward.json').exists()
    assert not (tmp_path / 'reward.txt').exists()


def test_detail_write_failure_cannot_report_zero_or_damage_submissions(tmp_path):
    namespace = scope(PATHS[0], tmp_path)
    archive = tmp_path / 'submissions.json';archive.write_text('{"untouched":true}')
    def fail(*args):
        raise OSError('fixture detail write failed')
    namespace['_write_json_atomic'] = fail
    with pytest.raises(OSError, match='detail write failed'):
        namespace['write_reward'](0, 'ok', extra={'counts': {}})
    assert not (tmp_path / 'reward.json').exists() and not (tmp_path / 'reward.txt').exists()
    assert archive.read_text() == '{"untouched":true}'


def test_generated_writers_are_current():
    assert sync(repository(), check=True)['online_tasks'] == 30


def test_details_cannot_overwrite_the_numeric_reward(tmp_path):
    namespace = scope(PATHS[0], tmp_path)
    with patch.dict(os.environ, {'SCORE_DETAILS_JSON': str(tmp_path / 'reward.json')}):
        with pytest.raises(ValueError, match='separate paths'):
            namespace['write_reward'](0, 'ok')
    assert not (tmp_path / 'reward.json').exists()
