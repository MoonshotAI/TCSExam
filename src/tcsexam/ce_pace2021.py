"""Reconstruct PACE 2021 public cluster-editing data with a fixed XZ toolchain."""
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import tarfile
import tempfile

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
        'source_root': 'heur',
        'output_directory': 'app/instances',
        'first_instance': 1,
        'last_instance': 199,
        'instance_step': 2,
        'instance_count': 100,
    }
    if selection.get('output_directory') == 'tests/instances':
        expected.update(output_directory='tests/instances', first_instance=2, last_instance=200)
    for name, value in expected.items():
        if selection.get(name) != value:
            raise ValueError(f'Unexpected PACE public selection parameter: {name}')
    if len(rows) != selection['instance_count']:
        raise ValueError('PACE public data manifest must contain exactly 100 instances')
    required = {}
    for number in range(selection['first_instance'], selection['last_instance'] + 1,
                        selection['instance_step']):
        stem = f'heur{number:03d}.gr'
        member = selection['source_root'] + '/' + stem
        path = selection['output_directory'] + '/' + stem + '.xz'
        matches = [row for row in rows if row.get('path') == path]
        if len(matches) != 1 or matches[0].get('mode') != '0644':
            raise ValueError(f'PACE output declaration or mode differs: {path}')
        required[member] = matches[0]
    declared = {row.get('path') for row in rows}
    if declared != {row['path'] for row in required.values()}:
        raise ValueError('PACE public data manifest contains an undeclared output')
    return required


def _compression_command(recipe):
    compression = recipe['compression']
    hidden = recipe.get('selection', {}).get('output_directory') == 'tests/instances'
    threads = compression.get('threads')
    preset = compression.get('preset')
    if ((not hidden and (threads != 2 or preset != 9))
            or (hidden and (threads not in (1, 2) or preset not in (6, 9)))):
        raise ValueError('Unsupported frozen PACE XZ thread or preset parameters')
    arguments = ['--format=xz', '--stdout', f'--threads={threads}', '--check=crc64']
    selection = recipe.get('selection', {'output_directory': 'app/instances'})
    output_directory = relative(selection['output_directory'])
    if output_directory not in ('app/instances', 'tests/instances'):
        raise ValueError('Unsupported PACE output directory')
    overrides = compression.get('preset_overrides')
    if not isinstance(overrides, dict):
        raise ValueError('PACE preset overrides must be explicit')
    if hidden:
        allowed = {f'heur{number:03d}.gr' for number in range(2, 201, 2)}
        if any(name not in allowed or value not in (6, 9) for name, value in overrides.items()):
            raise ValueError('PACE hidden compression override differs from the selected files')
    elif overrides != {'heur199.gr': 6}:
        raise ValueError('PACE public compression overrides differ')
    override_command = ''
    for value in (6, 9):
        names = sorted(name for name, level in overrides.items() if level == value)
        if names:
            override_command += 'case "$name" in ' + '|'.join(names) + f') preset={value} ;; esac; '
    if not hidden:
        override_command = 'if [ "$name" = heur199.gr ]; then preset=6; fi; '
    if (compression.get('format') != 'xz' or compression.get('check') != 'crc64'
            or compression.get('arguments') != arguments
            or compression.get('preset_overrides') != overrides):
        raise ValueError('Unsupported PACE XZ compression parameters')
    tool = compression['tool']
    if tool.get('version') != '5.8.4' or tool.get('archive_root') != 'xz-5.8.4':
        raise ValueError('PACE reconstruction requires XZ Utils 5.8.4')
    root = relative(tool['archive_root'])
    configure = tool.get('configure')
    if (not isinstance(configure, list) or not configure
            or not all(isinstance(value, str) and value for value in configure)):
        raise ValueError('XZ configure arguments must be a nonempty string list')
    xz = '/tmp/' + root + '/src/xz/xz'
    quoted_arguments = ' '.join(shlex.quote(value) for value in arguments)
    return [
        '/bin/sh', '-eu', '-c',
        f'tar -xzf xz-source.tar.gz -C /tmp && '
        f'cd /tmp/{shlex.quote(root)} && '
        f'./configure {" ".join(shlex.quote(value) for value in configure)} && '
        f'make -j2 && '
        f'test "$({shlex.quote(xz)} --version | head -n 1)" = "xz (XZ Utils) 5.8.4" && '
        f'{shlex.quote(xz)} --version && '
        f'cd /tcsexam-output && '
        f'mkdir -p output/{output_directory} && '
        f'for source in input/heur*.gr; do '
        f'name=${{source##*/}}; preset={preset}; '
        f'{override_command}'
        f'destination=output/{output_directory}/$name.xz; '
        f'{shlex.quote(xz)} {quoted_arguments} "-$preset" "$source" > "$destination"; '
        f'chmod 0644 "$destination"; '
        f'{shlex.quote(xz)} --decompress --stdout "$destination" | cmp - "$source"; '
        f'done'
    ]


def prepare_public_data(root, resource, rows, output, downloads, inputs=None,
                        args=None, builder_image=None):
    recipe = load(within(root, resource['recipe']))
    required = _selected_rows(rows, recipe['selection'])
    build = recipe['build']
    image = builder_image or acquire_official_builder(
        root, build, Path(downloads).parent, args)
    archive = (None if recipe.get('input_files') else
               _source(root, recipe['source'], build, image, downloads, inputs, args, resource['id']))
    tool_source = recipe['compression']['tool']['source']
    tool_archive = _source(root, tool_source, build, image, downloads, inputs, args,
                           resource['id'] + '-xz')
    output = Path(output)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.ce-pace2021-') as folder:
        work = Path(folder)
        source_directory = work / 'input'
        source_directory.mkdir()
        (work / 'output').mkdir()
        shutil.copyfile(tool_archive, work / 'xz-source.tar.gz')
        seen = set()
        if recipe.get('input_files'):
            input_files = recipe['input_files']
            sources = {source['id']: source for source in recipe['sources']}
            if set(input_files) != {PurePosixPath(member).name for member in required}:
                raise ValueError('PACE per-file sources differ from the exact selected instances')
            for member in required:
                stem = PurePosixPath(member).name
                source = sources[input_files[stem]]
                original = _source(root, source, build, image, downloads, inputs, args,
                                   resource['id'] + '-' + stem)
                shutil.copyfile(original, source_directory / stem)
                seen.add(member)
        else:
            with tarfile.open(archive, 'r|gz') as source:
                for member in source:
                    name = relative(member.name)
                    if member.isdir():
                        if name != recipe['selection']['source_root']:
                            raise ValueError(f'Undeclared PACE archive directory: {name}')
                        continue
                    if (name in seen or name not in required or not member.isfile()
                            or member.issym() or member.islnk()):
                        raise ValueError(f'Duplicate, undeclared or special PACE member: {name}')
                    seen.add(name)
                    destination = source_directory / PurePosixPath(name).name
                    with source.extractfile(member) as stream, destination.open('wb') as target:
                        shutil.copyfileobj(stream, target, 1024 * 1024)
        if seen != set(required):
            raise ValueError(f'PACE archive is missing public instances: '
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
            raise ValueError(f'PACE compression did not produce a regular file: {member}')
        destination.chmod(int(row['mode'], 8))
        if destination.stat().st_size != row['bytes'] or digest(destination) != row['sha256']:
            raise ValueError(f'PACE compressed output hash or size differs: {member}')
