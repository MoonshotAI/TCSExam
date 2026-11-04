"""Rebuild development inputs from the fixed BPPLIB upstream archives."""
from collections import defaultdict
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from .layout import load, within
from .resources import input_file, rar_members


def ffd(weights, capacity):
    # A maximum segment tree finds the first bin that can fit each item.
    size = 1
    while size < len(weights):
        size *= 2
    tree = [0] * (2 * size)
    count = 0
    for weight in sorted(weights, reverse=True):
        if tree[1] < weight:
            index = size + count
            count += 1
            tree[index] = capacity
            j = index // 2
            while j:
                tree[j] = max(tree[2*j], tree[2*j+1])
                j //= 2
        index = 1
        while index < size:
            index = 2*index if tree[2*index] >= weight else 2*index+1
        tree[index] -= weight
        index //= 2
        while index:
            tree[index] = max(tree[2*index], tree[2*index+1])
            index //= 2
    return count


def bounds(path):
    ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    result = {}
    with zipfile.ZipFile(path) as archive:
        strings = [''.join(s.itertext()) for s in
                   ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('x:si', ns)]
        for name in archive.namelist():
            if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml', name):
                continue
            for row in ET.fromstring(archive.read(name)).findall('x:sheetData/x:row', ns)[1:]:
                cells = {}
                for cell in row.findall('x:c', ns):
                    value = cell.find('x:v', ns)
                    if value is not None:
                        cells[re.sub(r'\d', '', cell.attrib['r'])] = (
                            strings[int(value.text)] if cell.attrib.get('t') == 's' else value.text)
                if cells.get('A') and cells.get('B', '').isdigit() and cells.get('C', '').isdigit():
                    value = (int(cells['B']), int(cells['C']))
                    if cells['A'] in result and result[cells['A']] != value:
                        raise ValueError('Conflicting official bounds')
                    result[cells['A']] = value
    return result


def packing(original, csp, log):
    values = list(map(int, original.split()))
    n, capacity, weights = values[0], values[1], values[2:]
    tokens = list(map(int, csp.split()))
    m, csp_capacity = tokens[:2]
    if len(weights) != n or len(tokens) != 2 + 2*m or capacity != csp_capacity:
        raise ValueError('Invalid original or cutting-stock input')
    types = list(zip(tokens[2::2], tokens[3::2]))
    expanded, starts = [], []
    for weight, demand in types:
        if weight <= 0 or demand <= 0:
            raise ValueError('Invalid weight or demand')
        starts.append(len(expanded))
        expanded.extend([weight] * demand)
    if sorted(weights) != sorted(expanded):
        raise ValueError('BPP/CSP weights differ')
    if 'Solution:' not in log.decode():
        raise ValueError('No official solution')
    used, bins, count = [0]*m, [0]*n, 0
    for line in log.decode().rsplit('Solution:', 1)[1].strip().splitlines():
        match = re.fullmatch(r'(\d+) x \[(.*)\]', line.strip())
        if not match:
            raise ValueError('Invalid packing pattern')
        indices = [int(x)-1 for x in re.findall(r'i=(\d+)', match[2])]
        if not indices or any(i < 0 or i >= m for i in indices):
            raise ValueError('Invalid packing type')
        for _ in range(int(match[1])):
            count += 1
            for i in indices:
                if used[i] >= types[i][1]:
                    raise ValueError('Packing exceeds demand')
                bins[starts[i]+used[i]] = count
                used[i] += 1
    if used != [d for _, d in types]:
        raise ValueError('Packing does not cover all items')
    by_weight, offsets, loads = defaultdict(list), defaultdict(int), defaultdict(int)
    for weight, bin_id in zip(expanded, bins):
        by_weight[weight].append(bin_id)
    assigned = []
    for weight in weights:
        bin_id = by_weight[weight][offsets[weight]]
        offsets[weight] += 1
        assigned.append(bin_id)
        loads[bin_id] += weight
    if any(x > capacity for x in loads.values()):
        raise ValueError('Packing exceeds capacity')
    return (str(count)+'\n'+' '.join(map(str, assigned))+'\n').encode()


def prepare(root, bundle, rows, output, downloads, inputs=None):
    recipe = load(within(root, bundle['recipe']))
    supplied = inputs
    inputs = {}
    for source in recipe['sources']:
        archive = input_file(source, downloads, supplied)
        if source['id'] == 'Solutions.xlsx':
            inputs[source['id']] = archive
        else:
            for member, data in rar_members(archive):
                key = source['id'] + '/' + member
                if key in inputs:
                    raise ValueError('Duplicate upstream member')
                inputs[key] = data
    for row in rows:
        if row.get('source_member'):
            data = inputs[row['source_member']]
        elif row.get('packing'):
            spec = row['packing']
            data = packing(inputs[spec['original']], inputs[spec['csp']], inputs[spec['log']])
        elif row['path'] == 'bpplib_table.md':
            official_bounds = bounds(inputs['Solutions.xlsx'])
            lines = recipe['table_intro'].copy()
            groups = defaultdict(list)
            for entry in rows:
                if 'category' in entry:
                    groups[entry['category']].append(entry)
            for category, entries in sorted(groups.items()):
                lines.extend([f"## Class {category} ({recipe['table_headings'][category]} instances)", '',
                              '| instance | n | capacity | best | ffd | gap |',
                              '|---|---|---|---|---|---|'])
                for entry in sorted(entries, key=lambda r: Path(r['path']).name):
                    name = Path(entry['path']).name
                    values = list(map(int, inputs[entry['source_member']].split()))
                    n, capacity, weights = values[0], values[1], values[2:]
                    lower, upper = official_bounds[name]
                    best = str(upper) if lower == upper else f'{lower}..{upper}'
                    baseline = ffd(weights, capacity)
                    # Compare with the known feasible packing, not the unknown
                    # optimum when lower < upper. Preserve the two trailing
                    # spaces inside the cell: the original table is hash-pinned.
                    lines.append(f'| {name} | {n} | {capacity} | {best} | {baseline} | {baseline-upper}  |')
                lines.append('')
            data = '\n'.join(lines).encode()
        else:
            raise ValueError(f"Missing preparation rule: {row['path']}")
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError(f"Reconstructed bytes differ: {row['path']}")
        path = output / row['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(int(row['mode'], 8))


def validate_packing(original, data, expected_bins=None):
    values = list(map(int, original.split()))
    if len(values) < 2:
        raise ValueError('Invalid original input')
    n, capacity, weights = values[0], values[1], values[2:]
    tokens = data.split()
    if len(weights) != n or len(tokens) != n + 1:
        raise ValueError('Packing does not cover all items')
    count = int(tokens[0])
    bins = list(map(int, tokens[1:]))
    if (count <= 0 or any(bin_id < 1 or bin_id > count for bin_id in bins) or
            len(set(bins)) != count):
        raise ValueError('Invalid packing bin count')
    if expected_bins is not None and count != expected_bins:
        raise ValueError('Packing bin count differs')
    loads = defaultdict(int)
    for weight, bin_id in zip(weights, bins):
        loads[bin_id] += weight
    if any(load > capacity for load in loads.values()):
        raise ValueError('Packing exceeds capacity')
    return count, bins


def original_source(csp):
    source = csp.split('/', 1)[0]
    for suffix in ('_CSP', ' CSP'):
        if source.endswith(suffix):
            return source[:-len(suffix)]
    raise ValueError(f'Cannot locate original archive for {csp}')


def load_transform(root, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('_tcsexam_bpplib_transform', within(root, path))
    if spec is None or spec.loader is None:
        raise ValueError('Cannot load BPPLIB transform')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def judging_inputs(sources, packings, downloads, inputs):
    required = {spec[key] for spec in packings for key in ('csp', 'log')}
    original_names = defaultdict(set)
    for spec in packings:
        original_names[original_source(spec['csp'])].add(Path(spec['csp']).name)
    source_ids = set(original_names) | {key.split('/', 1)[0] for key in required}
    members, originals = {}, {}
    for source in sources:
        if source['id'] not in source_ids:
            continue
        archive = input_file(source, downloads, inputs)
        for member, data in rar_members(archive):
            key = source['id'] + '/' + member
            name = Path(member).name
            original_key = (source['id'], name)
            wanted_original = source['id'] in original_names and name in original_names[source['id']]
            if key not in required and not wanted_original:
                continue
            if key in members or (wanted_original and original_key in originals):
                raise ValueError('Duplicate upstream member')
            members[key] = data
            if wanted_original:
                originals[original_key] = key
    missing = required - set(members)
    missing.update(f'{source}/*/{name}' for source, names in original_names.items()
                   for name in names if (source, name) not in originals)
    if missing:
        raise ValueError(f'Missing official source members: {sorted(missing)[:5]}')
    original_keys = {spec['csp']: originals[(original_source(spec['csp']), Path(spec['csp']).name)]
                     for spec in packings}
    return members, original_keys


def prepare_judging(root, bundle, rows, output, downloads, inputs=None):
    from .resources import relative, verify
    recipe = load(within(root, bundle['recipe']))
    source_recipe = load(within(root, recipe['source_recipe']))
    reconstruction = load(within(root, recipe['reconstruction']))
    original_specs = reconstruction['original_packings']
    transformed_specs = reconstruction['transformed']
    if len(original_specs) != reconstruction['byte_identical_original_packings']:
        raise ValueError('Original packing count differs')
    if (len(transformed_specs) != reconstruction['byte_identical_transformed_instances_and_packings'] or
            len(rows) != len(transformed_specs)):
        raise ValueError('Transformed instance count differs')
    if len({spec['csp'] for spec in original_specs}) != len(original_specs):
        raise ValueError('Duplicate original packing')
    expected_paths = {'tests/instances/' + spec['code']: spec for spec in transformed_specs}
    output_rows = {row['path']: row for row in rows}
    if len(expected_paths) != len(transformed_specs) or len(output_rows) != len(rows):
        raise ValueError('Duplicate transformed output')
    if set(expected_paths) != set(output_rows):
        raise ValueError('Judging manifest does not match reconstruction')
    for path, spec in expected_paths.items():
        if output_rows[path]['sha256'] != spec['instance_sha256']:
            raise ValueError(f'Judging manifest hash differs: {path}')
    transform = load_transform(root, recipe['transform'])
    members, original_keys = judging_inputs(source_recipe['sources'], original_specs, downloads, inputs)
    packings = {}
    for spec in original_specs:
        original = members[original_keys[spec['csp']]]
        data = packing(original, members[spec['csp']], members[spec['log']])
        count, bins = validate_packing(original, data, spec['bins'])
        if hashlib.sha256(data).hexdigest() != spec['sha256']:
            raise ValueError(f"Original packing bytes differ: {spec['path']}")
        packings[Path(spec['csp']).name] = (original, count, bins)
    generated = {}
    for spec in transformed_specs:
        name = spec['official']
        if name not in packings:
            raise ValueError(f'Missing original packing: {name}')
        original, count, bins = packings[name]
        values = list(map(int, original.split()))
        n, capacity, weights = values[0], values[1], values[2:]
        transformed, perm = transform.transform_instance(name, n, weights)
        instance = transform.serialize(n, capacity, transformed)
        transformed_bins = transform.rewrite_packing(bins, perm)
        transformed_packing = (str(count) + '\n' + ' '.join(map(str, transformed_bins)) + '\n').encode()
        validate_packing(instance, transformed_packing, count)
        if hashlib.sha256(instance).hexdigest() != spec['instance_sha256']:
            raise ValueError(f"Transformed instance bytes differ: {spec['code']}")
        if hashlib.sha256(transformed_packing).hexdigest() != spec['packing_sha256']:
            raise ValueError(f"Transformed packing bytes differ: {spec['code']}")
        generated['tests/instances/' + spec['code']] = instance
    output = Path(output)
    for row in rows:
        path = output / relative(row['path'])
        data = generated[row['path']]
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError(f"Reconstructed bytes differ: {row['path']}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(int(row['mode'], 8))
    verify(output, rows)
