"""Import a fixed, explicit input-only archive without claiming public access."""
from pathlib import Path, PurePosixPath
import json
import re
import shutil
import tarfile

from .layout import load, within
from .resources import content_digest, digest, input_file, relative, verify
from .solver_data_recipes import validate_payload


def prepare_data(root, resource, rows, output, downloads, inputs=None, **kwargs):
    recipe = load(within(root, resource['recipe']))
    validation_rows = rows
    if recipe['task_id'] == 'qbf-qbfeval' and recipe['data_split'] == 'hidden':
        validation_rows = []
        for row in rows:
            path = PurePosixPath(relative(row['path']))
            if (path.parts[:2] != ('opt', 'qbf-judge300') or len(path.parts) != 3
                    or not path.name.endswith('.qdimacs.xz')):
                raise ValueError('QBF fixed archive contains an undeclared data root')
            validation_rows.append(dict(row, path='tests/instances/' + path.name))
    validate_payload(validation_rows, recipe['data_split'])
    if digest(within(root, resource['files_manifest'])) != recipe['manifest_sha256']:
        raise ValueError('Fixed archive frozen manifest identity differs')
    archive = input_file(recipe['source'], downloads, inputs)
    if recipe.get('archive_format') != 'tar+gzip':
        raise ValueError('Fixed input archive must declare tar+gzip')
    expected = {relative(row['path']): row for row in rows}
    if len(expected) != len(rows) or not expected:
        raise ValueError('Fixed input archive requires a unique nonempty allowlist')
    seen = set()
    with tarfile.open(archive, 'r|gz') as source:
        for member in source:
            name = relative(member.name)
            if (name not in expected or name in seen or not member.isfile()
                    or member.issym() or member.islnk()):
                raise ValueError('Fixed input archive has an undeclared or special member')
            row = expected[name]
            if member.size != row['bytes'] or member.mode & 0o7777 != int(row['mode'], 8):
                raise ValueError('Fixed input archive member metadata differs')
            destination = Path(output) / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.extractfile(member) as inp, destination.open('wb') as out:
                shutil.copyfileobj(inp, out, 1024 * 1024)
            destination.chmod(int(row['mode'], 8))
            seen.add(name)
    if seen != set(expected):
        raise ValueError('Fixed input archive is missing declared data files')
    return verify(output, rows)


def prepare_image_context(root, resource, context, downloads, inputs=None, notices=None):
    """Create a scratch-image context after exact fixed-archive validation."""
    context = Path(context)
    context.mkdir(parents=True, exist_ok=False)
    rows = load(within(root, resource['files_manifest']))['files']
    payload = context / 'rootfs'
    payload.mkdir()
    result = prepare_data(root, resource, rows, payload, downloads, inputs=inputs)
    notice_directory = context / 'notices'
    notice_directory.mkdir()
    for name, original in (notices or {}).items():
        original = Path(original)
        if Path(name).name != name or original.is_symlink() or not original.is_file():
            raise ValueError('Fixed data notice must be a regular file with a basename')
        shutil.copyfile(original, notice_directory / name)
    recipe = load(within(root, resource['recipe']))
    (context / 'Dockerfile').write_text(
        'FROM scratch\nCOPY rootfs/ /payload/rootfs/\n'
        'COPY notices/ /licenses/tcsexam-data/\n'
        'LABEL org.tcsexam.resource=' + json.dumps(resource['id']) + '\n'
        'LABEL org.tcsexam.data-split=' + json.dumps(recipe['data_split']) + '\n')
    declaration = dict(resource_id=resource['id'], task_id=recipe['task_id'],
                       data_split=recipe['data_split'], files=result['files'],
                       bytes=result['bytes'], source=recipe['source'],
                       manifest_sha256=recipe['manifest_sha256'],
                       public_pin=None, public_upload_performed=False,
                       new_distribution_authorization=False)
    (context / 'build-declaration.json').write_text(json.dumps(declaration, indent=2) + '\n')
    return declaration


FIXED_ARCHIVE_PRODUCTS = frozenset({
    'solver-maxclique-dimacs-development-data',
    'solver-maxclique-dimacs-judging-data',
    'solver-maxsat-mse-judging-data',
    'solver-radiation-mznchallenge-judging-data',
    'qbf-judging',
})


def recipe_choices(values=None):
    """Parse only the five declared, explicitly selected archive alternatives."""
    if isinstance(values, dict):
        pairs = list(values.items())
    else:
        pairs = []
        for value in values or []:
            name, separator, option = value.partition('=')
            if not separator or not name or not option:
                raise ValueError('Use --data-recipe PRODUCT=fixed_archive')
            pairs.append((name, option))
    selected = {}
    for name, option in pairs:
        if name not in FIXED_ARCHIVE_PRODUCTS or option != 'fixed_archive':
            raise ValueError(f'Unknown declared data recipe: {name}={option}')
        if name in selected:
            raise ValueError(f'Duplicate data recipe selection: {name}')
        selected[name] = option
    return selected


def explicit_inputs(values=None):
    """Parse the existing local input interface consistently across commands."""
    result = {}
    for value in values or []:
        name, separator, path = value.partition('=')
        if not separator or not name or not path or name in result:
            raise ValueError('Use unique --input NAME=PATH values')
        result[name] = Path(path)
    return result


def effective_resource(root, resource, choices=None):
    """Return a call-local recipe overlay while retaining data and rights facts."""
    import copy
    import hashlib
    selected = recipe_choices(choices)
    if resource['id'] not in selected:
        return resource
    if resource.get('type') != 'data':
        raise ValueError('An archive alternative requires a declared data product')
    path = 'assets/data/solver/archive-import/' + resource['id'] + '-recipe.json'
    recipe = load(within(root, path))
    if recipe.get('available') is False:
        raise ValueError('Fixed archive unavailable: ' + recipe.get(
            'unavailable_reason', 'Use the default public-source data recipe.'))
    source = recipe.get('source', {})
    manifest_path = recipe.get('files_manifest', resource['files_manifest'])
    version = resource.get('content_version')
    legacy = None
    if (recipe.get('content_version', version) != version
            or recipe.get('manifest_sha256') != digest(within(root, resource['files_manifest']))):
        original = load(within(root, resource['recipe']))
        legacy = original.get('legacy_fixed_archive', {})
        if (resource['id'] != 'solver-maxsat-mse-judging-data'
                or original.get('plaintext_contract') != 'sha256-before-and-after-relabel-v1'
                or original.get('format') != 'official_maxsat_generator'
                or original.get('content_version') != resource.get('content_version')
                or legacy.get('recipe') != path
                or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,95}', legacy.get('content_version', ''))
                or recipe.get('files_manifest') != legacy.get('files_manifest')
                or recipe.get('content_version') != legacy.get('content_version')
                or recipe.get('manifest_sha256') != legacy.get('manifest_sha256')):
            raise ValueError('Declared archive alternative differs from the frozen data identity')
        manifest_path = legacy['files_manifest']
        if digest(within(root, manifest_path)) != legacy['manifest_sha256']:
            raise ValueError('Legacy MaxSAT archive manifest identity differs')
        entries = load(within(root, manifest_path))['files']
        names = validate_payload(entries, resource['data_split'])
        if names != {relative(row['path']) for row in original['outputs']}:
            raise ValueError('Legacy MaxSAT archive selection differs from the official solver inputs')
        version = legacy['content_version']
    if (recipe.get('format') != 'fixed_data_archive' or source.get('url') is not None
            or recipe.get('task_id') != resource.get('task_id')
            or recipe.get('data_split') != resource.get('data_split')
            or (recipe.get('content_version') is not None
                and recipe['content_version'] != version)
            or recipe.get('manifest_sha256') != digest(within(root, manifest_path))):
        raise ValueError('Declared archive alternative differs from the frozen data identity')
    paths = [path, manifest_path, *recipe.get('generator_paths', [])]
    if legacy is not None:
        paths.append(resource['recipe'])
    identity = {'option': 'fixed_archive', 'source': source,
                'files': {name: digest(within(root, name)) for name in paths},
                'target_root': resource['target_root']}
    signature = hashlib.sha256(json.dumps(identity, sort_keys=True,
                                           separators=(',', ':')).encode()).hexdigest()
    result = copy.deepcopy(resource)
    result['files_manifest'] = manifest_path
    if legacy is not None:
        result.update(files_manifest=manifest_path, manifest_sha256=legacy['manifest_sha256'],
                      content_version=version, content_digest=content_digest(entries, resource['target_root']),
                      files=len(entries), bytes=sum(row['bytes'] for row in entries))
    result.update(recipe=path, recipe_format='fixed_data_archive',
                  source_inputs=[source], dependencies=[],
                  acquisition={'preferred': 'local_build'},
                  selected_data_recipe='fixed_archive', data_recipe_signature=signature)
    result.pop('source_input', None)
    result.pop('source_input_file', None)
    return result


def check_explicit_input(root, resource, downloads, inputs=None):
    """Validate the exact selected archive even when a complete cache exists."""
    recipe = load(within(root, resource['recipe']))
    source = recipe['source']
    if (inputs or {}).get(source['id']) is None:
        raise ValueError(f"Resource requires explicit --input {source['id']}=PATH")
    return input_file(source, downloads, inputs)
