"""Prepare the OSCM NumPy tool payload from its fixed official wheel."""
import base64
import csv
import hashlib
import io
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

from .layout import load, within
from .resources import (acquire_official_builder, digest, download_official, input_file,
                        relative, verify)


def _selected_row(rows, recipe):
    filename = recipe['wheel']['filename']
    expected_path = 'opt/ocm/pkg/' + filename
    if len(rows) != 1 or rows[0].get('path') != expected_path:
        raise ValueError('OSCM tools manifest must contain exactly the fixed NumPy wheel')
    row = rows[0]
    source = recipe['source']
    if (row.get('type', 'file') != 'file' or row.get('mode') != '0644'
            or row.get('bytes') != source['bytes'] or row.get('sha256') != source['sha256']):
        raise ValueError('OSCM tools wheel declaration differs from the fixed official source')
    return row


def _notice_declarations(recipe):
    declarations = recipe['wheel']['notice_members']
    if len(declarations) != 4:
        raise ValueError('OSCM tools requires the four reviewed NumPy notice members')
    notices = {}
    for row in declarations:
        member = relative(row.get('member', ''))
        path = relative(row.get('path', ''))
        if (member in notices or not isinstance(row.get('bytes'), int) or row['bytes'] < 0
                or not isinstance(row.get('sha256'), str) or len(row['sha256']) != 64):
            raise ValueError(f'Invalid OSCM tools notice declaration: {member}')
        notices[member] = row
    staged = {row['path']: row for row in recipe.get('license_files', [])}
    if set(staged) != {row['path'] for row in declarations}:
        raise ValueError('OSCM tools staged licenses must equal the reviewed wheel notices')
    for row in declarations:
        other = staged[row['path']]
        if other['bytes'] != row['bytes'] or other['sha256'] != row['sha256']:
            raise ValueError(f'OSCM tools staged notice declaration differs: {row["path"]}')
    return notices


def _read_record(source, wheel):
    name = wheel['record_member']
    with source.open(name) as stream:
        data = stream.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError('NumPy wheel RECORD exceeds the preparation limit')
    if len(data) != wheel['record_bytes'] or hashlib.sha256(data).hexdigest() != wheel['record_sha256']:
        raise ValueError('NumPy wheel RECORD hash or size differs')
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError('NumPy wheel RECORD is not UTF-8') from exc
    records = {}
    for values in csv.reader(io.StringIO(text)):
        if not values:
            continue
        if len(values) != 3:
            raise ValueError('Malformed NumPy wheel RECORD row')
        member = relative(values[0])
        if member != values[0] or member in records:
            raise ValueError(f'Duplicate or non-canonical NumPy RECORD member: {member}')
        encoded, size = values[1], values[2]
        if member == name:
            if encoded or size:
                raise ValueError('NumPy RECORD must not hash itself')
            records[member] = None
            continue
        if not encoded.startswith('sha256=') or not size.isdigit():
            raise ValueError(f'Unsupported NumPy RECORD digest or size: {member}')
        records[member] = (encoded.removeprefix('sha256='), int(size))
    if name not in records or len(records) != wheel['file_members']:
        raise ValueError('NumPy wheel RECORD file count differs')
    return records


def _record_directories(records):
    directories = set()
    for name in records:
        for parent in PurePosixPath(name).parents:
            if str(parent) == '.':
                break
            directories.add(str(parent))
    return directories


def _validate_wheel(archive, root, recipe, notices):
    wheel = recipe['wheel']
    with zipfile.ZipFile(archive) as source:
        records = _read_record(source, wheel)
        allowed_directories = _record_directories(records)
        seen = set()
        files = set()
        observed_notices = {}
        for member in source.infolist():
            raw = member.filename
            name = relative(raw)
            if name in seen:
                raise ValueError(f'Duplicate NumPy wheel member: {name}')
            seen.add(name)
            if member.is_dir():
                if raw != name + '/' or name not in allowed_directories:
                    raise ValueError(f'Undeclared NumPy wheel directory: {name}')
                continue
            kind = stat.S_IFMT(member.external_attr >> 16)
            if (raw != name or name not in records or kind not in (0, stat.S_IFREG)
                    or member.flag_bits & 0x1):
                raise ValueError(f'Undeclared or special NumPy wheel member: {name}')
            declaration = records[name]
            if declaration is not None and member.file_size != declaration[1]:
                raise ValueError(f'NumPy RECORD member size differs: {name}')
            hasher = hashlib.sha256()
            size = 0
            with source.open(member) as stream:
                while block := stream.read(1024 * 1024):
                    size += len(block)
                    hasher.update(block)
            if declaration is not None:
                encoded = base64.urlsafe_b64encode(hasher.digest()).rstrip(b'=').decode('ascii')
                if size != declaration[1] or encoded != declaration[0]:
                    raise ValueError(f'NumPy RECORD member hash or size differs: {name}')
            if name in notices:
                observed_notices[name] = (size, hasher.hexdigest())
            files.add(name)
        if files != set(records):
            raise ValueError(f'NumPy wheel is missing RECORD members: '
                             f'{sorted(set(records) - files)}')
    for name, declaration in notices.items():
        if observed_notices.get(name) != (declaration['bytes'], declaration['sha256']):
            raise ValueError(f'NumPy wheel notice hash or size differs: {name}')
        path = within(root, declaration['path'])
        if (path.is_symlink() or not path.is_file() or path.stat().st_size != declaration['bytes']
                or digest(path) != declaration['sha256']):
            raise ValueError(f'Staged NumPy notice differs from the wheel: {declaration["path"]}')


def prepare_tools(root, resource, rows, output, downloads, inputs=None,
                  args=None, builder_image=None):
    recipe = load(within(root, resource['recipe']))
    if recipe.get('archive_format') != 'wheel':
        raise ValueError('OSCM tools reconstruction requires an official wheel')
    row = _selected_row(rows, recipe)
    notices = _notice_declarations(recipe)
    source = recipe['source']
    supplied = (inputs or {}).get(source['id'])
    image = builder_image
    if supplied is None and source.get('url'):
        image = image or acquire_official_builder(root, recipe['build'], Path(downloads).parent, args)
        archive = download_official(source, downloads, recipe['build'], image, args,
                                    resource_name=resource['id'])
    else:
        archive = input_file(source, downloads, inputs)
    _validate_wheel(archive, root, recipe, notices)
    destination = Path(output) / relative(row['path'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(archive, destination)
    destination.chmod(int(row['mode'], 8))
    if destination.stat().st_size != row['bytes'] or digest(destination) != row['sha256']:
        raise ValueError('OSCM tools output wheel hash or size differs')
    result = verify(Path(output), rows)
    if result != {'files': 1, 'bytes': row['bytes']}:
        raise ValueError(f'OSCM tools output totals differ: {result}')
