#!/usr/bin/env python3
"""Grade declared source files in an image-owned project and dependency tree."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

# Load the image-owned shared checks without using the submission's import path.
import importlib.util as _import_util
_security_spec = _import_util.spec_from_file_location(
    "tcsexam_lean_security", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lean_security.py"))
_security = _import_util.module_from_spec(_security_spec)
_security_spec.loader.exec_module(_security)


def collect_submission(source, policy):
    source = Path(source)
    task = source / 'Task'
    if source.is_symlink() or task.is_symlink():
        raise ValueError('Submission directories must not be symbolic links')
    paths = [task / 'Basic.lean']
    if policy == 'task-lean-sources' and task.is_dir():
        paths += [p for p in sorted(task.rglob('*.lean')) if p != task / 'Basic.lean']
    result = {}
    for path in paths:
        if not path.exists() and path == task / 'Basic.lean':
            continue
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != source.parent):
            raise ValueError('Submission source files must not use symbolic links')
        if not path.is_file():
            raise ValueError('Submission source must be a regular file: ' + str(path.relative_to(source)))
        data = path.read_bytes()
        try:
            error = _security.source_error(data.decode('utf-8'), allow_native=policy != 'task-lean-sources')
        except UnicodeDecodeError:
            error = 'Lean source must be UTF-8'
        if error:
            raise ValueError(str(path.relative_to(source)) + ': ' + error)
        result[path.relative_to(source).as_posix()] = data
    return result


def prepare_project(trusted_app, app, submitted):
    trusted_app, app = Path(trusted_app), Path(app)
    shutil.copytree(trusted_app, app, symlinks=True,
                    ignore=lambda folder, names: ['build'] if Path(folder) == trusted_app / '.lake' else [])
    # Keep fixed dependency caches while removing stale project compilation.
    shutil.rmtree(app / 'Task', ignore_errors=True)
    (app / 'Task').mkdir()
    for relative, data in submitted.items():
        destination = app / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)


def publish_reward(path, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Scorer did not produce a finite numeric reward')
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(str(value) + '\n')
    temporary.replace(path)


def main():
    tests = Path(__file__).resolve().parent
    config = json.loads((tests / 'submission-policy.json').read_text())
    output = Path(os.environ.get('REWARD_FILE', '/logs/verifier/reward.txt')).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    for name in ('reward.txt', 'reward.json', 'score-details.json', 'judge_result.json'):
        (output.parent / name).unlink(missing_ok=True)
    output.unlink(missing_ok=True)
    source = Path(os.environ.get('APP_DIR', '/app'))
    try:
        submitted = collect_submission(source, config['policy'])
    except ValueError as error:
        (output.parent / 'score-details.json').write_text(json.dumps({'valid': False, 'error': str(error)}))
        publish_reward(output, 0.0)
        return 0
    provenance = {'policy': config['policy'], 'files': [
        {'path': path, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        for path, data in sorted(submitted.items())]}
    (output.parent / 'submission-manifest.json').write_text(json.dumps(provenance, indent=2) + '\n')
    with tempfile.TemporaryDirectory(prefix='tcsexam-verifier-') as directory:
        directory = Path(directory)
        app = directory / 'app'
        prepare_project(config['trusted_app'], app, submitted)
        reward = directory / 'reward.txt'
        details = directory / 'score-details.json'
        environment = {k: v for k, v in os.environ.items()
                       if not k.startswith(('PYTHON', 'LEAN_', 'LAKE_'))}
        environment.update(APP_DIR=str(app), REWARD_FILE=str(reward), REWARD_JSON=str(details))
        process = subprocess.run([sys.executable, '-I', str(tests / 'score.py'), '--app', str(app),
                                  '--tests', str(tests), '--reward', str(reward)],
                                 cwd=app, env=environment)
        for name in ('score-details.json', 'judge_result.json'):
            candidate = directory / name
            if candidate.is_file():
                shutil.copyfile(candidate, output.parent / name)
        if process.returncode:
            raise RuntimeError('Scorer process failed with exit code ' + str(process.returncode))
        value = float(reward.read_text())
        # Preserve scores above the reference result; never clamp to one.
        publish_reward(output, value)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
