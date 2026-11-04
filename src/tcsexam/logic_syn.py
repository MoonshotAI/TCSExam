"""Reconstruct logic-syn public resources from pinned official sources."""
import copy
import hashlib
import io
import lzma
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile

from .layout import load, within
from .resources import copy_official_member, digest, input_file, relative


def prepare_public_data(root, resource, rows, output, downloads, inputs=None):
    recipe = load(within(root, resource['recipe']))
    archive = input_file(recipe['source'], downloads, inputs)
    selection = recipe['selection']
    source_root = selection['source_root'].strip('/')
    output_directory = selection['output_directory'].strip('/')
    license_output = relative(selection['license_output'])
    required = {}
    for row in rows:
        path = relative(row['path'])
        if path == license_output:
            member = source_root + '/' + relative(selection['license_member'])
        elif PurePosixPath(path).parent.as_posix() == output_directory and path.endswith('.truth'):
            member = (source_root + '/' + relative(selection['benchmark_directory'])
                      + '/' + PurePosixPath(path).name)
        else:
            raise ValueError(f'Undeclared logic-syn public output: {path}')
        if member in required:
            raise ValueError(f'Duplicate logic-syn source member: {member}')
        required[member] = row
    truth_count = sum(row['path'].endswith('.truth') for row in rows)
    if truth_count != selection['truth_table_count']:
        raise ValueError('Public truth-table manifest count differs from the recipe')
    seen = set()
    with tarfile.open(archive, 'r|gz') as source:
        for member in source:
            name = relative(member.name)
            if name not in required:
                continue
            row = required[name]
            if name in seen or not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f'Invalid or duplicate official logic-syn member: {name}')
            if member.size != row['bytes']:
                raise ValueError(f'Official logic-syn member size differs: {name}')
            with source.extractfile(member) as stream:
                copy_official_member(stream, output / relative(row['path']), row)
            seen.add(name)
    if seen != set(required):
        raise ValueError(f'Official IWLS archive is missing files: {sorted(set(required) - seen)}')


def _source_path(member_name, source_root):
    name = relative(member_name)
    if name == source_root:
        return ''
    prefix = source_root + '/'
    if not name.startswith(prefix):
        raise ValueError(f'Unexpected ABC archive root: {name}')
    return relative(name[len(prefix):])


def prepare_abc_source(root, resource, rows, output, downloads, inputs=None):
    recipe = load(within(root, resource['recipe']))
    transform_path = within(root, recipe['transform'])
    if digest(transform_path) != recipe['transform_sha256']:
        raise ValueError('ABC transform hash differs')
    transform = load(transform_path)
    archive = input_file(recipe['source'], downloads, inputs)
    if len(rows) != 1:
        raise ValueError('ABC resource must declare exactly one output archive')
    row = rows[0]
    destination = output / relative(row['path'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_root = relative(transform['source_root'])
    output_root = relative(transform['output_root'])
    excluded = {relative(path) for path in transform['excluded_paths']}
    omitted_directories = {relative(path) for path in transform['omitted_directory_entries']}
    mtimes = {relative(path) if path else '': value
              for path, value in transform['member_mtimes'].items()}
    mode_overrides = {relative(path) if path else '': value
                      for path, value in transform['mode_overrides'].items()}
    replacements = {}
    for path, replacement in transform['replacements'].items():
        data = replacement['text'].encode()
        if hashlib.sha256(data).hexdigest() != replacement['sha256']:
            raise ValueError(f'ABC replacement hash differs: {path}')
        replacements[relative(path)] = data
    metadata = transform['metadata']
    if metadata['tar_format'] != 'gnu' or metadata['xz_check'] != 'crc64':
        raise ValueError('Unsupported ABC archive format')
    seen = set()
    with tempfile.TemporaryDirectory(dir=destination.parent) as work:
        raw = Path(work) / 'abc.tar'
        with tarfile.open(raw, 'w', format=tarfile.GNU_FORMAT) as result:
            with tarfile.open(archive, 'r:gz') as source:
                upstream = {}
                for original in source.getmembers():
                    path = _source_path(original.name, source_root)
                    if path in excluded or (original.isdir() and path in omitted_directories):
                        continue
                    if path in upstream:
                        raise ValueError(f'Duplicate ABC member: {path}')
                    upstream[path] = original
                if set(upstream) != set(mtimes):
                    raise ValueError('ABC archive member set differs from the transform')
                for path in mtimes:
                    original = upstream[path]
                    member = copy.copy(original)
                    member.name = output_root + ('/' + path if path else '')
                    member.uid = metadata['uid']
                    member.gid = metadata['gid']
                    member.uname = metadata['uname']
                    member.gname = metadata['gname']
                    member.mtime = mtimes[path]
                    member.mode = mode_overrides.get(path, member.mode)
                    member.pax_headers = {}
                    data = None
                    if original.isfile():
                        if path in replacements:
                            data = replacements[path]
                        else:
                            data = source.extractfile(original).read()
                        member.size = len(data)
                    result.addfile(member, io.BytesIO(data) if data is not None else None)
                    seen.add(path)
        if seen != set(mtimes):
            raise ValueError(f'ABC archive member set differs: {sorted(set(mtimes) - seen)}')
        if digest(raw) != transform['uncompressed_tar_sha256']:
            raise ValueError('Reconstructed uncompressed ABC tar hash differs')
        with lzma.open(destination, 'wb', format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
                       preset=metadata['xz_preset']) as compressed, raw.open('rb') as source:
            shutil.copyfileobj(source, compressed, 1024 * 1024)
    destination.chmod(int(row['mode'], 8))
    if destination.stat().st_size != row['bytes'] or digest(destination) != row['sha256']:
        raise ValueError('Reconstructed ABC archive hash or size differs')
