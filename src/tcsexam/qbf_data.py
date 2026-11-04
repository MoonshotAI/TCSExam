"""Rebuild frozen hidden QDIMACS inputs from the fixed official artifact."""
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile

from .layout import load, within
from .resources import (acquire_official_builder, digest, download_official, input_file,
                        official_build_command, relative, run_official_container, verify)


def generation_command(recipe=None):
    version = (recipe or {}).get('compression_tool_version', '5.2.5')
    if version not in ('5.2.5', '5.8.4'):
        raise ValueError('Unsupported fixed QBF XZ version')
    return ['/bin/sh', '-eu', '-c',
            'apt-get update -qq && apt-get install -y -qq python3 build-essential ca-certificates && '
            'tar -xzf /tcsexam-output/xz-source.tar.gz -C /tmp && '
            f'cd /tmp/xz-{version} && ./configure --disable-shared --enable-static --disable-nls && make -j2 && '
            f'test "$(/tmp/xz-{version}/src/xz/xz --version | head -n 1)" = "xz (XZ Utils) {version}" && '
            'cd /tcsexam-output && python3 worker.py recipe.json inputs output']


def prepare_data(root, resource, rows, output, downloads, inputs=None, args=None, builder_image=None):
    recipe = load(within(root, resource['recipe']))
    expected = {relative(row['path']) for row in rows}
    declared = {relative(row['path']) for row in recipe['outputs']}
    if len(expected) != len(rows) or len(declared) != len(recipe['outputs']) or expected != declared:
        raise ValueError('QDIMACS output selection differs from frozen identity')
    members = {row['source_member'].removeprefix('./'): row for row in recipe['outputs']}
    if len(members) != len(rows):
        raise ValueError('QDIMACS source member mapping is not unique')
    build = recipe['build']
    image = builder_image or acquire_official_builder(root, build, Path(downloads).parent, args)
    paths = {}
    for source in recipe['sources']:
        paths[source['id']] = (input_file(source, downloads, inputs) if (inputs or {}).get(source['id']) is not None else
                               download_official(source, downloads, build, image, args, resource_name=resource['id']))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.qbf-data-') as temporary:
        work = Path(temporary)
        (work / 'inputs').mkdir()
        (work / 'output').mkdir()
        shutil.copyfile(within(root, resource['recipe']), work / 'recipe.json')
        for path, declaration in recipe['implementation_files'].items():
            original = within(root, path)
            if digest(original) != declaration['sha256'] or PurePosixPath(declaration['destination']).name != declaration['destination']:
                raise ValueError('QDIMACS implementation identity differs')
            shutil.copyfile(original, work / declaration['destination'])
        shutil.copyfile(paths[recipe['xz_source_id']], work / 'xz-source.tar.gz')
        seen = set()
        with tarfile.open(paths[recipe['archive_source_id']], 'r|gz') as source:
            for member in source:
                name = member.name.removeprefix('./')
                if name not in members:
                    continue
                if name in seen or not member.isfile() or member.issym() or member.islnk() or member.size > 128 * 1024 * 1024:
                    raise ValueError('Selected QDIMACS source member is duplicate, oversized or special')
                declaration = members[name]
                filename = declaration['input_filename']
                if PurePosixPath(filename).name != filename:
                    raise ValueError('QDIMACS input filename must be a basename')
                with source.extractfile(member) as stream, (work / 'inputs' / filename).open('wb') as target:
                    shutil.copyfileobj(stream, target, 1024 * 1024)
                if digest(work / 'inputs' / filename) != declaration['source_sha256_plain']:
                    raise ValueError('Official QDIMACS source plaintext differs')
                seen.add(name)
        if seen != set(members):
            raise ValueError('Official QBF artifact is missing selected inputs')
        result_directory = Path(downloads).parent / (resource['id'] + '-generation')
        result_directory.mkdir(exist_ok=True)
        run_official_container(
            official_build_command(build, generation_command(recipe), output, image, args),
            int(build.get('timeout_sec', 7200)), Path(downloads).parent / 'official-container-logs',
            copy_in=[(str(work) + '/.', '/tcsexam-output')],
            copy_out=[('/tcsexam-output/output/.', output),
                      ('/tcsexam-output/generation-report.json', result_directory / 'generation-report.json')])
    return verify(output, rows)
