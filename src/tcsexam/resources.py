"""Pinned resource acquisition, safe extraction and atomic content caches."""
from contextlib import contextmanager
import ctypes
import ctypes.util
import fcntl
import gzip
import hashlib
import json
import lzma
import os
import posixpath
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile

from .layout import load, within


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def relative(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or '\x00' in name:
        raise ValueError(f'Unsafe archive path: {name!r}')
    return str(p)


def manifest(root, bundle):
    path = within(root, bundle.get('files_manifest', bundle.get('manifest', '')))
    if digest(path) != bundle['manifest_sha256']:
        raise ValueError(f"Manifest hash differs: {bundle['id']}")
    rows = load(path)['files']
    names = [relative(r['path']) for r in rows]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate manifest path')
    return rows


def link_target(row, rows):
    kind = row.get('type', 'file')
    if kind not in ('symlink', 'hardlink'):
        return None
    target = row.get('link_target')
    if not target or '\\' in target or '\x00' in target or target.startswith('/'):
        raise ValueError('Declared links must have bounded relative targets')
    name = relative(row['path'])
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target)
                                 if kind == 'symlink' else target)
    resolved = relative(resolved)
    expected = {relative(r['path']): r for r in rows}
    if resolved not in expected or expected[resolved].get('type', 'file') != 'file':
        raise ValueError('Declared link target must be a declared regular file')
    return resolved


def verify(folder, rows):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('Resource cache must be a real directory')
    expected = {relative(r['path']): r for r in rows}
    actual = set()
    for p in folder.rglob('*'):
        name = p.relative_to(folder).as_posix()
        if not (p.is_symlink() or p.is_file() or p.is_dir()):
            raise ValueError(f'Unexpected special file: {name}')
        if p.is_symlink() or p.is_file():
            actual.add(name)
            row = expected.get(name)
            if row is None:
                raise ValueError(f'Content differs: {name}')
            kind = row.get('type', 'file')
            target = link_target(row, rows)
            if kind == 'symlink':
                if (not p.is_symlink() or os.readlink(p) != row['link_target'] or
                    stat.S_IMODE(p.lstat().st_mode) != int(row['mode'], 8)):
                    raise ValueError(f'Link differs: {name}')
                continue
            if p.is_symlink():
                raise ValueError(f'Unexpected link: {name}')
            if kind == 'hardlink':
                if p.stat().st_ino != (folder / target).stat().st_ino:
                    raise ValueError(f'Hard link differs: {name}')
            elif p.stat().st_size != row['bytes'] or digest(p) != row['sha256']:
                raise ValueError(f'Content differs: {name}')
            if stat.S_IMODE(p.stat().st_mode) != int(row['mode'], 8):
                raise ValueError(f'Permission differs: {name}')
    if actual != set(expected):
        raise ValueError(f'Missing resource files: {sorted(set(expected) - actual)[:5]}')
    return {'files': len(rows), 'bytes': sum(r.get('bytes', 0) for r in rows)}


def download(source, cache):
    """Reuse only checked bytes. Never commit a partial or corrupt download."""
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / source['sha256']
    if target.is_file() and digest(target) == source['sha256']:
        return target
    url = urllib.parse.urlsplit(source['url'])
    if url.scheme not in ('https', 'http') or not url.hostname or url.username or url.password:
        raise ValueError('Resource URL must be HTTP(S) without credentials')
    fd, name = tempfile.mkstemp(dir=cache, prefix='.download-')
    try:
        with os.fdopen(fd, 'wb') as output, urllib.request.urlopen(source['url'], timeout=120) as response:
            size = 0
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > source['bytes']:
                    raise ValueError('Download exceeds declared size')
                output.write(block)
        if size != source['bytes'] or digest(name) != source['sha256']:
            raise ValueError('Downloaded resource hash or size differs')
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)
    return target


def extract_tar(archive, destination, rows):
    """Extract checked regular files and explicitly declared bounded links."""
    expected = {relative(r['path']): r for r in rows}
    seen, links = set(), []
    with tarfile.open(archive, 'r|gz') as tar:
        for member in tar:
            name = relative(member.name)
            if member.isdir():
                if not any(p.startswith(name.rstrip('/') + '/') for p in expected):
                    raise ValueError(f'Undeclared directory: {name}')
                continue
            if name in seen or name not in expected:
                raise ValueError(f'Duplicate or undeclared archive member: {name}')
            row = expected[name]
            seen.add(name)
            kind = row.get('type', 'file')
            if kind in ('symlink', 'hardlink'):
                link_target(row, rows)
                if ((kind == 'symlink' and not member.issym()) or
                    (kind == 'hardlink' and not member.islnk()) or member.linkname != row['link_target']):
                    raise ValueError(f'Archive link differs: {name}')
                links.append(row)
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f'Undeclared archive link or special file: {name}')
            if member.size != row['bytes'] or stat.S_IMODE(member.mode) != int(row['mode'], 8):
                raise ValueError(f'Archive metadata differs: {name}')
            dest = Path(destination) / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as inp, dest.open('wb') as out:
                shutil.copyfileobj(inp, out, 1024 * 1024)
            dest.chmod(int(row['mode'], 8))
    for row in links:
        dest = Path(destination) / row['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        target = link_target(row, rows)
        if row['type'] == 'symlink':
            dest.symlink_to(row['link_target'])
        else:
            os.link(Path(destination) / target, dest)
    verify(destination, rows)


def rar_members(path):
    """Read RAR via system libarchive without asking it to create any paths."""
    library = ctypes.util.find_library('archive')
    if not library:
        raise ValueError('Install libarchive (Debian/Ubuntu: libarchive13 or libarchive13t64)')
    lib = ctypes.CDLL(library)
    for name, result, arguments in (
        ('archive_read_new', ctypes.c_void_p, []),
        ('archive_read_support_format_all', ctypes.c_int, [ctypes.c_void_p]),
        ('archive_read_support_filter_all', ctypes.c_int, [ctypes.c_void_p]),
        ('archive_read_open_filename', ctypes.c_int, [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]),
        ('archive_read_next_header', ctypes.c_int, [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]),
        ('archive_entry_pathname', ctypes.c_char_p, [ctypes.c_void_p]),
        ('archive_entry_filetype', ctypes.c_uint, [ctypes.c_void_p]),
        ('archive_entry_symlink', ctypes.c_char_p, [ctypes.c_void_p]),
        ('archive_entry_hardlink', ctypes.c_char_p, [ctypes.c_void_p]),
        ('archive_read_data', ctypes.c_ssize_t, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]),
        ('archive_read_free', ctypes.c_int, [ctypes.c_void_p]),
    ):
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = result, arguments
    reader = lib.archive_read_new()
    try:
        lib.archive_read_support_format_all(reader)
        lib.archive_read_support_filter_all(reader)
        if lib.archive_read_open_filename(reader, os.fsencode(path), 1024 * 1024) != 0:
            raise ValueError('Cannot open upstream archive')
        entry = ctypes.c_void_p()
        while True:
            code = lib.archive_read_next_header(reader, ctypes.byref(entry))
            if code == 1:
                break
            if code != 0:
                raise ValueError('Damaged upstream archive header')
            name = relative(lib.archive_entry_pathname(entry).decode('utf-8'))
            kind = lib.archive_entry_filetype(entry)
            if lib.archive_entry_symlink(entry) or lib.archive_entry_hardlink(entry):
                raise ValueError('Upstream archive contains an undeclared link')
            if kind == stat.S_IFDIR:
                continue
            if kind != stat.S_IFREG:
                raise ValueError('Upstream archive contains a special file')
            data = bytearray()
            buffer = ctypes.create_string_buffer(65536)
            while True:
                n = lib.archive_read_data(reader, buffer, len(buffer))
                if n == 0:
                    break
                if n < 0:
                    raise ValueError('Damaged upstream archive member')
                data.extend(buffer.raw[:n])
                if len(data) > 64 * 1024 * 1024:
                    raise ValueError('Upstream member exceeds preparation limit')
            yield name, bytes(data)
    finally:
        lib.archive_read_free(reader)


def official_source_rows(rows):
    required = {}
    for row in rows:
        member = row.get('source_member')
        if not member:
            continue
        member = relative(member)
        if member in required:
            raise ValueError(f'Duplicate official source member: {member}')
        required[member] = row
    if not required:
        raise ValueError('Official build has no declared source members')
    return required


def copy_official_member(stream, destination, row):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('wb') as output:
        shutil.copyfileobj(stream, output, 1024 * 1024)
    destination.chmod(int(row['mode'], 8))
    if destination.stat().st_size != row['bytes'] or digest(destination) != row['sha256']:
        raise ValueError(f'Official source content differs: {row["source_member"]}')


def extract_official(archive, destination, rows, archive_format):
    """Extract exactly the declared official files, rejecting every other member."""
    destination = Path(destination)
    required = official_source_rows(rows)
    seen = set()
    if archive_format == 'zip':
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                name = relative(member.filename)
                if member.is_dir():
                    if not any(p.startswith(name.rstrip('/') + '/') for p in required):
                        raise ValueError(f'Undeclared official directory: {name}')
                    continue
                kind = stat.S_IFMT(member.external_attr >> 16)
                if (name in seen or name not in required or
                        kind not in (0, stat.S_IFREG) or member.file_size != required[name]['bytes']):
                    raise ValueError(f'Duplicate, undeclared or special official member: {name}')
                seen.add(name)
                row = required[name]
                with source.open(member) as stream:
                    copy_official_member(stream, destination / relative(row['path']), row)
    elif archive_format == 'tar.gz':
        with tarfile.open(archive, 'r|gz') as source:
            for member in source:
                name = relative(member.name)
                if member.isdir():
                    if not any(p.startswith(name.rstrip('/') + '/') for p in required):
                        raise ValueError(f'Undeclared official directory: {name}')
                    continue
                if (name in seen or name not in required or not member.isfile() or
                        member.issym() or member.islnk() or member.size != required[name]['bytes']):
                    raise ValueError(f'Duplicate, undeclared or special official member: {name}')
                seen.add(name)
                row = required[name]
                with source.extractfile(member) as stream:
                    copy_official_member(stream, destination / relative(row['path']), row)
    else:
        raise ValueError(f'Unsupported official archive format: {archive_format}')
    if seen != set(required):
        raise ValueError(f'Official archive is missing files: {sorted(set(required) - seen)}')


def official_builder_reference(build):
    from .setup import PIN
    reference = build.get('builder_image')
    if not isinstance(reference, str) or not PIN.fullmatch(reference):
        raise ValueError('Official build requires a digest-pinned Docker builder image')
    return reference


def acquire_official_builder(root, build, cache, args=None):
    from argparse import Namespace
    from .build import ImageBuilder
    reference = official_builder_reference(build)
    options = Namespace(artifacts=None, image_map=None, cache=cache,
                        docker_context=getattr(args, 'docker_context', None),
                        pull_policy=getattr(args, 'pull_policy', 'missing'))
    builder = ImageBuilder(root, [], options)
    record = builder.acquire(reference)
    return record.get('local_image', record['reference'])


def official_build_command(build, command, output, image, args=None, name=None):
    from .build import proxy_arguments
    from .setup import docker_command
    official_builder_reference(build)
    name = name or 'tcsexam-official-build-' + os.urandom(16).hex()
    workdir = (PurePosixPath('/tcsexam-output') / relative(build['cwd'])).as_posix()
    setup = ('apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 '
             '-o Acquire::https::Timeout=60 update && '
             'apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 '
             '-o Acquire::https::Timeout=60 install -y --no-install-recommends make g++ && '
             'rm -rf /var/lib/apt/lists/* && exec "$@"')
    result = docker_command(args) + [
        'create', '--name', name, '--pull=never', '--platform', 'linux/amd64',
        '--workdir', workdir, '--env', 'LC_ALL=C', '--env', 'DEBIAN_FRONTEND=noninteractive']
    for proxy_name, value in sorted(proxy_arguments().items()):
        result += ['--env', f'{proxy_name}={value}']
    return result + [image, '/bin/sh', '-eu', '-c', setup, 'tcsexam-official-build', *command]


def run_official_container(create_command, timeout_sec, log_directory, copy_in=(), copy_out=()):
    """Run one named container without host mounts and preserve its command evidence."""
    create_index = create_command.index('create')
    prefix = create_command[:create_index]
    name = create_command[create_command.index('--name') + 1]
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', name):
        raise ValueError('Invalid official container name')
    container = None
    primary = None
    events = []
    cleanup_errors = []

    def call(operation, command, timeout, check=True):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            events.append({'operation': operation, 'error': str(exc),
                           'stdout': getattr(exc, 'stdout', None),
                           'stderr': getattr(exc, 'stderr', None)})
            raise ValueError(f'Official container {operation} failed: {exc}') from exc
        events.append({'operation': operation, 'returncode': result.returncode,
                       'stdout': result.stdout, 'stderr': result.stderr})
        if check and result.returncode:
            detail = (result.stderr or result.stdout or '')[-1000:]
            raise ValueError(f'Official container {operation} failed with exit code '
                             f'{result.returncode}: {detail}')
        return result

    try:
        created = call('create', create_command, 60, check=False)
        candidate = created.stdout.strip()
        if re.fullmatch(r'[0-9a-fA-F]{12,64}', candidate):
            container = candidate
        elif created.returncode == 0:
            container = name
        if created.returncode:
            detail = (created.stderr or created.stdout or '')[-1000:]
            raise ValueError(f'Official container create failed with exit code '
                             f'{created.returncode}: {detail}')
        if container is None:
            raise ValueError('Official container create returned no verifiable container ID')
        for host, remote in copy_in:
            call('cp-in', prefix + ['cp', str(host), f'{container}:{remote}'], 300)
        call('start', prefix + ['start', container], 60)
        waited = call('wait', prefix + ['wait', container], int(timeout_sec))
        try:
            status = int(waited.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError) as exc:
            raise ValueError('Official container wait returned no valid exit status') from exc
        if not 0 <= status <= 255:
            raise ValueError(f'Official container wait returned invalid exit status: {status}')
        if status:
            raise ValueError(f'Official container exited with status {status}')
        for remote, host in copy_out:
            call('cp-out', prefix + ['cp', f'{container}:{remote}', str(host)], 300)
    except BaseException as exc:
        primary = exc
    finally:
        if container is not None:
            for operation, arguments, timeout in (
                    ('logs', ['logs', container], 30), ('rm', ['rm', '-f', container], 60)):
                try:
                    call(operation, prefix + arguments, timeout)
                except ValueError as exc:
                    cleanup_errors.append(str(exc))
        if primary is not None:
            events.append({'operation': 'failure', 'error': str(primary)})
        try:
            log_directory = Path(log_directory)
            log_directory.mkdir(parents=True, exist_ok=True)
            log_path = log_directory / (name + '.log')
            def text(value):
                return value.decode(errors='replace') if isinstance(value, bytes) else str(value or '')
            log_path.write_text('\n\n'.join(
                f"{event['operation']}\n{event.get('error', '')}\n"
                f"returncode={event.get('returncode', '')}\n"
                f"stdout:\n{text(event.get('stdout'))}\nstderr:\n{text(event.get('stderr'))}"
                for event in events) + '\n')
        except (OSError, ValueError) as exc:
            cleanup_errors.append(f'Cannot preserve official container log: {exc}')
    if primary is not None:
        if cleanup_errors:
            primary.add_note('Official container cleanup also failed: ' + '; '.join(cleanup_errors))
        raise primary
    if cleanup_errors:
        raise ValueError('Official container cleanup failed: ' + '; '.join(cleanup_errors))
    return log_path


def official_download_limits(build):
    """Bound the whole transfer/retry sequence, with time for setup and hashing.

    An unspecified limit retains the 120-second transfer and 300-second outer
    default. An explicit download_timeout_sec is the transfer's total budget;
    installing curl and checking the file receive 180 additional seconds.
    """
    seconds = build.get('download_timeout_sec', 120)
    if type(seconds) is not int or not 0 < seconds <= 2 ** 31 - 180:
        raise ValueError('download_timeout_sec must be a positive finite integer within the timer range')
    return seconds, seconds + 180


def download_official(source, cache, build, image, args=None, resource_name=None):
    transfer_timeout, outer_timeout = official_download_limits(build)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / source['sha256']
    if target.is_file() and digest(target) == source['sha256']:
        return target
    url = urllib.parse.urlsplit(source['url'])
    if url.scheme not in ('https', 'http') or not url.hostname or url.username or url.password:
        raise ValueError('Resource URL must be HTTP(S) without credentials')
    official_builder_reference(build)
    from .build import proxy_arguments
    from .setup import docker_command
    with tempfile.TemporaryDirectory(dir=cache, prefix='.download-') as folder:
        setup = ('apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 '
                 '-o Acquire::https::Timeout=60 update && '
                 'apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 '
                 '-o Acquire::https::Timeout=60 install -y --no-install-recommends '
                 'curl ca-certificates coreutils && rm -rf /var/lib/apt/lists/* && '
                 f'timeout --signal=TERM --kill-after=10 {transfer_timeout}s '
                 'curl --fail --location --retry 2 --connect-timeout 30 '
                 f'--max-time {transfer_timeout} --retry-max-time {transfer_timeout} '
                 '--output /out/source "$1" && '
                 'printf \'%s  /out/source\\n\' "$2" | sha256sum -c - && '
                 'test "$(stat -c %s /out/source)" = "$3"')
        name = ('tcsexam-official-download-' + (resource_name + '-' if resource_name else '')
                + os.urandom(16).hex())
        command = docker_command(args) + [
            'create', '--name', name, '--pull=never', '--platform', 'linux/amd64',
            '--workdir', '/out', '--env', 'LC_ALL=C', '--env', 'DEBIAN_FRONTEND=noninteractive']
        for proxy_name, value in sorted(proxy_arguments().items()):
            command += ['--env', f'{proxy_name}={value}']
        command += [image, '/bin/sh', '-eu', '-c', setup, 'tcsexam-official-download',
                    source['url'], source['sha256'], str(source['bytes'])]
        archive = Path(folder) / 'source'
        run_official_container(command, outer_timeout,
                               cache.parent / 'official-container-logs',
                               copy_out=[('/out/source', archive)])
        if archive.stat().st_size != source['bytes'] or digest(archive) != source['sha256']:
            raise ValueError('Downloaded official resource hash or size differs')
        os.replace(archive, target)
    return target


def prepare_official_build(root, resource, rows, output, downloads, inputs=None,
                           args=None, builder_image=None):
    """Acquire, build and install an official tool inside its pinned Docker toolchain."""
    recipe = load(within(root, resource['recipe']))
    build = recipe['build']
    source = recipe['source']
    supplied = (inputs or {}).get(source.get('id', 'source_archive'))
    image = builder_image
    if supplied is None and source.get('url'):
        image = image or acquire_official_builder(root, build, Path(downloads).parent, args)
        archive = download_official(source, downloads, build, image, args,
                                    resource_name=resource['id'])
    else:
        archive = input_file(source, downloads, inputs)
    extract_official(archive, output, rows, recipe['archive_format'])
    command = build['command']
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        raise ValueError('Official build command must be a nonempty argument list')
    build_dir = output / relative(build['cwd'])
    artifact = build_dir / relative(build['artifact'])
    install = output / relative(build['install'])
    declared = {row['path']: row for row in rows}
    artifact_name = artifact.relative_to(output).as_posix()
    install_name = install.relative_to(output).as_posix()
    if artifact_name not in declared or install_name not in declared:
        raise ValueError('Official build outputs must be declared in the file manifest')
    image = image or acquire_official_builder(root, build, Path(downloads).parent, args)
    name = 'tcsexam-official-build-' + resource['id'] + '-' + os.urandom(16).hex()
    run_official_container(official_build_command(build, command, output, image, args, name=name),
                           int(build.get('timeout_sec', 120)),
                           Path(downloads).parent / 'official-container-logs',
                           copy_in=[(str(output) + '/.', '/tcsexam-output')],
                           copy_out=[('/tcsexam-output/.', output)])
    if artifact.is_symlink() or not artifact.is_file():
        raise ValueError('Official build did not produce a regular executable')
    install.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact, install)
    for path, name in ((artifact, artifact_name), (install, install_name)):
        path.chmod(int(declared[name]['mode'], 8))


def resource_by_id(root, name):
    """Resolve data identities from the shared image inventory."""
    for resource in load(Path(root) / 'assets/images.json')['images']:
        if (resource.get('type') in ('data', 'toolchain') and resource.get('recipe')
                and resource.get('files_manifest') and resource.get('id') == name):
            relative(resource['id'])
            relative(resource['content_version'])
            return resource
    raise ValueError(f'Unknown preparable data or tool image: {name}')


def content_digest(rows, target_root='/'):
    """Hash content and runtime paths independently of recipe JSON formatting."""
    prefix = relative(target_root.lstrip('/')) if target_root != '/' else ''
    entries = []
    for row in rows:
        path = '/'.join(x for x in (prefix, relative(row['path'])) if x)
        entry = {'path': '/' + path, 'bytes': row.get('bytes', 0),
                 'mode': format(int(row['mode'], 8), '04o')}
        if row.get('type', 'file') == 'file':
            entry['sha256'] = row['sha256']
        else:
            link_target(row, rows)
            entry['type'] = row['type']
            entry['link_target'] = row['link_target']
        entries.append(entry)
    canonical = json.dumps(sorted(entries, key=lambda r: r['path']),
                           sort_keys=True, separators=(',', ':')).encode()
    return 'sha256:' + hashlib.sha256(canonical).hexdigest()


def input_file(source, downloads, inputs=None):
    """Accept an explicit fixed source or acquire the same checked bytes."""
    supplied = (inputs or {}).get(source.get('id', 'source_archive'))
    if supplied is None:
        if not source.get('url'):
            raise ValueError(f"Resource requires explicit --input {source.get('id', 'source_archive')}=PATH")
        return download(source, downloads)
    supplied = Path(supplied)
    if supplied.is_symlink() or not supplied.is_file():
        raise ValueError('Supplied source must be a regular file')
    if supplied.stat().st_size != source['bytes'] or digest(supplied) != source['sha256']:
        raise ValueError('Supplied source hash or size differs')
    return supplied


def prepare_qbf(root, resource, rows, output, downloads, inputs=None):
    """Recover frozen compressed bytes from checked official plain instances."""
    recipe = load(within(root, resource['recipe']))
    frozen = (inputs or {}).get('frozen_input')
    if frozen is not None:
        archive = input_file(dict(recipe['frozen_input'], id='frozen_input'), downloads, inputs)
        extract_tar(archive, output, rows)
        return
    source = input_file(dict(recipe['source_archive'], id='source_archive'), downloads, inputs)
    required = {row['source_member'].removeprefix('./'): row
                for row in rows if row.get('source_member')}
    seen = set()
    with tarfile.open(source, 'r|gz') as archive:
        for member in archive:
            name = member.name.removeprefix('./')
            if name not in required:
                continue
            if not member.isfile() or member.issym() or member.islnk() or name in seen:
                raise ValueError('Invalid or duplicate official QBF member')
            if member.size > 128 * 1024 * 1024:
                raise ValueError('QBF source member exceeds preparation limit')
            row = required[name]
            data = archive.extractfile(member).read()
            if hashlib.sha256(data).hexdigest() != row['source_sha256_plain']:
                raise ValueError('Official QBF plain bytes differ')
            compressed = lzma.compress(data, format=lzma.FORMAT_XZ,
                                       check=lzma.CHECK_CRC64,
                                       preset=recipe['compression']['preset'])
            if hashlib.sha256(compressed).hexdigest() != row['sha256']:
                raise ValueError('QBF compressed bytes differ; provide fixed original input')
            path = output / relative(row['path'])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(compressed)
            path.chmod(int(row['mode'], 8))
            seen.add(name)
    if seen != set(required):
        raise ValueError('Official QBF source is missing selected instances')
    for row in rows:
        if row.get('source_path'):
            path = output / relative(row['path'])
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(within(root, row['source_path']), path)
            path.chmod(int(row['mode'], 8))


def prepare_resource(root, name, cache, inputs=None, args=None, builder_image=None,
                     resource=None):
    """Prepare checked rootfs before model execution; atomically publish success."""
    root = Path(root)
    from .fixed_data_archive import effective_resource, check_explicit_input
    resource = resource or effective_resource(
        root, resource_by_id(root, name), getattr(args, 'data_recipe', None))
    if resource['id'] != name:
        raise ValueError('Effective resource ID differs from requested product')
    rows = manifest(root, resource)
    provenance = {}
    if resource.get('recipe_format') == 'official_maxsat_generator':
        from .maxsat_data import cache_identity
        provenance = cache_identity(root, resource, rows)
    target = Path(cache).expanduser().resolve() / name / resource['content_version']
    if resource.get('selected_data_recipe'):
        check_explicit_input(root, resource, Path(cache).expanduser() / 'downloads', inputs)
        target = target.parent / 'routes' / resource['content_version'] / resource['data_recipe_signature']
    target.parent.mkdir(parents=True, exist_ok=True)
    identity = content_digest(rows, resource['target_root'])
    with (target.parent / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = target / '.complete.json'
        rootfs = target / 'rootfs'
        if target.is_symlink() or marker.is_symlink() or rootfs.is_symlink():
            raise ValueError('Resource cache cannot be a symbolic link')
        prefix = relative(resource['target_root'].lstrip('/')) if resource['target_root'] != '/' else ''
        completion = load(marker) if marker.is_file() else {}
        if completion.get('content_digest') == identity:
            if any(completion.get(key) != value for key, value in provenance.items()):
                raise ValueError('MaxSAT cache provenance differs from the official conversion recipe; use a fresh cache')
            verify(rootfs / prefix, rows)
            return rootfs
        if target.exists():
            raise ValueError(f'Incomplete cache exists; remove or move it before retrying: {target}')
        with tempfile.TemporaryDirectory(dir=target.parent, prefix='.preparing-') as work:
            work = Path(work)
            staged = work / 'complete'
            payload = staged / 'rootfs' / prefix
            payload.mkdir(parents=True)
            downloads = Path(cache).expanduser().resolve() / 'downloads'
            if resource.get('recipe_format') == 'official_mqlib':
                from .maxcut_data import prepare_data
                prepare_data(root, resource, rows, payload, downloads, inputs=inputs,
                             args=args, builder_image=builder_image)
            elif resource.get('recipe_format') == 'official_archive':
                from .official_archive_data import prepare_data
                prepare_data(root, resource, rows, payload, downloads, inputs=inputs,
                             args=args, builder_image=builder_image)
            elif resource.get('recipe_format') == 'official_files':
                from .official_file_data import prepare_data
                prepare_data(root, resource, rows, payload, downloads, inputs=inputs,
                             args=args, builder_image=builder_image)
            elif resource.get('recipe_format') == 'official_dfvs_xz':
                from .dfvs_pace2022 import prepare_public_data
                prepare_public_data(root, resource, rows, payload, downloads, inputs=inputs,
                                    args=args, builder_image=builder_image)
            elif resource.get('recipe_format') == 'official_ce_xz':
                from .ce_pace2021 import prepare_public_data
                prepare_public_data(root, resource, rows, payload, downloads, inputs=inputs,
                                    args=args, builder_image=builder_image)
            elif resource.get('recipe_format') == 'official_vc_xz':
                from .vc_pace2019 import prepare_public_data
                prepare_public_data(root, resource, rows, payload, downloads, inputs=inputs,
                                    args=args, builder_image=builder_image)
            elif resource.get('recipe_format') == 'official_gp_generator':
                from .gp_data import prepare_data
                prepare_data(root, resource, rows, payload, downloads, inputs=inputs,
                             args=args, builder_image=builder_image)
            elif resource.get('recipe_format') == 'official_qbf_generator':
                from .qbf_data import prepare_data
                prepare_data(root, resource, rows, payload, downloads, inputs=inputs,
                             args=args, builder_image=builder_image)
            elif resource.get('recipe_format') == 'official_maxsat_generator':
                from .maxsat_data import prepare_data
                prepare_data(root, resource, rows, payload, downloads, inputs=inputs,
                             args=args, builder_image=builder_image)
            elif resource.get('recipe_format') == 'fixed_data_archive':
                from .fixed_data_archive import prepare_data
                prepare_data(root, resource, rows, payload, downloads, inputs=inputs)
            elif resource.get('recipe_format') == 'frozen_directory':
                from .solver_data_recipes import prepare_frozen_directory
                prepare_frozen_directory(root, resource, rows, payload, downloads,
                                         inputs=inputs)
            elif resource.get('recipe_format') == 'official_atcoder_generator':
                from .atcoder_data import prepare_data
                prepare_data(root, resource, rows, payload, downloads, inputs=inputs,
                             args=args, builder_image=builder_image)
            elif name == 'bpplib-development':
                from .bpplib import prepare
                prepare(root, resource, rows, payload, downloads, inputs=inputs)
            elif name == 'bpplib-judging':
                from .bpplib import prepare_judging
                prepare_judging(root, resource, rows, payload, downloads, inputs=inputs)
            elif name == 'qbf-public':
                prepare_qbf(root, resource, rows, payload, downloads, inputs=inputs)
            elif name == 'solver-ce-pace2021-development-data':
                from .ce_pace2021 import prepare_public_data
                prepare_public_data(root, resource, rows, payload, downloads, inputs=inputs,
                                    args=args, builder_image=builder_image)
            elif name == 'solver-dfvs-pace2022-development-data':
                from .dfvs_pace2022 import prepare_public_data
                prepare_public_data(root, resource, rows, payload, downloads, inputs=inputs,
                                    args=args, builder_image=builder_image)
            elif name == 'solver-vc-pace2019-development-data':
                from .vc_pace2019 import prepare_public_data
                prepare_public_data(root, resource, rows, payload, downloads, inputs=inputs,
                                    args=args, builder_image=builder_image)
            elif name == 'solver-ahc058-atcoder-development-data':
                from .ahc058_atcoder import prepare_public_data
                prepare_public_data(root, resource, rows, payload, downloads, inputs=inputs,
                                    args=args, builder_image=builder_image)
            elif name == 'solver-oscm-pace2024-development-data':
                from .oscm_pace2024 import prepare_public_data
                prepare_public_data(root, resource, rows, payload, downloads, inputs=inputs,
                                    args=args, builder_image=builder_image)
            elif name == 'solver-oscm-pace2024-development-tools':
                from .oscm_pace2024_tools import prepare_tools
                prepare_tools(root, resource, rows, payload, downloads, inputs=inputs,
                              args=args, builder_image=builder_image)
            elif name == 'solver-logic-syn-iwls2023-development-data':
                from .logic_syn import prepare_public_data
                prepare_public_data(root, resource, rows, payload, downloads, inputs=inputs)
            elif name == 'solver-logic-syn-iwls2023-development-tools':
                from .logic_syn import prepare_abc_source
                prepare_abc_source(root, resource, rows, payload, downloads, inputs=inputs)
            elif resource.get('recipe_format') == 'fixed_tar':
                recipe = load(within(root, resource['recipe']))
                extract_tar(input_file(recipe['source'], downloads, inputs), payload, rows)
            elif resource.get('recipe_format') == 'official_build':
                prepare_official_build(root, resource, rows, payload, downloads, inputs=inputs,
                                       args=args, builder_image=builder_image)
            else:
                raise ValueError(f'No preparation recipe implementation: {name}')
            verify(payload, rows)
            completion = {'content_digest': identity, 'manifest_sha256': resource['manifest_sha256']}
            completion.update(provenance)
            if resource.get('selected_data_recipe'):
                completion.update(selected_data_recipe=resource['selected_data_recipe'],
                                  data_recipe_signature=resource['data_recipe_signature'],
                                  recipe_sha256=digest(within(root, resource['recipe'])),
                                  source_sha256=resource['source_inputs'][0]['sha256'])
            (staged / '.complete.json').write_text(json.dumps(completion) + '\n')
            os.replace(staged, target)
    return target / 'rootfs'


def data_image_source_paths(root, resource, recipe=None):
    """List the files copied into a data-image context, including its notices."""
    root = Path(root)
    recipe = recipe if recipe is not None else load(within(root, resource['recipe']))
    paths = ['assets/data/Dockerfile']
    evidence = resource.get('evidence') or resource.get('distribution_evidence')
    if evidence:
        paths.append(evidence)
    paths.extend(declaration['path'] for declaration in recipe.get('license_files', []))
    bpplib_notice = 'docs/licenses/third-party/BPPLIB-CC-BY-NC-ND-4.0.txt'
    if resource['id'] == 'bpplib-development' and (root / bpplib_notice).is_file():
        paths.append(bpplib_notice)
    return list(dict.fromkeys(paths))


def data_image_metadata(resource):
    """Metadata embedded alongside the verified instance manifest."""
    return {key: resource[key] for key in ('id', 'content_version', 'distribution',
                                         'public_upload_allowed')}


def stage_data_context(root, name, rootfs, output, resource=None):
    """Create a data-only build context, excluding the local completion marker."""
    root = Path(root)
    resource = resource or resource_by_id(root, name)
    rows = manifest(root, resource)
    prefix = relative(resource['target_root'].lstrip('/')) if resource['target_root'] != '/' else ''
    verify(Path(rootfs) / prefix, rows)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for row in rows:
        destination = output / 'rootfs' / prefix / relative(row['path'])
        destination.parent.mkdir(parents=True, exist_ok=True)
        if row.get('type') == 'symlink':
            destination.symlink_to(row['link_target'])
        elif row.get('type') != 'hardlink':
            shutil.copy2(Path(rootfs) / prefix / row['path'], destination)
    for row in rows:
        if row.get('type') == 'hardlink':
            os.link(output / 'rootfs' / prefix / link_target(row, rows),
                    output / 'rootfs' / prefix / row['path'])
    metadata = output / 'manifest'
    metadata.mkdir()
    (metadata / 'files.json').write_text(json.dumps({'files': rows}, indent=2) + '\n')
    (metadata / 'content.json').write_text(json.dumps({**data_image_metadata(resource),
        'content_digest': content_digest(rows, resource['target_root'])}, indent=2) + '\n')
    licenses = output / 'licenses'
    licenses.mkdir()
    recipe = load(within(root, resource['recipe']))
    for declaration in recipe.get('license_files', []):
        source = within(root, declaration['path'])
        if (not source.is_file() or source.stat().st_size != declaration['bytes']
                or digest(source) != declaration['sha256']):
            raise ValueError(f'Data-image license hash or size differs: {declaration["path"]}')
    for path in data_image_source_paths(root, resource, recipe)[1:]:
        source = within(root, path)
        shutil.copy2(source, licenses / source.name)
    shutil.copy2(root / 'assets/data/Dockerfile', output / 'Dockerfile')
    return output


def build_data_image(root, name, cache, registry_ref, builder='remote', inputs=None,
                     context=None, metadata_file=None, registry_prefix=None, public=False, args=None):
    """Build on remote BuildKit and persist to an explicitly authorized registry."""
    if builder not in ('remote', 'remote-acr'):
        raise ValueError('Data images require an explicitly remote builder')
    prefix = registry_prefix.rstrip('/') if registry_prefix else ''
    if not prefix or not any(registry_ref.startswith(prefix + separator) for separator in ('/', ':')):
        raise ValueError('Build target must be inside the explicitly authorized registry prefix')
    if not context or not metadata_file:
        raise ValueError('Supply persistent context and metadata output paths')
    from .fixed_data_archive import effective_resource
    resource = effective_resource(Path(root), resource_by_id(Path(root), name),
                                  getattr(args, 'data_recipe', None))
    if resource['distribution'] not in ('redistributable', 'local_prepare', 'private_only'):
        raise ValueError(f'Resource has no accepted distribution decision: {name}')
    if public and (resource['distribution'] != 'redistributable'
                   or resource.get('public_upload_allowed') is not True):
        raise ValueError(f'Resource is not approved for public registry upload: {name}')
    rootfs = prepare_resource(root, name, cache, inputs, args=args, resource=resource)
    stage_data_context(root, name, rootfs, context, resource=resource)
    subprocess.run(['docker', 'buildx', 'build', '--builder', builder,
                    '--platform', 'linux/amd64', '--provenance=false', '--sbom=false',
                    '--push', '--metadata-file', str(metadata_file), '-t', registry_ref,
                    str(context)], check=True)
    digest_value = load(metadata_file).get('containerimage.digest')
    if not digest_value or not digest_value.startswith('sha256:'):
        raise ValueError('Build did not return a persisted image digest')
    resource = resource_by_id(Path(root), name)
    return {'id': name, 'reference': registry_ref.split('@')[0] + '@' + digest_value,
            'digest': digest_value, 'platform': 'linux/amd64',
            'content_digest': content_digest(manifest(Path(root), resource), resource['target_root']),
            'distribution': resource['distribution'], 'verification': {'build_push': True}}


# Temporary compatibility for consumers migrating to image records.
bundle_by_id = resource_by_id


def prepare_bundle(root, name, cache, archive=None):
    if archive is not None and name != 'qbf-public':
        raise ValueError('local_prepare uses pinned official inputs, not a published generated archive')
    return prepare_resource(root, name, cache, {'frozen_input': archive} if archive else None)


def make_archive(folder, rows, output):
    """Deterministic intermediate archive; data images are the delivery artifact."""
    verify(folder, rows)
    output = Path(output)
    with output.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w|', format=tarfile.PAX_FORMAT) as tar:
            for row in sorted(rows, key=lambda r: r['path']):
                p = Path(folder) / relative(row['path'])
                info = tarfile.TarInfo(row['path'])
                info.mode = int(row['mode'], 8)
                info.mtime = info.uid = info.gid = 0
                kind = row.get('type', 'file')
                if kind in ('symlink', 'hardlink'):
                    link_target(row, rows)
                    info.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
                    info.linkname = row['link_target']
                    tar.addfile(info)
                else:
                    info.size = row['bytes']
                    with p.open('rb') as stream:
                        tar.addfile(info, stream)
    return {'bytes': output.stat().st_size, 'sha256': digest(output)}
