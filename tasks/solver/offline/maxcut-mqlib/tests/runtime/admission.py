# SPDX-License-Identifier: Apache-2.0
"""Cross-trial admission using an atomic Docker container-name lock."""
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import time
import uuid

from docker_api import DockerError
from resources import Capacity, EnvironmentUnavailable, MIB, discover, cpu_list, slots

PREFIX = 'org.tcsexam.public-judge'
LOCK = 'tcsexam-public-judge-admission-v1'


def daemon_capacity():
    daemons = []
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                if (p/'comm').read_text().strip() == 'dockerd':
                    daemons.append(int(p.name))
            except OSError:
                pass
    if len(daemons) != 1:
        raise EnvironmentUnavailable('Need one visible Docker daemon; verifier requires pid: host and cgroup: host')
    host = discover(cgroup='/host-cgroup', pid=daemons[0])
    local = discover(cgroup='/host-cgroup')
    # Explicit verifier quotas restrict this trial, including in nested Docker.
    ids = sorted(set(host.cpu_ids) & set(local.cpu_ids))
    return Capacity(ids, min(host.cpu_count, local.cpu_count, len(ids)),
                    min(host.memory_bytes, local.memory_bytes),
                    min(host.available_bytes, local.available_bytes),
                    min(host.disk_free_bytes, local.disk_free_bytes),
                    {'daemon': host.json(), 'verifier': local.json()})


def identify_controller(docker):
    # Harbor can share the UTS hostname with its network-control service;
    # HOSTNAME can therefore identify that service rather than this process.
    own = Path('/proc/self/cgroup').read_text()
    matches=[]
    for item in docker.containers():
        if item['Id'] not in own:
            continue
        if (item.get('Labels') or {}).get(PREFIX+'.controller') != '1' or item['State']!='running':
            continue
        try:
            candidate=docker.inspect(item['Id'])
        except DockerError as exc:
            if exc.status == 404:
                continue
            raise
        pid=candidate['State'].get('Pid',0)
        try:
            if pid and Path(f'/proc/{pid}/cgroup').read_text()==own:
                matches.append(candidate)
        except OSError:
            pass
    if len(matches)!=1:
        raise EnvironmentUnavailable('Cannot identify the verifier container by its process cgroup')
    return matches[0]


@contextmanager
def locked(docker, image):
    token = uuid.uuid4().hex
    deadline = time.monotonic()+180
    while True:
        try:
            cid = docker.create(LOCK, {'Image': image, 'Cmd': ['true'],
                'Labels': {PREFIX+'.lock': token, PREFIX+'.expiry': str(time.time()+120)},
                'HostConfig': {'NetworkMode': 'none'}})
            break
        except DockerError as e:
            if e.status != 409:
                raise
            try:
                info = docker.inspect(LOCK)
                expiry = float(info['Config']['Labels'].get(PREFIX+'.expiry', 'inf'))
                if expiry < time.time():
                    docker.remove(info['Id'])
            except DockerError as missing:
                if missing.status != 404:
                    raise
            if time.monotonic() >= deadline:
                raise EnvironmentUnavailable('Shared resource admission lock did not become available')
            time.sleep(0.2)
    try:
        yield
    finally:
        docker.remove(cid)


def usage(docker, own_controller):
    """Reserve all active controllers and pending or running judging units.

    Lightweight management processes share one CPU and 512 MiB.
    Charging each waiting controller a full CPU can deadlock a small host.
    Unknown external
    processes are additionally covered by Linux MemAvailable; this is not a
    general-purpose host workload scheduler.
    """
    cpu = 1.0
    memory = 512*MIB
    pinned = set()
    active_units = []
    disk = 0
    for item in docker.containers():
        labels = item.get('Labels', {}) or {}
        if labels.get(PREFIX+'.lock'):
            continue
        managed = labels.get(PREFIX+'.unit')
        is_controller = labels.get(PREFIX+'.controller') == '1'
        if is_controller or not managed:
            continue
        if item['State'] not in ('running', 'restarting', 'paused') and not (managed and item['State']=='created'):
            continue
        try:
            info = docker.inspect(item['Id'])
        except DockerError as exc:
            # An owner may collect and remove its completed worker while
            # another trial reads the daemon's container-list snapshot.
            if exc.status == 404:
                continue
            raise
        hc = info['HostConfig']
        cpus = (hc.get('NanoCpus', 0)/1e9 or
                (hc.get('CpuQuota', 0)/hc.get('CpuPeriod', 100000) if hc.get('CpuQuota', 0)>0 else 0))
        ids = cpu_list(hc.get('CpusetCpus', ''))
        if ids:
            pinned.update(ids)
            cpus = cpus or len(ids)
        cpu += cpus
        memory += hc.get('Memory', 0)
        if managed:
            active_units.append(info['Id'])
            disk += int(labels.get(PREFIX+'.disk_mb', 0))*MIB
    return math.ceil(cpu), memory, pinned, active_units, disk


def reap_orphans(docker):
    """Remove only labelled workers whose owning verifier has disappeared."""
    for item in docker.containers():
        labels=item.get('Labels') or {}
        owner=labels.get(PREFIX+'.owner')
        if not labels.get(PREFIX+'.unit') or not owner:
            continue
        try:
            state=docker.inspect(owner)['State']['Status']
            orphan=state not in ('running','restarting','paused')
        except DockerError as exc:
            if exc.status != 404:
                raise
            orphan=True
        if orphan:
            docker.remove(item['Id'])


def reserve(docker, image, controller, task, keys, cfg):
    """Return a newly created reserved worker or None while resources are busy."""
    with locked(docker, image):
        reap_orphans(docker)
        cap = daemon_capacity()
        try:
            slots(cap, cfg['cpus'], cfg['memory_mb']*MIB, disk_per_unit=cfg['disk_mb']*MIB)
        except EnvironmentUnavailable:
            return None, cap
        used_cpu, used_mem, pinned, _, used_disk = usage(docker, controller)
        free_cpu = min(cap.cpu_count-used_cpu, len(set(cap.cpu_ids)-pinned))
        free_mem = min(cap.memory_bytes-used_mem, cap.available_bytes-512*MIB)
        if (free_cpu < cfg['cpus'] or free_mem < cfg['memory_mb']*MIB or
                cap.disk_free_bytes-used_disk < (cfg['disk_mb']+2048)*MIB):
            return None, cap
        ids = sorted(set(cap.cpu_ids)-pinned)[:cfg['cpus']]
        name = 'tcsexam-unit-'+uuid.uuid4().hex[:20]
        cid = docker.create(name, {
            'Image': image, 'WorkingDir': '/work',
            'Entrypoint': ['python3', '/opt/public_judge/worker.py'], 'Cmd': [],
            'Env': ['TCS_UNIT_KEYS='+json.dumps(keys), 'JUDGE_JOBS=1'],
            'Labels': {PREFIX+'.unit': task, PREFIX+'.owner': controller,
                       PREFIX+'.keys': json.dumps(keys), PREFIX+'.disk_mb': str(cfg['disk_mb']), PREFIX+'.created': str(time.time())},
            'HostConfig': {'NetworkMode': 'none', 'NanoCpus': cfg['cpus']*1000000000,
                'CpusetCpus': ','.join(map(str,ids)), 'Memory': cfg['memory_mb']*MIB,
                'MemorySwap': cfg['memory_mb']*MIB, 'PidsLimit': 1024,
                'CapDrop': ['ALL'], 'CapAdd': ['CHOWN', 'SETUID', 'SETGID', 'DAC_OVERRIDE', 'KILL'], 'SecurityOpt': ['no-new-privileges:true']}})
        return (cid, ids), cap
