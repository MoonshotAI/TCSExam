"""Reconstruct AHC058 public data with the official locked Rust generator."""
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

from .layout import load, within
from .resources import (acquire_official_builder, digest, download_official, input_file,
                        official_build_command, relative, run_official_container, verify)


PUBLIC_GENERATION = [
    ('h00.txt', 250854218785),
    ('h04.txt', 51468017913079),
    ('h19.txt', 129837058162460),
    ('h24.txt', 150636911777541),
    ('h27.txt', 161465247114690),
]
GENERATOR_FILES = {
    'tools/Cargo.lock',
    'tools/Cargo.toml',
    'tools/src/bin/gen.rs',
    'tools/src/lib.rs',
}
ADDITIONAL_FILES = GENERATOR_FILES | {
    'tools/README.html',
    'tools/README.md',
    'tools/seeds.txt',
    'tools/src/bin/vis.rs',
}
DIRECTORIES = {'tools', 'tools/in', 'tools/src', 'tools/src/bin'}


def _row(rows, path):
    matches = [row for row in rows if row.get('path') == path]
    if (len(matches) != 1 or matches[0].get('mode') != '0644'
            or matches[0].get('type', 'file') != 'file'):
        raise ValueError(f'AHC058 output declaration or mode differs: {path}')
    return matches[0]


def _selected_rows(rows, selection):
    official_selection = {
        'source_root': 'tools/in',
        'output_directory': 'app/instances',
        'first_instance': 0,
        'last_instance': 99,
        'instance_count': 100,
    }
    if selection.get('official') != official_selection:
        raise ValueError('Unexpected AHC058 official-instance selection')
    expected_generated = [
        {'path': f'app/instances/{name}', 'seed': seed}
        for name, seed in PUBLIC_GENERATION
    ]
    if selection.get('generated_public') != expected_generated:
        raise ValueError('Unexpected AHC058 public seed mapping')
    if set(selection) != {'official', 'generated_public'} or len(rows) != 105:
        raise ValueError('AHC058 development data must contain exactly 105 files')
    official = {}
    generated = []
    outputs = set()
    for number in range(100):
        stem = f'{number:04d}.txt'
        row = _row(rows, f'app/instances/{stem}')
        official[f'tools/in/{stem}'] = row
        outputs.add(row['path'])
    for index, declaration in enumerate(expected_generated):
        row = _row(rows, declaration['path'])
        generated.append((index, row, declaration['seed']))
        outputs.add(row['path'])
    if {row.get('path') for row in rows} != outputs:
        raise ValueError('AHC058 development data manifest contains an undeclared output')
    return official, generated


def _archive_policy(recipe, official):
    policy = recipe.get('archive_policy', {})
    if set(policy) != {'directories', 'additional_files', 'generator_files', 'checked_files'}:
        raise ValueError('AHC058 archive policy is incomplete')
    directories = {relative(value) for value in policy['directories']}
    additional = {relative(value) for value in policy['additional_files']}
    generator = {relative(value) for value in policy['generator_files']}
    if (directories != DIRECTORIES or additional != ADDITIONAL_FILES
            or generator != GENERATOR_FILES or set(official) & additional):
        raise ValueError('Unexpected AHC058 archive member declaration')
    checked = {}
    for row in policy['checked_files']:
        path = relative(row.get('path', ''))
        if (path not in additional or path in checked or not isinstance(row.get('bytes'), int)
                or row['bytes'] < 0 or not isinstance(row.get('sha256'), str)
                or len(row['sha256']) != 64):
            raise ValueError(f'Invalid AHC058 checked upstream member: {path}')
        checked[path] = row
    if set(checked) != additional:
        raise ValueError('Every additional AHC058 archive member must have a hash declaration')
    return directories, additional, generator, checked


def _copy_stream(stream, destination, row):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('wb') as output:
        shutil.copyfileobj(stream, output, 1024 * 1024)
    destination.chmod(int(row['mode'], 8))
    if destination.stat().st_size != row['bytes'] or digest(destination) != row['sha256']:
        raise ValueError(f'AHC058 output hash or size differs: {row["path"]}')


def _check_stream(stream, member, declaration, destination=None):
    hasher = hashlib.sha256()
    size = 0
    output = None
    try:
        if destination is not None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            output = destination.open('wb')
        while block := stream.read(1024 * 1024):
            size += len(block)
            hasher.update(block)
            if output is not None:
                output.write(block)
    finally:
        if output is not None:
            output.close()
    if size != declaration['bytes'] or hasher.hexdigest() != declaration['sha256']:
        raise ValueError(f'AHC058 checked upstream file hash or size differs: {member}')
    if destination is not None:
        destination.chmod(0o644)


def _extract_archive(archive, output, work, official, policy):
    directories, additional, generator, checked = policy
    seen = set()
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            name = relative(member.filename)
            if name in seen:
                raise ValueError(f'Duplicate AHC058 archive member: {name}')
            seen.add(name)
            if member.flag_bits & 0x1:
                raise ValueError(f'Encrypted AHC058 archive member: {name}')
            kind = stat.S_IFMT(member.external_attr >> 16)
            if member.is_dir():
                if name not in directories or kind not in (0, stat.S_IFDIR):
                    raise ValueError(f'Undeclared or special AHC058 archive directory: {name}')
                continue
            if kind not in (0, stat.S_IFREG) or (name not in official and name not in additional):
                raise ValueError(f'Duplicate, undeclared or special AHC058 member: {name}')
            if name in official:
                row = official[name]
                if member.file_size != row['bytes']:
                    raise ValueError(f'AHC058 official plaintext size differs: {name}')
                with source.open(member) as stream:
                    _copy_stream(stream, output / relative(row['path']), row)
            else:
                declaration = checked[name]
                if member.file_size != declaration['bytes']:
                    raise ValueError(f'AHC058 checked upstream file size differs: {name}')
                destination = Path(work) / name if name in generator else None
                with source.open(member) as stream:
                    _check_stream(stream, name, declaration, destination)
    expected = set(official) | directories | additional
    if seen != expected:
        raise ValueError(f'AHC058 archive is missing declared members: {sorted(expected - seen)}')


def _generation_command(recipe):
    generation = recipe.get('generation', {})
    expected = {
        'public_seed_file': 'PUBLIC5.seeds.txt',
        'public_output_directory': 'generated-public5',
        'calibration_seed_file': 'CALIBRATION100.seeds.txt',
        'calibration_output_directory': 'generated-calibration100',
    }
    if generation != expected or recipe['build'].get('cwd') != 'tools':
        raise ValueError('Unexpected AHC058 official generator parameters')
    return [
        '/bin/sh', '-eu', '-c',
        'cargo --version && rustc --version && '
        'cargo run --release --locked --bin gen -- '
        'CALIBRATION100.seeds.txt --dir generated-calibration100 && '
        'cargo run --release --locked --bin gen -- '
        'PUBLIC5.seeds.txt --dir generated-public5 && '
        'set -- generated-calibration100/*.txt && test "$#" -eq 100 && '
        'set -- generated-public5/*.txt && test "$#" -eq 5'
    ]


def _check_generated_directory(folder, expected, label):
    folder = Path(folder)
    actual = {path.name for path in folder.iterdir()} if folder.is_dir() else set()
    if actual != set(expected):
        raise ValueError(f'AHC058 {label} output paths differ: {sorted(actual)}')
    for name in expected:
        path = folder / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'AHC058 {label} output is not a regular file: {name}')


def prepare_public_data(root, resource, rows, output, downloads, inputs=None,
                        args=None, builder_image=None):
    recipe = load(within(root, resource['recipe']))
    if recipe.get('archive_format') != 'zip':
        raise ValueError('AHC058 reconstruction requires the fixed official ZIP')
    official, generated = _selected_rows(rows, recipe.get('selection', {}))
    policy = _archive_policy(recipe, official)
    build = recipe['build']
    source = recipe['source']
    image = builder_image or acquire_official_builder(
        root, build, Path(downloads).parent, args)
    supplied = (inputs or {}).get(source['id'])
    if supplied is None and source.get('url'):
        archive = download_official(source, downloads, build, image, args,
                                    resource_name=resource['id'])
    else:
        archive = input_file(source, downloads, inputs)
    output = Path(output)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.ahc058-atcoder-') as folder:
        work = Path(folder)
        public_output = work / 'public5'
        calibration_output = work / 'calibration100'
        public_output.mkdir()
        calibration_output.mkdir()
        _extract_archive(archive, output, work, official, policy)
        tools = work / 'tools'
        generation = recipe['generation']
        (tools / generation['public_seed_file']).write_text(
            ''.join(f'{seed}\n' for _, _, seed in generated))
        (tools / generation['calibration_seed_file']).write_text(
            ''.join(f'{number}\n' for number in range(100)))
        name = 'tcsexam-official-build-' + resource['id'] + '-' + os.urandom(16).hex()
        run_official_container(
            official_build_command(build, _generation_command(recipe), output, image,
                                   args, name=name),
            int(build.get('timeout_sec', 1800)),
            Path(downloads).parent / 'official-container-logs',
            copy_in=[(str(work) + '/.', '/tcsexam-output')],
            copy_out=[
                ('/tcsexam-output/tools/generated-public5/.', public_output),
                ('/tcsexam-output/tools/generated-calibration100/.', calibration_output),
            ],
        )
        _check_generated_directory(calibration_output, (f'{n:04d}.txt' for n in range(100)),
                                   'calibration')
        for member, row in official.items():
            stem = Path(member).name
            if (calibration_output / stem).read_bytes() != (output / relative(row['path'])).read_bytes():
                raise ValueError(f'AHC058 official generator calibration differs: {stem}')
        _check_generated_directory(public_output, (f'{index:04d}.txt' for index in range(5)),
                                   'public generator')
        for index, row, _ in generated:
            source_path = public_output / f'{index:04d}.txt'
            destination = output / relative(row['path'])
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)
            destination.chmod(int(row['mode'], 8))
            if destination.stat().st_size != row['bytes'] or digest(destination) != row['sha256']:
                raise ValueError(f'AHC058 generated public output hash or size differs: {row["path"]}')
    result = verify(output, rows)
    if result != {'files': 105, 'bytes': sum(row['bytes'] for row in rows)}:
        raise ValueError(f'AHC058 reconstructed output totals differ: {result}')
    return result
