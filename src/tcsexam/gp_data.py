"""Reconstruct exact DIMACS10 graph products with the original generators."""
from pathlib import Path, PurePosixPath
import shutil
import tempfile

from .layout import load, within
from .resources import (acquire_official_builder, digest, download_official, input_file,
                        official_build_command, relative, run_official_container, verify)


def generation_command():
    return ['/bin/sh', '-eu', '-c',
            'apt-get update -qq && apt-get install -y -qq python3 python3-pip g++ ca-certificates && '
            'cd /tcsexam-output && '
            'python3 -m pip install --no-index --no-deps wheels/*.whl && '
            'python3 worker.py recipe.json inputs output']


def prepare_data(root, resource, rows, output, downloads, inputs=None, args=None, builder_image=None):
    recipe = load(within(root, resource['recipe']))
    expected = {relative(row['path']) for row in rows}
    declared = {relative(row['path']) for row in recipe['outputs']}
    if len(expected) != len(rows) or len(declared) != len(recipe['outputs']) or expected != declared:
        raise ValueError('Graph output allowlist differs from the frozen product')
    build = recipe['build']
    image = builder_image or acquire_official_builder(root, build, Path(downloads).parent, args)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.gp-data-') as temporary:
        work = Path(temporary)
        for name in ['inputs', 'wheels', 'output']:
            (work / name).mkdir()
        shutil.copyfile(within(root, resource['recipe']), work / 'recipe.json')
        for source_path, declaration in recipe['implementation_files'].items():
            path = within(root, source_path)
            if digest(path) != declaration['sha256'] or PurePosixPath(declaration['destination']).name != declaration['destination']:
                raise ValueError('Graph generation implementation identity differs')
            shutil.copyfile(path, work / declaration['destination'])
        for source in recipe['sources']:
            supplied = (inputs or {}).get(source['id'])
            original = (input_file(source, downloads, inputs) if supplied is not None else
                        download_official(source, downloads, build, image, args, resource_name=resource['id']))
            name = source.get('filename', source['id'])
            if PurePosixPath(name).name != name:
                raise ValueError('Graph source filename is not a basename')
            shutil.copyfile(original, work / ('wheels' if source['role'] == 'python_wheel' else 'inputs') / name)
        results = Path(downloads).parent / (resource['id'] + '-generation')
        results.mkdir(exist_ok=True)
        run_official_container(
            official_build_command(build, generation_command(), output, image, args),
            int(build.get('timeout_sec', 3600)), Path(downloads).parent / 'official-container-logs',
            copy_in=[(str(work) + '/.', '/tcsexam-output')],
            copy_out=[('/tcsexam-output/output/.', output),
                      ('/tcsexam-output/generation-report.json', results / 'generation-report.json')])
    return verify(output, rows)
