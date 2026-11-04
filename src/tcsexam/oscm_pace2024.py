"""Reconstruct the PACE 2024 OSCM development data from two fixed official ZIPs."""
import hashlib
from pathlib import Path
import shutil
import stat
import zipfile

from .layout import load, within
from .resources import (acquire_official_builder, digest, download_official, input_file,
                        relative, verify)


TINY_INSTANCES = [
    'complete_4_5.gr',
    'cycle_8_shuffled.gr',
    'cycle_8_sorted.gr',
    'grid_9_shuffled.gr',
    'ladder_4_4_shuffled.gr',
    'ladder_4_4_sorted.gr',
    'matching_4_4.gr',
    'path_9_shuffled.gr',
    'path_9_sorted.gr',
    'plane_5_6.gr',
    'star_6.gr',
    'tree_6_10.gr',
    'website_20.gr',
]


def _row(rows, path):
    matches = [row for row in rows if row.get('path') == path]
    if (len(matches) != 1 or matches[0].get('mode') != '0644'
            or matches[0].get('type', 'file') != 'file'):
        raise ValueError(f'OSCM output declaration or mode differs: {path}')
    return matches[0]


def _selected_rows(rows, selection):
    exact = selection.get('exact_public', {})
    expected_exact = {
        'source': 'exact_public',
        'output_directory': 'app/instances',
        'first_instance': 1,
        'last_instance': 100,
        'instance_count': 100,
    }
    for name, value in expected_exact.items():
        if exact.get(name) != value:
            raise ValueError(f'Unexpected OSCM exact selection parameter: {name}')
    testsets = selection.get('testsets', {})
    expected_testsets = {
        'source': 'testsets',
        'archive_root': 'Pace2024-Testsets-603fd742fd525971cd78d93195d0eca7256056e9',
        'medium_output_directory': 'app/testsets/medium_test_set/instances',
        'medium_first_instance': 1,
        'medium_last_instance': 60,
        'tiny_output_directory': 'app/testsets/tiny_test_set/instances',
        'tiny_instances': TINY_INSTANCES,
    }
    for name, value in expected_testsets.items():
        if testsets.get(name) != value:
            raise ValueError(f'Unexpected OSCM test-set selection parameter: {name}')
    if len(rows) != 173:
        raise ValueError('OSCM development data manifest must contain exactly 173 files')
    required = {'exact_public': {}, 'testsets': {}}
    outputs = set()
    for number in range(1, 101):
        stem = f'{number}.gr'
        path = f'app/instances/{stem}'
        required['exact_public'][stem] = _row(rows, path)
        outputs.add(path)
    root = testsets['archive_root']
    for number in range(1, 61):
        stem = f'{number}.gr'
        path = f'app/testsets/medium_test_set/instances/{stem}'
        member = f'{root}/medium_test_set/instances/{stem}'
        required['testsets'][member] = _row(rows, path)
        outputs.add(path)
    for stem in TINY_INSTANCES:
        path = f'app/testsets/tiny_test_set/instances/{stem}'
        member = f'{root}/tiny_test_set/instances/{stem}'
        required['testsets'][member] = _row(rows, path)
        outputs.add(path)
    if {row.get('path') for row in rows} != outputs:
        raise ValueError('OSCM development data manifest contains an undeclared output')
    return required


def _archive_policy(recipe, name):
    policy = recipe.get('archive_policy', {}).get(name, {})
    if set(policy) != {'directories', 'additional_files', 'checked_files'}:
        raise ValueError(f'OSCM archive policy is incomplete: {name}')
    directories = [relative(value) for value in policy['directories']]
    additional = [relative(value) for value in policy['additional_files']]
    if (len(directories) != len(set(directories)) or len(additional) != len(set(additional))
            or set(directories) & set(additional)):
        raise ValueError(f'Duplicate OSCM archive policy member: {name}')
    checked = {}
    for row in policy['checked_files']:
        path = relative(row.get('path', ''))
        if (path not in additional or path in checked or not isinstance(row.get('bytes'), int)
                or row['bytes'] < 0 or not isinstance(row.get('sha256'), str)
                or len(row['sha256']) != 64):
            raise ValueError(f'Invalid OSCM checked upstream member: {path}')
        checked[path] = row
    return set(directories), set(additional), checked


def _copy_stream(stream, destination, row):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('wb') as output:
        shutil.copyfileobj(stream, output, 1024 * 1024)
    destination.chmod(int(row['mode'], 8))
    if destination.stat().st_size != row['bytes'] or digest(destination) != row['sha256']:
        raise ValueError(f'OSCM official plaintext hash or size differs: {row["path"]}')


def _check_additional(stream, member, declaration):
    hasher = hashlib.sha256()
    size = 0
    while block := stream.read(1024 * 1024):
        size += len(block)
        hasher.update(block)
    if declaration is not None and (size != declaration['bytes']
                                    or hasher.hexdigest() != declaration['sha256']):
        raise ValueError(f'OSCM checked upstream file hash or size differs: {member}')


def _extract_archive(archive, output, required, policy):
    directories, additional, checked = policy
    overlap = set(required) & (directories | additional)
    if overlap:
        raise ValueError(f'OSCM output and upstream-only members overlap: {sorted(overlap)}')
    seen = set()
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            name = relative(member.filename)
            if name in seen:
                raise ValueError(f'Duplicate OSCM archive member: {name}')
            seen.add(name)
            if member.is_dir():
                if name not in directories:
                    raise ValueError(f'Undeclared OSCM archive directory: {name}')
                continue
            kind = stat.S_IFMT(member.external_attr >> 16)
            if (kind not in (0, stat.S_IFREG) or member.flag_bits & 0x1
                    or (name not in required and name not in additional)):
                raise ValueError(f'Duplicate, undeclared or special OSCM member: {name}')
            if name in required:
                row = required[name]
                if member.file_size != row['bytes']:
                    raise ValueError(f'OSCM official plaintext size differs: {name}')
                with source.open(member) as stream:
                    _copy_stream(stream, output / relative(row['path']), row)
            elif name in checked:
                declaration = checked[name]
                if member.file_size != declaration['bytes']:
                    raise ValueError(f'OSCM checked upstream file size differs: {name}')
                with source.open(member) as stream:
                    _check_additional(stream, name, declaration)
    expected = set(required) | directories | additional
    if seen != expected:
        raise ValueError(f'OSCM archive is missing declared members: {sorted(expected - seen)}')


def prepare_public_data(root, resource, rows, output, downloads, inputs=None,
                        args=None, builder_image=None):
    recipe = load(within(root, resource['recipe']))
    if recipe.get('archive_format') != 'zip' or set(recipe.get('sources', {})) != {
            'exact_public', 'testsets'}:
        raise ValueError('OSCM reconstruction requires exactly the two official ZIP sources')
    required = _selected_rows(rows, recipe['selection'])
    policies = {name: _archive_policy(recipe, name) for name in required}
    build = recipe['build']
    image = builder_image
    archives = {}
    for name, source in recipe['sources'].items():
        supplied = (inputs or {}).get(source['id'])
        if supplied is None and source.get('url'):
            image = image or acquire_official_builder(root, build, Path(downloads).parent, args)
            archives[name] = download_official(source, downloads, build, image, args,
                                               resource_name=resource['id'] + '-' + name)
        else:
            archives[name] = input_file(source, downloads, inputs)
    output = Path(output)
    for name in ('exact_public', 'testsets'):
        _extract_archive(archives[name], output, required[name], policies[name])
    result = verify(output, rows)
    if result != {'files': 173, 'bytes': sum(row['bytes'] for row in rows)}:
        raise ValueError(f'OSCM reconstructed output totals differ: {result}')
