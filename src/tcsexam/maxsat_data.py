"""Reconstruct selected MSE input products with the original input conversion."""
import hashlib
import lzma
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from urllib.parse import urlsplit

from .layout import load, within
from .resources import (acquire_official_builder, digest, download_official, input_file,
                        official_build_command, relative, run_official_container, verify)


PLAINTEXT_CONTRACT = 'sha256-before-and-after-relabel-v1'
CANONICAL_FORMATS = ('original-v1', 'streaming-two-pass-v1')


def _sha256(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def validate_recipe(root, resource, rows):
    """Bind official inputs, conversion code and selected output identities."""
    recipe = load(within(root, resource['recipe']))
    if recipe.get('format') != 'official_maxsat_generator':
        raise ValueError('MaxSAT resource requires an official generation recipe')
    expected = {relative(row['path']): row for row in rows}
    outputs = recipe.get('outputs', [])
    declared = {relative(row['path']): row for row in outputs}
    if (not expected or len(expected) != len(rows) or len(declared) != len(outputs)
            or expected.keys() != declared.keys()):
        raise ValueError('MaxSAT output selection differs from frozen identity')
    contract = recipe.get('plaintext_contract')
    if contract is not None and contract != PLAINTEXT_CONTRACT:
        raise ValueError('Unknown MaxSAT plaintext verification contract')
    if contract is not None:
        version = recipe.get('content_version')
        if (not isinstance(version, str) or re.fullmatch('[a-z0-9][a-z0-9._-]{0,95}', version) is None
                or version != resource.get('content_version')):
            raise ValueError('MaxSAT recipe and resource content versions differ or are unsafe')
    version = recipe.get('compression_tool_version', '5.2.5')
    if version not in ('5.2.5', '5.8.4'):
        raise ValueError('Unsupported fixed MaxSAT XZ version')
    sources = recipe.get('sources', [])
    identities = [source['id'] for source in sources]
    filenames = [source['filename'] for source in sources]
    if (len(identities) != len(set(identities)) or len(filenames) != len(set(filenames))
            or recipe.get('archive_source_id') not in identities
            or recipe.get('xz_source_id') not in identities):
        raise ValueError('MaxSAT source selection must be unique and complete')
    for source in sources:
        parsed = urlsplit(source.get('url', ''))
        if (not source['filename'] or PurePosixPath(source['filename']).name != source['filename']
                or source['filename'] in ('.', '..') or '\\' in source['filename']
                or parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or not _sha256(source.get('sha256')) or type(source.get('bytes')) is not int
                or source['bytes'] <= 0):
            raise ValueError('MaxSAT sources need pinned public HTTPS inputs and safe filenames')
    destinations = []
    for path, declaration in recipe.get('implementation_files', {}).items():
        destination = declaration['destination']
        if (not destination or PurePosixPath(destination).name != destination
                or destination in ('.', '..') or '\\' in destination
                or digest(within(root, path)) != declaration['sha256']):
            raise ValueError('MaxSAT input conversion implementation identity differs')
        destinations.append(destination)
    if len(set(destinations)) != len(destinations) or 'worker.py' not in destinations:
        raise ValueError('MaxSAT conversion code destinations must be unique and include worker.py')
    members = set()
    for row in outputs:
        operation = row.get('operation')
        if operation == 'copy_pdf' and contract is None:
            if row.get('input_filename') not in filenames:
                raise ValueError('MaxSAT PDF input is not a declared official source')
            continue
        if operation not in ('maxsat_convert', 'maxsat_pack', 'maxsat_relabel'):
            raise ValueError('Unknown MaxSAT input conversion operation')
        member = relative(row['source_member'])
        if not _sha256(row.get('source_sha256_plain')):
            raise ValueError('MaxSAT source plaintext SHA-256 must be declared')
        if row.get('source_id', recipe['archive_source_id']) != recipe['archive_source_id']:
            raise ValueError('MaxSAT instance must use the declared official archive')
        if operation == 'maxsat_relabel':
            if (not _sha256(row.get('output_sha256_plain'))
                    or not isinstance(row.get('original_seed_name'), str) or not row['original_seed_name']
                    or re.fullmatch('[0-9a-f]{16}', row.get('seed_hex', '')) is None
                    or ('permutation_sha256' in row and not _sha256(row['permutation_sha256']))):
                raise ValueError('MaxSAT relabeling requires the seed and both plaintext identities')
        if contract is not None:
            if row.get('canonical_format') not in CANONICAL_FORMATS:
                raise ValueError('MaxSAT relabel contract requires a known explicit canonical format')
            if (operation != 'maxsat_relabel' or row.get('source_id') != recipe['archive_source_id']
                    or type(row.get('output_plaintext_bytes')) is not int
                    or row['output_plaintext_bytes'] <= 0
                    or any(type(row.get(field)) is not int or row[field] <= 0
                           for field in ('nvars', 'nclauses', 'top'))
                    or type(row.get('source_member_bytes')) is not int
                    or not 0 < row['source_member_bytes'] <= 8 * 1024 ** 3
                    or type(row.get('source_expanded_limit_bytes')) is not int
                    or not 0 < row['source_expanded_limit_bytes'] <= 8 * 1024 ** 3
                    or not row['path'].endswith('.wcnf.xz')):
                raise ValueError('MaxSAT relabel contract requires complete formula metadata')
            if member in members:
                raise ValueError('MaxSAT relabel source members must be unique')
            members.add(member)
        if operation in ('maxsat_pack', 'maxsat_relabel'):
            if (row.get('compression_tool_version', version) != version
                    or type(row.get('compression_preset', 6)) is not int
                    or row.get('compression_preset', 6) not in (6, 9)
                    or type(row.get('compression_threads', 1)) is not int
                    or row.get('compression_threads', 1) not in (1, 2)):
                raise ValueError('Unsupported frozen MaxSAT compression parameters')
    return recipe


def cache_identity(root, resource, rows):
    """A checked payload alone cannot certify the new official conversion route."""
    recipe = validate_recipe(root, resource, rows)
    if recipe.get('plaintext_contract') != PLAINTEXT_CONTRACT:
        return {}
    return {'maxsat_plaintext_contract': PLAINTEXT_CONTRACT,
            'maxsat_recipe_sha256': digest(within(root, resource['recipe']))}


def verify_generation_report(recipe, rows, output, report):
    """Check independent decompression of the exact bytes installed for solvers."""
    if recipe.get('plaintext_contract') != PLAINTEXT_CONTRACT:
        return
    actual_rows = load(report).get('files', [])
    actual = {relative(row['path']): row for row in actual_rows}
    expected = {relative(row['path']): row for row in rows}
    if len(actual) != len(actual_rows) or actual.keys() != expected.keys():
        raise ValueError('MaxSAT generation report selection differs')
    for declaration in recipe['outputs']:
        name = relative(declaration['path'])
        row = actual[name]
        for field in ('source_id', 'source_member', 'source_sha256_plain', 'output_sha256_plain',
                      'output_plaintext_bytes', 'seed_hex', 'nvars', 'nclauses', 'top',
                      'source_member_bytes', 'canonical_format'):
            if row.get(field) != declaration[field]:
                raise ValueError(f'MaxSAT generation report {field} differs: {name}')
        if ('permutation_sha256' in declaration
                and row.get('permutation_sha256') != declaration['permutation_sha256']):
            raise ValueError(f'MaxSAT generation report permutation_sha256 differs: {name}')
        expanded = row.get('source_expanded_bytes')
        if (type(expanded) is not int
                or not 0 < expanded <= declaration['source_expanded_limit_bytes']):
            raise ValueError(f'MaxSAT generation report expanded input size differs: {name}')
        if (row.get('bytes') != expected[name]['bytes']
                or row.get('sha256') != expected[name]['sha256']):
            raise ValueError(f'MaxSAT generation report compressed identity differs: {name}')
        h = hashlib.sha256()
        size = 0
        with lzma.open(Path(output) / name, 'rb') as stream:
            while block := stream.read(1024 * 1024):
                size += len(block)
                if size > declaration['output_plaintext_bytes']:
                    raise ValueError(f'MaxSAT expanded output exceeds declared size: {name}')
                h.update(block)
        if size != declaration['output_plaintext_bytes'] or h.hexdigest() != declaration['output_sha256_plain']:
            raise ValueError(f'MaxSAT output plaintext differs: {name}')


def generation_command(recipe=None):
    version = (recipe or {}).get('compression_tool_version', '5.2.5')
    if version not in ('5.2.5', '5.8.4'):
        raise ValueError('Unsupported fixed MaxSAT XZ version')
    return ['/bin/sh', '-eu', '-c',
            'apt-get update -qq && apt-get install -y -qq python3 build-essential ca-certificates && '
            'tar -xzf /tcsexam-output/xz-source.tar.gz -C /tmp && '
            f'cd /tmp/xz-{version} && ./configure --disable-shared --enable-static --disable-nls && make -j2 && '
            f'test "$(/tmp/xz-{version}/src/xz/xz --version | head -n1)" = "xz (XZ Utils) {version}" && '
            'cd /tcsexam-output && python3 worker.py recipe.json inputs output']


def prepare_data(root, resource, rows, output, downloads, inputs=None, args=None, builder_image=None):
    recipe = validate_recipe(root, resource, rows)
    build = recipe['build']
    image = builder_image or acquire_official_builder(root, build, Path(downloads).parent, args)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.maxsat-data-') as temporary:
        work = Path(temporary)
        (work / 'inputs').mkdir()
        (work / 'output').mkdir()
        shutil.copyfile(within(root, resource['recipe']), work / 'recipe.json')
        for path, declaration in recipe['implementation_files'].items():
            original = within(root, path)
            if digest(original) != declaration['sha256'] or PurePosixPath(declaration['destination']).name != declaration['destination']:
                raise ValueError('MaxSAT input conversion implementation identity differs')
            shutil.copyfile(original, work / declaration['destination'])
        for source in recipe['sources']:
            name = source['filename']
            if PurePosixPath(name).name != name:
                raise ValueError('MaxSAT source filename must be a basename')
            original = (input_file(source, downloads, inputs) if (inputs or {}).get(source['id']) is not None else
                        download_official(source, downloads, build, image, args, resource_name=resource['id']))
            shutil.copyfile(original, work / ('xz-source.tar.gz' if source['id'] == recipe['xz_source_id'] else 'inputs/' + name))
        report = Path(downloads).parent / (resource['id'] + '-generation')
        report.mkdir(exist_ok=True)
        run_official_container(
            official_build_command(build, generation_command(recipe), output, image, args),
            int(build.get('timeout_sec', 7200)), Path(downloads).parent / 'official-container-logs',
            copy_in=[(str(work) + '/.', '/tcsexam-output')],
            copy_out=[('/tcsexam-output/output/.', output),
                      ('/tcsexam-output/generation-report.json', report / 'generation-report.json')])
    result = verify(output, rows)
    verify_generation_report(recipe, rows, output, report / 'generation-report.json')
    return result
