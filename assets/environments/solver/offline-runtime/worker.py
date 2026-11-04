# SPDX-License-Identifier: Apache-2.0
"""Run a frozen checker in a fresh Docker worker, preserving its time rules."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
runtime = Path('/judge')
if not (runtime / 'execution.py').is_file():
    runtime = next(parent / 'assets/environments/solver/judge-runtime'
                   for parent in Path(__file__).resolve().parents
                   if (parent / 'assets/environments/solver/judge-runtime/execution.py').is_file())
sys.path.insert(0, str(runtime))
from execution import install, own_tree, validate_tree, supervise_script
import time


def restricted_reference(reference, keys, pooled):
    expected = set(reference['instances'])
    if len(keys) != len(set(keys)) or not set(keys) <= expected:
        raise RuntimeError('Worker instance selection is invalid')
    if pooled and set(keys) != expected:
        raise RuntimeError('A shared time pool requires the complete instance set')
    result = dict(reference)
    result['instances'] = {key: reference['instances'][key] for key in keys}
    # Checkers that apply a shard selector use the restricted instance count.
    return result


def checked_records(result, reference):
    records = result.get('per_instance') or result.get('per_instance_detail', {})
    build_error = result.get('build_error') or result.get('compile_error')
    if build_error:
        records = {key: dict(B=value.get('B'), K=value.get('K'), A=None,
                             seconds=0, status='build_error', error=build_error)
                   for key, value in reference['instances'].items()}
    if not isinstance(records, dict) or set(records) != set(reference['instances']):
        raise RuntimeError('Checker did not report every assigned instance')
    for key, record in records.items():
        if not isinstance(record, dict):
            raise RuntimeError(f'Invalid checker record: {key}')
        if record.get('status') == 'instance file missing on judge side':
            raise RuntimeError(f'Judge data unavailable: {key}')
    return records


def preparation_files(directory, all_keys, selected, suffix):
    """Keep only assigned compressed inputs for the frozen unpack script.

    This changes the worker's private input view, like the restricted
    reference. Original compressed bytes and unpack commands are retained.
    It prevents every independent unit from unpacking the entire library.
    """
    found = set()
    removals = []
    for path in directory.rglob('*'):
        if not path.is_file() or not path.name.endswith(suffix):
            continue
        key = path.name[:-len(suffix)]
        if key not in all_keys:
            continue
        if key in selected:
            found.add(key)
        else:
            removals.append(path)
    if found != set(selected):
        raise RuntimeError('Judge data unavailable for selected preparation inputs')
    for path in removals:
        path.unlink()


def main():
    config = json.loads(Path('/opt/public_judge/task.json').read_text())
    keys = json.loads(os.environ['TCS_UNIT_KEYS'])
    path = Path('/tests/reference.json')
    full = json.loads(path.read_text())
    reference = restricted_reference(full, keys, config['pool'])
    if config.get('compressed_preparation'):
        preparation_files(Path('/tests/instances'), set(full['instances']),
                          set(keys), config['compressed_preparation'])
    path.write_text(json.dumps(reference))
    Path('/work').mkdir(exist_ok=True)
    Path('/logs/verifier').mkdir(parents=True, exist_ok=True)
    validate_tree('/submission/app')
    shutil.rmtree('/app', ignore_errors=True)
    shutil.move('/submission/app', '/app')
    own_tree("/app")
    install(config)
    result_path = Path('/work/checker-result.json')
    environment = dict(os.environ)
    environment.update(config.get('judge_env', {}))
    environment.update(JUDGE_JOBS='1', REWARD_PATH=str(result_path),
                       INSTANCE_SHARD='' if config['pool'] else '0/1')
    environment['TCSEXAM_PYTHON_EXECUTABLE'] = sys.executable
    environment['PATH'] = '/opt/public_judge/bin:' + environment.get('PATH', '')
    environment.pop('INSTANCE_SET', None)
    started = time.time()
    log_path = Path('/logs/verifier/checker.log')
    with log_path.open('wb') as log:
        # The frozen script retains decompression and task-specific exports.
        # Its Python checker call is redirected through our CPU-affinity
        # adapter; all original checker/scoring bytes remain unchanged.
        process = subprocess.run(['bash', '/opt/public_judge/frozen-test.sh'],
                                 env=environment, cwd='/work', stdout=log,
                                 stderr=subprocess.STDOUT)
    if process.returncode or not result_path.is_file():
        raise RuntimeError(f'Checker exited {process.returncode}; see checker.log')
    result = json.loads(result_path.read_text())
    records = checked_records(result, reference)
    result.update(per_instance=records, unit_started_at=started,
                  unit_wall_seconds=time.time()-started,
                  cpu_affinity=sorted(os.sched_getaffinity(0)))
    Path('/logs/verifier/unit.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    supervise_script(__file__, main)
