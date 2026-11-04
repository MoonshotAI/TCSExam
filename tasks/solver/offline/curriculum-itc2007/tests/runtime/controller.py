# SPDX-License-Identifier: Apache-2.0
"""Harbor verifier: schedule isolated units and recompute the existing metric."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import sys
import tarfile
import tempfile
import time

from admission import PREFIX, daemon_capacity, identify_controller, reserve
from docker_api import Docker, DockerError
from resources import EnvironmentUnavailable, MIB, slots

OUT = Path('/logs/verifier')


class ArchiveUploadUnavailable(EnvironmentUnavailable):
    """A created owned worker rejected its initial root archive upload."""


def upload_submission(docker, cid, archive, cfg, owner):
    try:
        with open(archive, 'rb') as f:
            docker.put_archive(cid, '/', f)
    except DockerError as exc:
        try:
            message = json.loads(exc.message).get('message')
        except (ValueError, AttributeError):
            raise exc
        if exc.status != 404 or message != f'Could not find the file / in container {cid}':
            raise
        try:
            info = docker.inspect(cid)
        except Exception as inspection_error:
            raise EnvironmentUnavailable(
                f'Initial archive upload failed: {exc}; worker inspection also failed: '
                f'{inspection_error}') from exc
        state = info['State']
        labels = info['Config'].get('Labels') or {}
        if (info['Id'] != cid or state.get('Status') != 'created' or
                state.get('Running') or state.get('Pid', 0) != 0 or
                labels.get(PREFIX+'.owner') != owner or
                labels.get(PREFIX+'.unit') != cfg['task']):
            raise
        raise ArchiveUploadUnavailable(str(exc)) from exc


def retry_upload_failure(exc, cid, group, failures, pending, trace):
    key = tuple(group)
    failures[key] = failures.get(key, 0)+1
    trace['events'].append({'event':'archive_upload_failed', 'keys':group,
        'container':cid, 'attempt':failures[key], 'maximum_attempts':3,
        'time':time.time(), 'reason':str(exc),
        'recovery':'remove_created_worker_and_reserve_new_worker'})
    if failures[key] >= 3:
        raise EnvironmentUnavailable(f'Initial archive upload failed after 3 workers: {exc}') from exc
    pending.insert(0, group)


def release_workers(docker, active, trace):
    failures = []
    for future, (cid, _) in list(active.items()):
        try:
            docker.remove(cid)
        except Exception as exc:
            failures.append(cid)
            trace['events'].append({'event':'worker_cleanup_failed', 'container':cid,
                                    'time':time.time(), 'reason':str(exc)})
        else:
            del active[future]
    write('resources.json', trace)
    return failures


def write(name, value):
    path = OUT / name
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True))
    temp.replace(path)


def submission_archive():
    root = Path('/app')
    if not root.is_dir():
        raise EnvironmentUnavailable('Harbor did not transfer the final /app artifact')
    # Plain archive avoids repeatedly compressing large compiler artifacts.
    dest = tempfile.TemporaryFile()
    with tarfile.open(fileobj=dest, mode='w') as tar:
        tar.add(root, arcname='submission/app', recursive=True)
    dest.seek(0)
    return dest


def tar_json(blob, name):
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        candidates = [m for m in tar if m.isfile() and Path(m.name).name == name]
        if len(candidates) != 1:
            raise EnvironmentUnavailable(f'Worker did not produce exactly one {name}')
        return json.load(tar.extractfile(candidates[0]))


def execute(docker, cid, archive, cfg, owner):
    # Archive file handles are independent, safe for parallel uploads.
    upload_submission(docker, cid, archive, cfg, owner)
    docker.start(cid)
    start = time.time()
    info = docker.inspect(cid)
    hc = info['HostConfig']
    if hc['Memory'] != cfg['memory_mb']*MIB or hc['NanoCpus'] != cfg['cpus']*1000000000:
        raise EnvironmentUnavailable('Docker did not retain requested CPU/memory limits')
    timeout = cfg['build_seconds'] + cfg['seconds'] + cfg['check_seconds'] + 300
    try:
        status = docker.wait(cid, timeout)
    except (TimeoutError, OSError) as exc:
        raise EnvironmentUnavailable(f'Worker outer timeout or Docker connection failure: {exc}') from exc
    info = docker.inspect(cid)
    if status['StatusCode'] != 0:
        logs = docker.call('GET', f'/containers/{cid}/logs?stdout=1&stderr=1', raw=True)
        (OUT / (cid[:12]+'.log')).write_bytes(logs)
        if info['State'].get('OOMKilled'):
            # No per-instance result survives a whole-container OOM; infrastructure
            # and solver failures cannot be distinguished safely here.
            raise EnvironmentUnavailable('Worker exceeded its memory limit before producing a verified result')
        raise EnvironmentUnavailable(f'Worker exited {status["StatusCode"]}; see {cid[:12]}.log')
    data = tar_json(docker.archive(cid, '/logs/verifier/unit.json'), 'unit.json')
    data['worker_container'] = cid
    data['container_started_at'] = start
    data['container_wall_seconds'] = time.time()-start
    data['memory_limit_bytes'] = hc['Memory']
    return data


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in ('reward.json', 'reward.txt'):
        (OUT/f).unlink(missing_ok=True)
    cfg = json.loads(Path('/opt/public_judge/task.json').read_text())
    def interrupted(signum, frame):
        raise EnvironmentUnavailable(f'Controller received signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    docker = Docker()
    info = docker.call('GET', '/info')
    if not all(info.get(k) for k in ('MemoryLimit', 'CpuCfsQuota', 'CPUSet')):
        raise EnvironmentUnavailable('Docker must support memory limits, CPU quotas and CPU affinity')
    controller = identify_controller(docker)
    controller_id = controller['Id']
    image = controller['Image']
    cap = daemon_capacity()
    max_jobs = slots(cap, cfg['cpus'], cfg['memory_mb']*MIB, disk_per_unit=cfg['disk_mb']*MIB)
    override = os.environ.get('TCSEXAM_MAX_JOBS')
    if override:
        if not override.isdigit() or int(override) < 1:
            raise EnvironmentUnavailable('TCSEXAM_MAX_JOBS must be a positive integer')
        max_jobs = min(max_jobs, int(override))
    max_jobs = 1 if cfg['pool'] else max_jobs
    reference = json.loads(Path('/tests/reference.json').read_text())
    keys = sorted(reference['instances'])
    units = [keys] if cfg['pool'] else [[key] for key in keys]
    trace = {'format_version': 1, 'status': 'running', 'task': cfg['task'],
             'harbor_version': '0.22.0', 'judge_image': image, 'capacity': cap.json(),
             'unit_resources': cfg, 'initial_max_jobs': max_jobs, 'peak_jobs': 0,
             'events': [], 'instance_count': len(keys),
             'runtime_sha256': {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in Path(__file__).parent.glob('*.py')}}
    write('resources.json', trace)
    pending = list(units)
    active = {}
    records = {}
    results = []
    upload_failures = {}
    temp = tempfile.NamedTemporaryFile(prefix='tcsexam-submission-', delete=False)
    temp.close()
    try:
        with submission_archive() as archived, open(temp.name, 'wb') as dst:
            import shutil
            shutil.copyfileobj(archived, dst, length=1024*1024)
        digest = hashlib.sha256()
        with open(temp.name, 'rb') as f:
            for chunk in iter(lambda: f.read(1024*1024), b''):
                digest.update(chunk)
        trace['submission_sha256'] = digest.hexdigest()
        pool = ThreadPoolExecutor(max_workers=max_jobs)
        try:
            while pending or active:
                changed = False
                for fut in list(active):
                    if not fut.done():
                        continue
                    cid, group = active[fut]
                    try:
                        result = fut.result()
                        expected = set(group)
                        if set(result['per_instance']) != expected:
                            raise EnvironmentUnavailable('Judging unit omitted or duplicated instances')
                        if set(records) & expected:
                            raise EnvironmentUnavailable('Duplicate instance result')
                        records.update(result['per_instance'])
                        results.append(result)
                        trace['events'].append({'event':'finished', 'keys':group, 'time':time.time(), 'container':cid})
                    except ArchiveUploadUnavailable as exc:
                        # The failed filesystem is discarded. A new admission
                        # reservation receives the same frozen tar and key group;
                        # no build or solver budget has started at this point.
                        retry_upload_failure(exc, cid, group, upload_failures, pending, trace)
                    finally:
                        try:
                            docker.remove(cid)
                            del active[fut]
                        finally:
                            write('resources.json', trace)
                    write('partial-results.json', {'per_instance':records, 'units':results})
                    changed = True
                while pending and len(active)<max_jobs:
                    reservation, current = reserve(docker, image, controller_id, cfg['task'], pending[0], cfg)
                    trace['latest_capacity'] = current.json()
                    if reservation is None:
                        break
                    cid, cpus = reservation
                    group = pending.pop(0)
                    fut = pool.submit(execute, docker, cid, temp.name, cfg, controller_id)
                    active[fut] = (cid, group)
                    trace['events'].append({'event':'reserved', 'keys':group, 'cpus':cpus,
                                            'time':time.time(), 'container':cid})
                    trace['peak_jobs'] = max(trace['peak_jobs'], len(active))
                    changed = True
                if changed:
                    write('resources.json', trace)
                if pending or active:
                    time.sleep(1)
        finally:
            try:
                cleanup_failures = release_workers(docker, active, trace)
            finally:
                pool.shutdown(wait=True, cancel_futures=True)
            if cleanup_failures:
                raise EnvironmentUnavailable('Could not release workers: '+', '.join(cleanup_failures))
        if set(records) != set(keys):
            raise EnvironmentUnavailable('Final instance coverage is incomplete')
        # The metric is always recomputed from raw objectives, never averaged
        # across unit scores (which would mishandle excluded reference keys).
        sys.path.insert(0, '/tests')
        from metric.engine import compute_metric
        anchors = json.loads(Path('/tests/anchors.json').read_text())
        metric_cfg = json.loads(Path('/tests/metric_config.json').read_text())
        from metric_adapter import prepare
        raw, usable_anchors, anchor_issues = prepare(records, anchors, metric_cfg)
        metric = compute_metric(raw, usable_anchors, metric_cfg)
        metric['anchor_issues'] = anchor_issues
        detail = {'reward':metric['score'], 'per_instance':records, 'metric':metric,
                  'units':results, 'resource_report':'resources.json'}
        write('metric_detail.json', detail)
        trace['status'] = 'completed'
        write('resources.json', trace)
        write('reward.json', {'reward':metric['score']})
        (OUT/'reward.txt').write_text(str(metric['score']))
    finally:
        release_workers(docker, active, trace)
        Path(temp.name).unlink(missing_ok=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        for name in ('reward.json','reward.txt'):
            (OUT/name).unlink(missing_ok=True)
        write('environment-error.json', {'status':'environment_unavailable', 'error_type':type(exc).__name__, 'reason':str(exc)})
        print(f'ENVIRONMENT_UNAVAILABLE: {exc}', file=sys.stderr)
        raise
