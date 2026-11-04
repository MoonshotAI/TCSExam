"""Prepare adopted judging graphs using their fixed vertex permutations."""
from pathlib import Path
import os
import json
import shutil
import tempfile

from .layout import load, within
from .resources import (acquire_official_builder, digest, download_official, input_file,
                        official_build_command, run_official_container, verify)

TRANSFORMS = {'dfvs-pace2022': ('official_dfvs_xz', 'vertex-relabeling-v1', 200),
              'oscm-pace2024': ('official_archive', 'free-layer-relabeling-v1', 100)}
WORKER = 'assets/data/solver/graph-relabel/worker.py'


def validate_recipe(root, resource, rows, recipe):
    policy = recipe.get('graph_transform', {})
    task = policy.get('task_id')
    if task not in TRANSFORMS:
        raise ValueError('Unsupported transformed graph task')
    format_, transform, count = TRANSFORMS[task]
    if (resource['id'] != f'solver-{task}-judging-data' or recipe.get('format') != format_
            or policy.get('id') != transform or policy.get('seed_tag') != 'tcshard-transform-20260831'
            or policy.get('implementation_path') != WORKER
            or digest(within(root, WORKER)) != policy.get('implementation_sha256')):
        raise ValueError('Graph transform identity, implementation or hidden-data product differs')
    if task == 'dfvs-pace2022' and recipe.get('compression') != {
            'format': 'xz', 'tool': 'python-lzma', 'liblzma_version': '5.2.5',
            'preset': 6, 'check': 'crc64', 'threads': 1}:
        raise ValueError('DFVS judging compression must use its adopted single-thread settings')
    expected_paths = ({f'tests/instances/e_{n:03d}.xz' for n in range(1, 201)}
                      if task == 'dfvs-pace2022' else
                      {f'tests/instances/{n}.gr' for n in range(101, 201)})
    output_rows = recipe.get('outputs', [])
    declared = {row['path']: row for row in output_rows}
    manifest = {row['path']: row for row in rows}
    if len(rows) != count or len(output_rows) != count or set(declared) != expected_paths or set(manifest) != expected_paths:
        raise ValueError('Transformed graph manifest must contain the complete judging selection')
    for path, row in declared.items():
        if any(row.get(k) != manifest[path].get(k) for k in ('bytes', 'sha256', 'mode')) or row['mode'] != '0644':
            raise ValueError('Transformed graph declaration differs from the file manifest')
        expected_member = ('exact_track_final_instances_all/' + Path(path).stem
                           if task == 'dfvs-pace2022' else Path(path).name)
        if row.get('source_member') != expected_member:
            raise ValueError('Transformed graph source-member mapping differs')
        contract = row.get('transform_contract', {})
        required = {'n', 'm', 'seed_hex', 'sha256_orig_tokens', 'sha256_new_tokens', 'output_sha256_plain'} if task == 'dfvs-pace2022' else {'n1', 'n2', 'm', 'seed_hex', 'sha256_orig_tokens', 'sha256_new_tokens', 'output_sha256_plain'}
        if not required <= set(contract):
            raise ValueError('Transformed graph contract lacks original dimensions, seed or hashes')
    return policy



def verify_generation_report(recipe, report):
    policy = recipe['graph_transform']
    if any(report.get(key) != policy[lookup] for key, lookup in
           [('task_id', 'task_id'), ('transform_id', 'id'), ('seed_tag', 'seed_tag')]):
        raise ValueError('Graph generation report identity differs')
    expected = {row['path']: row for row in recipe['outputs']}
    actual = {row['path']: row for row in report.get('files', [])}
    if len(actual) != len(report.get('files', [])) or set(actual) != set(expected):
        raise ValueError('Graph generation report omits or repeats judging files')
    for path, row in expected.items():
        contract = dict(row['transform_contract'], bytes=row['bytes'], sha256=row['sha256'])
        if any(actual[path].get(key) != value for key, value in contract.items()):
            raise ValueError('Graph generation report differs from the original transformation contract')
    return report


def prepare_data(root, resource, rows, output, downloads, inputs=None, args=None, builder_image=None):
    recipe = load(within(root, resource['recipe']))
    validate_recipe(root, resource, rows, recipe)
    build = recipe['build']
    image = builder_image or acquire_official_builder(root, build, Path(downloads).parent, args)
    source = recipe['source']
    archive = (input_file(source, downloads, inputs) if (inputs or {}).get(source['id']) is not None
               else download_official(source, downloads, build, image, args, resource_name=resource['id']))
    output = Path(output)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.graph-transform-') as folder:
        work = Path(folder)
        shutil.copyfile(archive, work / 'source.archive')
        shutil.copyfile(within(root, WORKER), work / 'worker.py')
        (work / 'recipe.json').write_text(json.dumps(recipe))
        command = ['/bin/sh', '-eu', '-c',
                   'apt-get -o Acquire::Retries=2 update && '
                   'apt-get -o Acquire::Retries=2 install -y --no-install-recommends python3 && '
                   'python3 worker.py recipe.json source.archive output generation-report.json']
        run_official_container(
            official_build_command(build, command, output, image, args,
                                   name='tcsexam-official-graph-' + os.urandom(16).hex()),
            int(build['timeout_sec']), Path(downloads).parent / 'official-container-logs',
            copy_in=[(str(work) + '/.', '/tcsexam-output')],
            copy_out=[('/tcsexam-output/output/.', output),
                      ('/tcsexam-output/generation-report.json', work / 'generation-report.json')])
        report = verify_generation_report(recipe, load(work / 'generation-report.json'))
        reports = Path(downloads).parent / 'graph-transform-reports'
        reports.mkdir(parents=True, exist_ok=True)
        (reports / (resource['id'] + '-' + digest(within(root, resource['recipe'])) + '.json')).write_text(
            json.dumps(report, indent=2) + '\n')
    return verify(output, rows)
