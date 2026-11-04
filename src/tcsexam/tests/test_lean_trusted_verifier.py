"""Regression checks for the boundary between final sources and fixed judging inputs."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / 'tasks/construction/cage-girth/tests/trusted_verifier.py'
spec = importlib.util.spec_from_file_location('trusted_lean_verifier', RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_submission_policy_keeps_open_auxiliary_sources_only(tmp_path):
    (tmp_path / 'Task').mkdir()
    (tmp_path / 'Task/Basic.lean').write_text('main')
    (tmp_path / 'Task/Helpers.lean').write_text('helpers')
    (tmp_path / 'Task/Helpers.olean').write_text('untrusted compiled code')
    (tmp_path / 'lakefile.lean').write_text('untrusted build code')
    assert runner.collect_submission(tmp_path, 'basic-only') == {'Task/Basic.lean': b'main'}
    assert runner.collect_submission(tmp_path, 'task-lean-sources') == {
        'Task/Basic.lean': b'main', 'Task/Helpers.lean': b'helpers'}


def test_submission_symlink_is_rejected(tmp_path):
    (tmp_path / 'Task').mkdir()
    (tmp_path / 'payload').write_text('invalid')
    (tmp_path / 'Task/Basic.lean').symlink_to(tmp_path / 'payload')
    with pytest.raises(ValueError, match='symbolic links'):
        runner.collect_submission(tmp_path, 'basic-only')


@pytest.mark.parametrize('value', [float('nan'), float('inf'), True, {'reward': 1}])
def test_invalid_reward_is_never_published(tmp_path, value):
    target = tmp_path / 'reward.txt'
    with pytest.raises(ValueError, match='numeric reward'):
        runner.publish_reward(target, value)
    assert not target.exists()


@pytest.mark.parametrize('scorer_exit', [0, 7])
def test_real_entry_uses_trusted_project_and_clears_stale_reward(tmp_path, scorer_exit):
    tests = tmp_path / 'tests'
    tests.mkdir()
    shutil.copyfile(RUNNER, tests / 'trusted_verifier.py')
    shutil.copyfile(RUNNER.with_name('lean_security.py'), tests / 'lean_security.py')
    trusted = tmp_path / 'trusted'
    (trusted / 'Task').mkdir(parents=True)
    (trusted / 'lakefile.toml').write_text('trusted dependency lock')
    dependency = trusted / '.lake/packages/batteries/.lake/build/lib/lean/Batteries.olean'
    dependency.parent.mkdir(parents=True)
    dependency.write_text('trusted compiled dependency')
    stale_project = trusted / '.lake/build/lib/lean/Task/Basic.olean'
    stale_project.parent.mkdir(parents=True)
    stale_project.write_text('stale project compilation')
    app = tmp_path / 'submission'
    (app / 'Task').mkdir(parents=True)
    (app / 'Task/Basic.lean').write_text('submitted source')
    (app / 'lakefile.toml').write_text('tampered')
    (tests / 'submission-policy.json').write_text(json.dumps({
        'policy': 'basic-only', 'trusted_app': str(trusted)}))
    (tests / 'score.py').write_text('''import argparse, pathlib, sys
p=argparse.ArgumentParser()
p.add_argument('--app');p.add_argument('--tests');p.add_argument('--reward')
a=p.parse_args()
assert pathlib.Path(a.app, 'lakefile.toml').read_text() == 'trusted dependency lock'
assert pathlib.Path(a.app, 'Task/Basic.lean').read_text() == 'submitted source'
assert pathlib.Path(a.app, '.lake/packages/batteries/.lake/build/lib/lean/Batteries.olean').read_text() == 'trusted compiled dependency'
assert not pathlib.Path(a.app, '.lake/build').exists()
pathlib.Path(a.reward).write_text('1.75')
sys.exit(''' + str(scorer_exit) + ')\n')
    output = tmp_path / 'output'
    output.mkdir()
    (output / 'reward.json').write_text('{"reward": 99, "details": []}')
    (output / 'reward.txt').write_text('99')
    process = subprocess.run([sys.executable, '-I', str(tests / 'trusted_verifier.py')],
        env={**os.environ, 'APP_DIR': str(app), 'REWARD_FILE': str(output / 'reward.txt')},
        capture_output=True, text=True)
    assert not (output / 'reward.json').exists()
    if scorer_exit:
        assert process.returncode != 0
        assert not (output / 'reward.txt').exists()
    else:
        assert process.returncode == 0, process.stderr
        assert float((output / 'reward.txt').read_text()) == 1.75
        manifest = json.loads((output / 'submission-manifest.json').read_text())
        assert [x['path'] for x in manifest['files']] == ['Task/Basic.lean']


def test_all_tasks_share_entry_and_preserve_declared_source_rules():
    import tomllib
    tasks = [p for track in ('theorem', 'construction', 'open')
             for p in (ROOT / 'tasks' / track).iterdir() if (p / 'task.toml').is_file()]
    assert len(tasks) == 70
    for task in tasks:
        assert (task / 'tests/trusted_verifier.py').read_bytes() == RUNNER.read_bytes()
        policy = json.loads((task / 'tests/submission-policy.json').read_text())
        assert policy['policy'] == ('task-lean-sources' if task.parent.name == 'open' else 'basic-only')
        assert (task / 'tests/test.sh').stat().st_mode & 0o111
        config = tomllib.loads((task / 'task.toml').read_text())
        assert config['verifier']['environment']
        assert config['agent']['timeout_sec'] == 43200
        assert '/logs/verifier/reward.json' not in (task / 'tests/score.py').read_text()
