"""Rebuild frozen AtCoder input splits from the official locked generator.

The recipe is maintainer material. It is never copied into a model workspace.
"""
import os
import importlib.util
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

from .layout import load, within
from .resources import (acquire_official_builder, digest, download_official, input_file,
                        official_build_command, relative, run_official_container, verify)

GENERATOR_FILES = {'tools/Cargo.toml', 'tools/Cargo.lock',
                   'tools/src/bin/gen.rs', 'tools/src/lib.rs'}


def selection(rows, recipe):
    """Validate a complete explicit split; do not infer membership from order."""
    declarations = recipe['outputs']
    if not declarations or len(declarations) != len(rows):
        raise ValueError('AtCoder output count differs from the frozen split')
    expected = {relative(row['path']): row for row in rows}
    outputs = {relative(row['path']): row for row in declarations}
    if len(expected) != len(rows) or len(outputs) != len(declarations) or set(expected) != set(outputs):
        raise ValueError('AtCoder output paths differ from the frozen split')
    seeds = set()
    for path, row in outputs.items():
        if expected[path].get('type', 'file') != 'file':
            raise ValueError('AtCoder inputs must be regular files')
        if ('source_member' in row) == ('seed' in row):
            raise ValueError('Each AtCoder output needs one source member or seed')
        if 'source_member' in row:
            relative(row['source_member'])
        else:
            seed = row['seed']
            if type(seed) is not int or not 100 <= seed < 2**64 or seed in seeds:
                raise ValueError('Invalid or duplicate AtCoder generation seed')
            seeds.add(seed)
    return expected, outputs


def extract_inputs(archive, work, output, rows, recipe):
    """Extract only the checked generator and explicitly selected official inputs."""
    from .ahc058_atcoder import _check_stream, _copy_stream
    expected, declarations = selection(rows, recipe)
    checked = {relative(row['path']): row for row in recipe['generator_files']}
    if set(checked) != GENERATOR_FILES:
        raise ValueError('AtCoder generator allowlist differs')
    members = {row['source_member']: expected[path] for path, row in declarations.items()
               if 'source_member' in row}
    calibration = {relative(row['path']): row for row in recipe['calibration_files']}
    if set(calibration) != {f'tools/in/{number:04d}.txt' for number in range(100)}:
        raise ValueError('AtCoder calibration must retain all 100 official inputs')
    wanted = set(checked) | set(members) | set(calibration)
    seen = set()
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            name = relative(member.filename)
            if name not in wanted:
                continue
            if name in seen or member.is_dir() or member.flag_bits & 1:
                raise ValueError(f'Duplicate, directory or encrypted AtCoder member: {name}')
            if stat.S_IFMT(member.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError(f'AtCoder member must be a regular file: {name}')
            seen.add(name)
            if name in checked:
                with source.open(member) as stream:
                    _check_stream(stream, name, checked[name], work / name)
            if name in calibration:
                with source.open(member) as stream:
                    _check_stream(stream, name, calibration[name], work / name)
            if name in members:
                with source.open(member) as stream:
                    _copy_stream(stream, output / members[name]['path'], members[name])
    if seen != wanted:
        raise ValueError(f'AtCoder archive is missing required files: {sorted(wanted-seen)}')
    return expected, declarations


def generation_command():
    return ['/bin/sh', '-eu', '-c',
            'cargo --version && rustc --version && '
            'cargo run --release --locked --bin gen -- CALIBRATION.seeds.txt --dir calibration && '
            'cargo run --release --locked --bin gen -- SELECTED.seeds.txt --dir selected']


def prepare_data(root, resource, rows, output, downloads, inputs=None, args=None,
                 builder_image=None):
    """Prepare a hash-checked public or hidden payload using one exact recipe."""
    recipe = load(within(root, resource['recipe']))
    selection(rows, recipe)
    build = recipe['build']
    if build.get('cwd') != 'tools':
        raise ValueError('AtCoder generator working directory must be tools')
    image = builder_image or acquire_official_builder(root, build, Path(downloads).parent, args)
    source = recipe['source']
    if (inputs or {}).get(source['id']) is None and source.get('url'):
        archive = download_official(source, downloads, build, image, args,
                                    resource_name=resource['id'])
    else:
        archive = input_file(source, downloads, inputs)
    output = Path(output)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.atcoder-generator-') as folder:
        work = Path(folder)
        expected, declarations = extract_inputs(archive, work, output, rows, recipe)
        generated = [(path, row) for path, row in declarations.items() if 'seed' in row]
        tools = work / 'tools'
        (tools / 'CALIBRATION.seeds.txt').write_text(''.join(f'{n}\n' for n in range(100)))
        (tools / 'SELECTED.seeds.txt').write_text(''.join(f'{row["seed"]}\n' for _, row in generated))
        results = work / 'results'
        results.mkdir()
        name = 'tcsexam-atcoder-' + resource['id'] + '-' + os.urandom(8).hex()
        run_official_container(
            official_build_command(build, generation_command(), output, image, args, name=name),
            int(build.get('timeout_sec', 1800)), Path(downloads).parent / 'official-container-logs',
            copy_in=[(str(work) + '/.', '/tcsexam-output')],
            copy_out=[('/tcsexam-output/tools/calibration', results / 'calibration'),
                      ('/tcsexam-output/tools/selected', results / 'selected')],
        )
        for row in recipe['calibration_files']:
            name = Path(row['path']).name
            if digest(results / 'calibration' / name) != row['sha256']:
                raise ValueError(f'Official AtCoder generator calibration differs: {name}')
        selected = results / 'selected'
        if {p.name for p in selected.iterdir()} != {f'{n:04d}.txt' for n in range(len(generated))}:
            raise ValueError('AtCoder generated output membership differs')
        transform = None
        transform_rows = {}
        if recipe.get('transform'):
            for field in ('transform', 'transform_manifest'):
                if digest(within(root, recipe[field])) != recipe[field + '_sha256']:
                    raise ValueError('AtCoder transformation source identity differs')
            spec = importlib.util.spec_from_file_location('_tcsexam_atcoder_transform', within(root, recipe['transform']))
            transform = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(transform)
            transform_rows = load(within(root, recipe['transform_manifest']))['instances']
        for n, (path, declaration) in enumerate(generated):
            dest = output / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            source_path = selected / f'{n:04d}.txt'
            if declaration.get('transform_key'):
                if transform is None:
                    raise ValueError('AtCoder transformation implementation missing')
                change = transform_rows[declaration['transform_key']]
                if digest(source_path) != change['src_sha256_plain']:
                    raise ValueError('AtCoder generated source hash differs')
                instance = transform.load_instance(str(source_path))
                perm = change['perm']
                if sorted(perm) != list(range(instance['N'])):
                    raise ValueError('AtCoder vertex or machine mapping is not a permutation')
                data = transform.emit(transform.transform_instance(instance, perm))
                dest.write_bytes(data)
                if digest(dest) != change['out_sha256_plain']:
                    raise ValueError('AtCoder transformed input hash differs')
            else:
                shutil.copyfile(source_path, dest)
            dest.chmod(int(expected[path]['mode'], 8))
    return verify(output, rows)
