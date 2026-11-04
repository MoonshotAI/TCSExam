"""Prepare a mode-normalized, verified Harbor helper build context."""
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import tempfile


HARBOR_VERSION = '0.22.0'


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def source_entries(source):
    source = Path(source)
    if source.is_symlink() or not source.is_dir():
        raise ValueError('Harbor helper source must be a real directory')
    entries = {}
    for root, directories, files in os.walk(source, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        root = Path(root)
        for name in directories:
            path = root / name
            mode = path.lstat().st_mode
            if not stat.S_ISDIR(mode) or path.is_symlink():
                raise ValueError('Harbor helper source contains a link or special directory')
            entries[path.relative_to(source).as_posix()] = {'type': 'directory', 'mode': 0o755}
        for name in files:
            path = root / name
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                raise ValueError('Harbor helper source contains a link or special file')
            entries[path.relative_to(source).as_posix()] = {
                'type': 'file', 'mode': 0o755 if mode & 0o111 else 0o644,
                'bytes': path.stat().st_size, 'sha256': file_digest(path)}
    if 'Dockerfile' not in entries:
        raise ValueError('Harbor helper source has no Dockerfile')
    return entries


def verify_context(context, entries):
    context = Path(context)
    if context.is_symlink() or not context.is_dir():
        raise ValueError('Harbor helper cache must be a real directory')
    if stat.S_IMODE(context.lstat().st_mode) != 0o755:
        raise ValueError('Harbor helper cache root permission differs')
    actual = set()
    for root, directories, files in os.walk(context, topdown=True, followlinks=False):
        root = Path(root)
        for name in directories:
            path = root / name
            relative = path.relative_to(context).as_posix()
            actual.add(relative)
            row = entries.get(relative)
            if (row is None or row['type'] != 'directory' or path.is_symlink()
                    or not stat.S_ISDIR(path.lstat().st_mode)
                    or stat.S_IMODE(path.lstat().st_mode) != row['mode']):
                raise ValueError(f'Harbor helper cache directory differs: {relative}')
        for name in files:
            path = root / name
            relative = path.relative_to(context).as_posix()
            actual.add(relative)
            row = entries.get(relative)
            if (row is None or row['type'] != 'file' or path.is_symlink()
                    or not stat.S_ISREG(path.lstat().st_mode)
                    or stat.S_IMODE(path.lstat().st_mode) != row['mode']
                    or path.stat().st_size != row['bytes'] or file_digest(path) != row['sha256']):
                raise ValueError(f'Harbor helper cache content differs: {relative}')
    if actual != set(entries):
        raise ValueError('Harbor helper cache is incomplete')


def normalized_context(cache, source=None):
    """Return the cached context and its hash using Harbor's own algorithm."""
    if source is None:
        from importlib.metadata import version
        if version('harbor') != HARBOR_VERSION:
            raise ValueError(f'Host support products require Harbor {HARBOR_VERSION}')
        from harbor.environments.docker import docker
        source = Path(docker.__file__).parent / 'harbor-docker-egress-control-sidecar'
    source = Path(source)
    entries = source_entries(source)
    target = Path(cache).expanduser().resolve() / 'harbor' / HARBOR_VERSION / 'egress-control'
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.parent / 'egress-control.lock'
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if target.is_symlink():
            raise ValueError('Harbor helper cache cannot be a symbolic link')
        if target.exists():
            verify_context(target, entries)
        else:
            with tempfile.TemporaryDirectory(prefix='.preparing-', dir=target.parent) as folder:
                staged = Path(folder) / 'context'
                staged.mkdir()
                staged.chmod(0o755)
                for relative, row in entries.items():
                    destination = staged / relative
                    if row['type'] == 'directory':
                        destination.mkdir()
                        destination.chmod(row['mode'])
                        continue
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    data = (source / relative).read_bytes()
                    if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                        raise ValueError(f'Harbor helper source changed while copying: {relative}')
                    destination.write_bytes(data)
                    destination.chmod(row['mode'])
                verify_context(staged, entries)
                os.replace(staged, target)
    verify_context(target, entries)
    from harbor.utils.container_cache import docker_build_context_hash
    key = docker_build_context_hash(context=target, dockerfile_path=target / 'Dockerfile',
                                    build_args={}, platform='linux/amd64')
    return target, key
