# SPDX-License-Identifier: Apache-2.0
"""One isolated judging unit; bin packing always retains its full time pool."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
runtime = Path('/judge')
if not (runtime / 'execution.py').is_file():
    runtime = next(parent / 'assets/environments/solver/judge-runtime'
                   for parent in Path(__file__).resolve().parents
                   if (parent / 'assets/environments/solver/judge-runtime/execution.py').is_file())
sys.path.insert(0, str(runtime))
from execution import install, own_tree, validate_tree, supervise_script
import time


def validate_judge_data(records):
    for key, rec in records.items():
        # Missing proof files and missing schedule entries are invalid solver
        # outputs. Only the scorer's explicit missing-instance marker denotes
        # unavailable infrastructure.
        if rec.get('status') == 'instance file missing on judge side':
            raise RuntimeError(f'Judge data unavailable: {key}: {rec["status"]}')


def main():
    cfg = json.loads(Path('/opt/public_judge/task.json').read_text())
    subset = json.loads(os.environ['TCS_UNIT_KEYS'])
    full = json.loads(Path('/tests/reference.json').read_text())
    if cfg['pool'] and sorted(subset) != sorted(full['instances']):
        raise RuntimeError('Bin packing requires the complete instance set')
    full['instances'] = {k: full['instances'][k] for k in subset}
    Path('/work').mkdir(exist_ok=True)
    Path('/logs/verifier').mkdir(parents=True, exist_ok=True)
    Path('/work/reference.json').write_text(json.dumps(full))
    validate_tree('/submission/app')
    shutil.rmtree('/app', ignore_errors=True)
    shutil.move('/submission/app', '/app')
    own_tree("/app")
    install(cfg)
    os.chdir('/app')
    # Every unit has a fresh filesystem and a Docker-enforced CPU/memory limit.
    # The existing scoring module starts the solver timer after compilation.
    os.environ['JUDGE_JOBS'] = '1'
    os.environ['PER_INSTANCE_SECONDS'] = str(cfg['seconds'])
    os.environ['BUILD_TIMEOUT'] = str(cfg['build_seconds'])
    if cfg['pool']:
        os.environ['TOTAL_TIME_POOL'] = str(cfg['seconds'])
    sys.path.insert(0, cfg['module_dir'])
    spec = importlib.util.spec_from_file_location('scoring', '/opt/public_judge/scoring.py')
    scoring = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scoring)
    started = time.time()
    result = scoring.main(['scoring.py', '/app', cfg['instances_dir'], '/work/reference.json'])
    records = result.get('per_instance', result.get('per_instance_detail', {}))
    if result.get('build_error'):
        records = {key: dict(B=v['B'], K=v['K'], A=None, seconds=0,
                            status='build_error', error=result['build_error'])
                   for key, v in full['instances'].items()}
    if set(records) != set(subset):
        raise RuntimeError(f'Incomplete instance coverage: {set(subset)-set(records)}')
    validate_judge_data(records)
    result.update(per_instance=records, unit_started_at=started,
                  unit_wall_seconds=time.time()-started, cpu_affinity=sorted(os.sched_getaffinity(0)))
    Path('/logs/verifier/unit.json').write_text(json.dumps(result, indent=2))

if __name__ == '__main__':
    supervise_script(__file__, main)
