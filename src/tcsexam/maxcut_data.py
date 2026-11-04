"""Download official MQLib graphs and replay the frozen vertex permutations."""
import hashlib
import csv
import io
import importlib.util
import lzma
from pathlib import Path
import zipfile

from .layout import load, within
from .resources import digest, input_file, relative, verify


def transform_raw(raw, spec, module):
    """Use the saved old-to-new permutation; never renumber a selected subset."""
    if hashlib.sha256(raw).hexdigest() != spec['sha256_orig_bytes']:
        raise ValueError('Original MQLib graph hash differs')
    n, edges = module.load_mqlib_text(raw.decode('utf-8', errors='replace'))
    perm = spec['perm']
    if len(perm) != n or sorted(perm) != list(range(1, n + 1)):
        raise ValueError('Saved MQLib permutation is not a bijection')
    data = module.canonical_bytes(n, [(perm[u - 1], perm[v - 1], w) for u, v, w in edges])
    if hashlib.sha256(data).hexdigest() != spec['sha256_new_bytes']:
        raise ValueError('Transformed MQLib graph hash differs')
    return data



def filter_repository(raw, name, recipe):
    """Retain exactly the historical public-105 background tables."""
    keep = set(recipe['public_graph_names'])
    if len(keep) != 105:
        raise ValueError('MQLib background filtering requires exactly 105 public graphs')
    if name == 'README.md':
        return recipe['readme_text'].encode()
    if name == 'instances.txt':
        names = [line.strip() for line in raw.decode().splitlines() if line.strip()]
        kept = [name for name in names if name in keep]
        if len(kept) != 105 or set(kept) != keep:
            raise ValueError('MQLib background instance list differs')
        return ('\n'.join(kept) + '\n').encode()
    zipped = name in ('results.zip', 'results_imgseg.zip')
    member = 'results.csv' if name == 'results.zip' else 'results_imgseg.csv'
    if zipped:
        with zipfile.ZipFile(io.BytesIO(raw)) as source:
            raw = source.read(member)
    source = csv.reader(io.StringIO(raw.decode()))
    header = next(source)
    text = io.StringIO()
    writer = csv.writer(text, lineterminator='\n')
    writer.writerow(header)
    index = 1 if zipped else 0
    for row in source:
        if row[index] in keep:
            writer.writerow(row)
    data = text.getvalue().encode()
    if not zipped:
        return data
    metadata = recipe['zip_metadata'][name]
    info = zipfile.ZipInfo(member, tuple(metadata['date_time']))
    for field in ('create_system', 'create_version', 'extract_version', 'flag_bits',
                  'internal_attr', 'external_attr'):
        setattr(info, field, metadata[field])
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as archive:
        archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return result.getvalue()


def prepare_data(root, resource, rows, output, downloads, inputs=None, **kwargs):
    recipe = load(within(root, resource['recipe']))
    paths = {relative(row['path']) for row in rows}
    mappings = {relative(row['path']): row for row in recipe['outputs']}
    if len(paths) != len(rows) or len(mappings) != len(recipe['outputs']) or paths != set(mappings):
        raise ValueError('MQLib recipe outputs differ from the frozen manifest')
    module, changes = None, {}
    if recipe.get('transform'):
        for field in ('transform', 'transform_manifest'):
            if digest(within(root, recipe[field])) != recipe[field + '_sha256']:
                raise ValueError('MQLib transformation identity differs')
        spec = importlib.util.spec_from_file_location('_tcsexam_mqlib_transform', within(root, recipe['transform']))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = load(within(root, recipe['transform_manifest']))
        if document['master_seed_tag'] != 'tcshard-transform-20260831':
            raise ValueError('Historical MQLib seed tag differs')
        changes = document['instances']
    sources = {source['id']: source for source in recipe['sources']}
    for row in rows:
        declaration = mappings[row['path']]
        source = sources[declaration['source_id']]
        downloaded = input_file(source, downloads, inputs)
        if declaration['kind'] == 'official_graph_zip':
            with zipfile.ZipFile(downloaded) as archive:
                members = [member for member in archive.infolist() if not member.is_dir()]
                if len(members) != 1 or members[0].flag_bits & 1:
                    raise ValueError('Official MQLib graph ZIP must contain one unencrypted graph')
                relative(members[0].filename)
                raw = archive.read(members[0])
            if declaration.get('transform_key'):
                key = declaration['transform_key']
                if module is None or key not in changes:
                    raise ValueError('MQLib output lacks its saved permutation')
                raw = transform_raw(raw, changes[key], module)
            preset = declaration['xz_preset']
            if preset not in (6, 9):
                raise ValueError('Unexpected frozen MQLib compression preset')
            data = lzma.compress(raw, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=preset)
        elif declaration['kind'] in ('official_repository_file', 'original_graph_zip', 'filtered_repository_table'):
            data = downloaded.read_bytes()
            if declaration['kind'] == 'filtered_repository_table':
                data = filter_repository(data, Path(row['path']).name, recipe)
        else:
            raise ValueError('Unknown MQLib preparation operation')
        path = Path(output) / relative(row['path'])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(int(row['mode'], 8))
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError(f'Frozen MQLib compressed or repository bytes differ: {row["path"]}')
    return verify(output, rows)
