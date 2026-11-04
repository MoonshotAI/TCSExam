"""Reconstruct PACE 2019 public vertex-cover data with a fixed XZ toolchain."""
import lzma
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import tarfile
import tempfile
import zipfile
import stat

from .layout import load, within
from .resources import (acquire_official_builder, digest, download_official, input_file,
                        official_build_command, relative, run_official_container)


def _source(root, source, build, image, downloads, inputs, args, resource_name):
    supplied = (inputs or {}).get(source['id'])
    if supplied is None and source.get('url'):
        return download_official(source, downloads, build, image, args,
                                 resource_name=resource_name)
    return input_file(source, downloads, inputs)


def _selected_rows(rows, selection):
    expected = {
        'source_root': 'public',
        'output_directory': 'app/instances',
        'first_instance': 1,
        'last_instance': 199,
        'instance_step': 2,
        'instance_count': 100,
    }
    if selection.get('output_directory') == 'tests/instances':
        expected.update(source_root='all', output_directory='tests/instances', first_instance=2, last_instance=200)
    for name, value in expected.items():
        if selection.get(name) != value:
            raise ValueError(f'Unexpected VC public selection parameter: {name}')
    if len(rows) != selection['instance_count']:
        raise ValueError('VC public data manifest must contain exactly 100 instances')
    required = {}
    for number in range(selection['first_instance'], selection['last_instance'] + 1,
                        selection['instance_step']):
        stem = f'vc-exact_{number:03d}.gr'
        member = selection['source_root'] + '/' + stem
        path = selection['output_directory'] + '/' + stem.removesuffix('.gr') + '.xz'
        matches = [row for row in rows if row.get('path') == path]
        if len(matches) != 1 or matches[0].get('mode') != '0644':
            raise ValueError(f'VC output declaration or mode differs: {path}')
        required[member] = matches[0]
    declared = {row.get('path') for row in rows}
    if declared != {row['path'] for row in required.values()}:
        raise ValueError('VC public data manifest contains an undeclared output')
    return required


def _compression_command(recipe):
    compression = recipe['compression']
    arguments = ['--format=xz', '--stdout', '--check=crc64']
    if (compression.get('format') != 'xz' or compression.get('check') != 'crc64'
            or 'threads' in compression or compression.get('arguments') != arguments
            or compression.get('preset') != 9 or compression.get('preset_overrides', {})):
        raise ValueError('Unsupported VC XZ compression parameters')
    tool = compression['tool']
    if tool.get('version') != '5.2.5' or tool.get('archive_root') != 'xz-5.2.5':
        raise ValueError('VC reconstruction requires XZ Utils 5.2.5')
    root = relative(tool['archive_root'])
    configure = tool.get('configure')
    if (not isinstance(configure, list) or not configure
            or not all(isinstance(value, str) and value for value in configure)):
        raise ValueError('XZ configure arguments must be a nonempty string list')
    xz = '/tmp/' + root + '/src/xz/xz'
    output_directory = relative(recipe.get('selection', {}).get('output_directory', 'app/instances'))
    if output_directory not in ('app/instances', 'tests/instances'):
        raise ValueError('Unsupported VC output directory')
    quoted_arguments = ' '.join(shlex.quote(value) for value in arguments)
    return [
        '/bin/sh', '-eu', '-c',
        f'tar -xzf xz-source.tar.gz -C /tmp && '
        f'cd /tmp/{shlex.quote(root)} && '
        f'./configure {" ".join(shlex.quote(value) for value in configure)} && '
        f'make -j2 && '
        f'test "$({shlex.quote(xz)} --version | head -n 1)" = "xz (XZ Utils) 5.2.5" && '
        f'test "$({shlex.quote(xz)} --version | tail -n 1)" = "liblzma 5.2.5" && '
        f'{shlex.quote(xz)} --version && '
        f'cd /tcsexam-output && '
        f'mkdir -p output/{output_directory} && '
        f'for source in input/vc-exact_*.gr; do '
        f'name=${{source##*/}}; destination=output/{output_directory}/${{name%.gr}}.xz; '
        f'{shlex.quote(xz)} {quoted_arguments} -9 "$source" > "$destination"; '
        f'chmod 0644 "$destination"; '
        f'{shlex.quote(xz)} --decompress --stdout "$destination" | cmp - "$source"; '
        f'done && '
        f'set -- output/{output_directory}/*.xz && test "$#" -eq 100'
    ]


def _same_plain_text(compressed, source):
    with lzma.open(compressed, 'rb') as left, source.open('rb') as right:
        while True:
            left_block = left.read(1024 * 1024)
            right_block = right.read(1024 * 1024)
            if left_block != right_block:
                return False
            if not left_block:
                return True


def prepare_public_data(root, resource, rows, output, downloads, inputs=None,
                        args=None, builder_image=None):
    recipe = load(within(root, resource['recipe']))
    required = _selected_rows(rows, recipe['selection'])
    build = recipe['build']
    image = builder_image or acquire_official_builder(
        root, build, Path(downloads).parent, args)
    archive = _source(root, recipe['source'], build, image, downloads, inputs, args,
                      resource['id'])
    tool_source = recipe['compression']['tool']['source']
    tool_archive = _source(root, tool_source, build, image, downloads, inputs, args,
                           resource['id'] + '-xz')
    output = Path(output)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.vc-pace2019-') as folder:
        work = Path(folder)
        source_directory = work / 'input'
        source_directory.mkdir()
        (work / 'output').mkdir()
        shutil.copyfile(tool_archive, work / 'xz-source.tar.gz')
        seen = set()
        if recipe.get('archive_format') == 'zip':
            source_members = recipe['source_members']
            if set(source_members) != set(required) or len(set(source_members.values())) != len(required):
                raise ValueError('VC ZIP input allowlist differs from the exact selection')
            with zipfile.ZipFile(archive) as source:
                for name in required:
                    member = source.getinfo(relative(source_members[name]))
                    if (member.is_dir() or member.flag_bits & 1 or
                            stat.S_IFMT(member.external_attr >> 16) not in (0, stat.S_IFREG)):
                        raise ValueError('Selected VC ZIP member is not regular and unencrypted')
                    destination = source_directory / PurePosixPath(name).name
                    with source.open(member) as stream, destination.open('wb') as target:
                        shutil.copyfileobj(stream, target, 1024 * 1024)
                    seen.add(name)
        else:
            with tarfile.open(archive, 'r|bz2') as source:
                for member in source:
                    name = relative(member.name)
                    if member.isdir():
                        if name != recipe['selection']['source_root']:
                            raise ValueError(f'Undeclared VC archive directory: {name}')
                        continue
                    if (name in seen or name not in required or not member.isfile()
                            or member.issym() or member.islnk()):
                        raise ValueError(f'Duplicate, undeclared or special VC member: {name}')
                    seen.add(name)
                    destination = source_directory / PurePosixPath(name).name
                    with source.extractfile(member) as stream, destination.open('wb') as target:
                        shutil.copyfileobj(stream, target, 1024 * 1024)
        if seen != set(required):
            raise ValueError(f'VC archive is missing public instances: '
                             f'{sorted(set(required) - seen)}')
        name = ('tcsexam-official-build-' + resource['id'] + '-'
                + os.urandom(16).hex())
        run_official_container(
            official_build_command(build, _compression_command(recipe), output, image,
                                   args, name=name),
            int(build.get('timeout_sec', 3600)),
            Path(downloads).parent / 'official-container-logs',
            copy_in=[(str(work) + '/.', '/tcsexam-output')],
            copy_out=[('/tcsexam-output/output/.', output)],
        )
        for member, row in required.items():
            destination = output / relative(row['path'])
            if destination.is_symlink() or not destination.is_file():
                raise ValueError(f'VC compression did not produce a regular file: {member}')
            destination.chmod(int(row['mode'], 8))
            if destination.stat().st_size != row['bytes'] or digest(destination) != row['sha256']:
                raise ValueError(f'VC compressed output hash or size differs: {member}')
            if not _same_plain_text(destination, source_directory / PurePosixPath(member).name):
                raise ValueError(f'VC decompressed output differs from official plaintext: {member}')
