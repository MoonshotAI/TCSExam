# SPDX-License-Identifier: Apache-2.0
"""Linux capacity discovery. Missing limit files never increase a known limit."""
from dataclasses import asdict, dataclass
from pathlib import Path
import math
import os
import shutil

MIB = 1024 ** 2

class EnvironmentUnavailable(RuntimeError):
    pass

@dataclass
class Capacity:
    cpu_ids: list[int]
    cpu_count: int
    memory_bytes: int
    available_bytes: int
    disk_free_bytes: int
    sources: dict

    def json(self):
        return asdict(self)


def cpu_list(value):
    result = set()
    for part in value.strip().split(','):
        if not part:
            continue
        ends = part.split('-')
        lo, hi = (int(ends[0]), int(ends[-1]))
        result.update(range(lo, hi + 1))
    return result


def read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return None


def positive_int(path):
    s = read(path)
    try:
        n = int(s)
        return n if 0 < n < 2 ** 60 else None
    except (ValueError, TypeError):
        return None


def ancestors(path, root):
    path, root = Path(path), Path(root)
    while path == root or root in path.parents:
        yield path
        if path == root:
            return
        path = path.parent


def discover(proc='/proc', cgroup='/sys/fs/cgroup', pid='self', disk='/', affinity=None):
    """Intersect affinity, cpusets, all visible ancestor quotas and memory limits.

    proc/cgroup must describe the same PID namespace. For the shared Docker
    host, pass the daemon PID and host cgroup mount. A container capacity is
    inspected separately and intersected by the caller.
    """
    proc, root = Path(proc), Path(cgroup)
    if affinity is None:
        affinity = os.sched_getaffinity(0 if pid == 'self' else int(pid))
    cpus = set(affinity)
    if not cpus:
        raise EnvironmentUnavailable('CPU affinity is empty')
    info = {}
    for line in (read(proc / 'meminfo') or '').splitlines():
        key, value = line.split(':', 1)
        info[key] = int(value.split()[0]) * 1024
    if not info.get('MemTotal') or not info.get('MemAvailable'):
        raise EnvironmentUnavailable('Cannot read total and available memory from /proc/meminfo')
    limits = [len(cpus)]
    memory = [info['MemTotal']]
    available = [info['MemAvailable']]
    seen = {}
    entries = read(proc / str(pid) / 'cgroup')
    if entries is None:
        raise EnvironmentUnavailable('Cannot inspect process cgroups')
    for entry in entries.splitlines():
        _, controllers, rel = entry.split(':', 2)
        if '..' in Path(rel).parts:
            raise EnvironmentUnavailable('Cgroup ancestry is hidden; use host cgroup namespace')
        if not controllers:
            base = root / rel.lstrip('/')
            if not base.is_dir():
                raise EnvironmentUnavailable(f'Cannot inspect cgroup directory {base}; use host cgroup namespace')
            observed_cpu = observed_memory = False
            for d in ancestors(base, root):
                quota = read(d / 'cpu.max')
                if quota:
                    observed_cpu = True
                    q, period = quota.split()
                    if q != 'max':
                        limits.append(int(q) / int(period))
                        seen[str(d / 'cpu.max')] = quota
                ids = read(d / 'cpuset.cpus.effective') or read(d / 'cpuset.cpus')
                if ids:
                    cpus.intersection_update(cpu_list(ids))
                if read(d / 'memory.max') is not None:
                    observed_memory = True
                m = positive_int(d / 'memory.max')
                if m:
                    memory.append(m)
                    used = positive_int(d / 'memory.current') or 0
                    available.append(max(0, m - used))
                    seen[str(d / 'memory.max')] = m
            # The v2 root has no resource limit files. A child cgroup must
            # expose them, or a known parent must bound its capacity.
            if base != root and not (observed_cpu and observed_memory):
                raise EnvironmentUnavailable('Cannot inspect CPU and memory limits for the non-root cgroup')
        else:
            for ctrl in controllers.split(','):
                if ctrl not in ('cpu', 'cpuset', 'memory'):
                    continue
                mount = root / ctrl
                if not mount.exists():
                    mount = root / controllers
                if not (mount / rel.lstrip('/')).is_dir():
                    raise EnvironmentUnavailable(f'Cannot inspect {ctrl} cgroup hierarchy')
                for d in ancestors(mount / rel.lstrip('/'), mount):
                    if ctrl == 'cpu':
                        q, p = positive_int(d / 'cpu.cfs_quota_us'), positive_int(d / 'cpu.cfs_period_us')
                        if q and p:
                            limits.append(q / p)
                            seen[str(d)] = {'quota': q, 'period': p}
                    elif ctrl == 'cpuset':
                        ids = read(d / 'cpuset.cpus')
                        if ids:
                            cpus.intersection_update(cpu_list(ids))
                    else:
                        m = positive_int(d / 'memory.limit_in_bytes')
                        if m:
                            memory.append(m)
                            available.append(max(0, m - (positive_int(d / 'memory.usage_in_bytes') or 0)))
                            seen[str(d / 'memory.limit_in_bytes')] = m
    count = math.floor(min([len(cpus)] + limits))
    return Capacity(sorted(cpus), count, min(memory), min(available), shutil.disk_usage(disk).free, seen)


def slots(capacity, cpu_per_unit, memory_per_unit, *, reserved_cpus=1,
          reserved_memory=512*MIB, reserved_disk=2*1024*MIB, disk_per_unit=0, max_jobs=10):
    minimum_disk = reserved_disk + disk_per_unit
    if capacity.disk_free_bytes < minimum_disk:
        raise EnvironmentUnavailable(f'Need {minimum_disk // MIB} MiB free disk; found {capacity.disk_free_bytes // MIB} MiB')
    disk_slots = (capacity.disk_free_bytes-reserved_disk)//disk_per_unit if disk_per_unit else max_jobs
    count = min(max_jobs, disk_slots, (capacity.cpu_count-reserved_cpus)//cpu_per_unit,
                (capacity.memory_bytes-reserved_memory)//memory_per_unit)
    if count < 1:
        raise EnvironmentUnavailable(
            f'Need at least {cpu_per_unit+reserved_cpus} CPUs and '
            f'{(memory_per_unit+reserved_memory)//MIB} MiB including controller reserve; '
            f'found {capacity.cpu_count} CPUs and {capacity.memory_bytes//MIB} MiB')
    return count
