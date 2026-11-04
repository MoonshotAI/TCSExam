"""Prepare explicit frozen outputs from fixed official per-file downloads."""
import importlib.util
import lzma
from pathlib import Path
import shutil
import tarfile
import tempfile

from .layout import load, within
from .resources import digest, input_file, relative, verify


def prepare_data(root, resource, rows, output, downloads, inputs=None, **kwargs):
    recipe = load(within(root, resource['recipe']))
    expected = {relative(row['path']): row for row in rows}
    outputs = {relative(row['path']): row for row in recipe['outputs']}
    if len(expected) != len(rows) or len(outputs) != len(recipe['outputs']) or set(expected) != set(outputs):
        raise ValueError('Official-file selection differs from the frozen manifest')
    sources = {source['id']: source for source in recipe['sources']}
    transform = None
    if recipe.get('transform'):
        if digest(within(root, recipe['transform'])) != recipe['transform_sha256']:
            raise ValueError('Official-file transformation identity differs')
        spec = importlib.util.spec_from_file_location('_tcsexam_file_transform', within(root, recipe['transform']))
        transform = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transform)
    mr_pairs = {}
    for path, declaration in outputs.items():
        source = (None if declaration['operation'] == 'jssp_generate' else
                  within(root, declaration['source_path']) if declaration['operation'] == 'project_file'
                  else input_file(sources[declaration['source_id']], downloads, inputs))
        destination = Path(output) / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if declaration['operation'] in ('copy', 'project_file'):
            shutil.copyfile(source, destination)
        elif declaration['operation'] == 'dimacs_binary':
            from .dimacs_binary_data import convert
            convert(source, destination)
        elif declaration['operation'] == 'xz_file':
            with lzma.open(source, 'rb') as inp, destination.open('wb') as out:
                remaining = expected[path]['bytes']
                while block := inp.read(min(1024 * 1024, remaining + 1)):
                    remaining -= len(block)
                    if remaining < 0:
                        raise ValueError('Official xz instance exceeds frozen byte size')
                    out.write(block)
        elif declaration['operation'] == 'tar_single_file':
            seen = False
            with tarfile.open(source, 'r|xz') as archive:
                for member in archive:
                    relative(member.name)
                    if member.isdir():
                        continue
                    if seen or not member.isfile() or member.issym() or member.islnk():
                        raise ValueError('Official input archive must contain exactly one regular file')
                    if member.size != expected[path]['bytes']:
                        raise ValueError('Official archived instance byte size differs')
                    with archive.extractfile(member) as inp, destination.open('wb') as out:
                        shutil.copyfileobj(inp, out, 1024 * 1024)
                    seen = True
            if not seen:
                raise ValueError('Official input archive contains no instance')
        elif declaration['operation'] == 'curriculum_relabel':
            if transform is None:
                raise ValueError('Curriculum relabeling implementation is missing')
            instance, maps = transform.transform_instance(declaration['official_stem'], transform.load_ctt(source))
            if maps != declaration['maps']:
                raise ValueError('Frozen curriculum label mappings differ')
            destination.write_bytes(transform.emit(instance))
        elif declaration['operation'] == 'itc_team_relabel':
            if transform is None:
                raise ValueError('Sports timetable relabeling implementation is missing')
            perm = declaration['perm']
            if sorted(perm) != list(range(len(perm))):
                raise ValueError('Frozen team mapping is not a permutation')
            text = transform.transform_text(source.read_text(), perm, declaration['neutral_instance_name'])
            destination.write_text(text)
        elif declaration['operation'] == 'logic_npn':
            if transform is None:
                raise ValueError('Truth-table transformation implementation is missing')
            n, masks = transform.parse_truth(source.read_text())
            parameters = declaration['parameters']
            m = len(masks)
            if (n != parameters['n'] or m != parameters['m']
                    or sorted(parameters['in_perm']) != list(range(n))
                    or sorted(parameters['out_perm']) != list(range(m))
                    or len(parameters['in_neg']) != n or len(parameters['out_neg']) != m
                    or any(v not in (0, 1) for v in parameters['in_neg'] + parameters['out_neg'])):
                raise ValueError('Frozen truth-table transformation dimensions differ')
            masks = transform.npn_transform_truth(n, masks, parameters['in_perm'],
                                                  parameters['in_neg'], parameters['out_perm'],
                                                  parameters['out_neg'])
            destination.write_text(transform.write_truth(n, masks))
        elif declaration['operation'] == 'tsp_relabel':
            if transform is None:
                raise ValueError('TSPLIB serialization implementation is missing')
            instance = transform.parse_instance(source)
            permutation = declaration['old_of_new']
            if sorted(permutation) != list(range(1, instance['n'] + 1)):
                raise ValueError('Frozen city mapping is not a permutation')
            if digest(source) != declaration['original_sha256']:
                raise ValueError('Frozen original TSPLIB source differs')
            destination.write_bytes(transform.emit_instance(instance, permutation))
        elif declaration['operation'] == 'cvrp_relabel':
            if transform is None:
                raise ValueError('CVRPLIB relabeling implementation is missing')
            instance = transform.parse_vrp(source)
            changed, permutation = transform.transform_instance(declaration['official_name'], instance)
            if transform.params_hash(permutation, instance['depot'], changed['depot']) != declaration['transform_params_sha256']:
                raise ValueError('CVRPLIB frozen transformation parameters differ')
            changed['header']['NAME'] = declaration['neutral_name']
            destination.write_bytes(transform.serialize(changed, comment=transform.NEUTRAL_COMMENT))
        elif declaration['operation'] in ('dimacs_relabel', 'dimacs_binary_relabel'):
            if transform is None:
                raise ValueError('DIMACS parser and serializer are missing')
            with tempfile.TemporaryDirectory(prefix='tcsexam-dimacs-') as temporary:
                canonical = source
                if declaration['operation'] == 'dimacs_binary_relabel':
                    from .dimacs_binary_data import convert
                    canonical = Path(temporary) / 'original.clq'
                    convert(source, canonical)
                n, edges = transform.parse_dimacs_text(canonical.read_text(errors='replace'))
            permutation = declaration['perm']
            if (n != declaration['n'] or len(edges) != declaration['m']
                    or sorted(permutation) != list(range(1, n + 1))):
                raise ValueError('Frozen DIMACS dimensions or permutation differ')
            changed = {tuple(sorted((permutation[u - 1], permutation[v - 1]))) for u, v in edges}
            destination.write_text(transform.canonical_text(n, changed))
        elif declaration['operation'] == 'sygus_convert':
            if transform is None:
                raise ValueError('Original SyGuS input conversion is missing')
            transform.convert(str(source), str(destination))
        elif declaration['operation'] == 'mr_relabel':
            if transform is None:
                raise ValueError('Original machine-reassignment input transformation is missing')
            key = declaration['parameter_key']
            if key not in mr_pairs:
                parameters = recipe['transform_parameters'][key]
                with tempfile.TemporaryDirectory(prefix='tcsexam-mr-') as temporary:
                    temporary = Path(temporary)
                    for component in ('model', 'assignment'):
                        original = input_file(sources[parameters[component + '_source_id']], downloads, inputs)
                        shutil.copyfile(original, temporary / (component + '_' + key + '.txt'))
                    model, assignment, orders, seed = transform.transform_instance(
                        key, str(temporary), parameters['orders'])
                    if seed != parameters['seed_hex']:
                        raise ValueError('Original machine-reassignment seed label differs')
                    mr_pairs[key] = {'model': model.encode(), 'assignment': assignment.encode(), 'remaining': 2}
            destination.write_bytes(mr_pairs[key][declaration['component']])
            mr_pairs[key]['remaining'] -= 1
            if mr_pairs[key]['remaining'] == 0:
                del mr_pairs[key]
        elif declaration['operation'] in ('calma_convert', 'calma_relabel'):
            if transform is None:
                raise ValueError('CALMA converter and transformation are missing')
            members = {relative(r['member']): r['basename'] for r in declaration['members']}
            if (len(members) != 4 or {name.lower() for name in members.values()}
                    != {'var.txt', 'dom.txt', 'ctr.txt', 'cst.txt'}):
                raise ValueError('CALMA source must select exactly four input text files')
            with tempfile.TemporaryDirectory(prefix='tcsexam-calma-') as temporary:
                temporary = Path(temporary)
                selected = set()
                with tarfile.open(source, 'r|gz') as archive:
                    for member in archive:
                        name = relative(member.name)
                        if name not in members:
                            continue
                        if name in selected or not member.isfile():
                            raise ValueError('CALMA source member is duplicate or non-regular')
                        selected.add(name)
                        with archive.extractfile(member) as inp, (temporary / members[name]).open('wb') as out:
                            shutil.copyfileobj(inp, out, 1024 * 1024)
                if selected != set(members):
                    raise ValueError('CALMA archive is missing selected source files')
                original = temporary / 'original.dzn'
                transform.convert(str(temporary), str(original))
                if digest(original) != declaration['original_dzn_sha256']:
                    raise ValueError('CALMA original DZN conversion differs')
                if declaration['operation'] == 'calma_convert':
                    shutil.copyfile(original, destination)
                else:
                    changed, variables, hard, soft = transform.transform_instance(
                        declaration['official_stem'], transform.load_dzn(original))
                    if (variables[1:] != declaration['var_permutation_new_from_old']
                            or hard != declaration['hard_order_new_from_old']
                            or soft != declaration['soft_order_new_from_old']):
                        raise ValueError('CALMA saved transformation parameters differ')
                    destination.write_bytes(transform.serialize(changed))
        elif declaration['operation'] == 'qap_relabel':
            if transform is None:
                raise ValueError('QAP relabeling implementation is missing')
            n, flow, distances = transform.parse_dat(source)
            flow, distances, facilities, locations = transform.transform_instance(
                declaration['official_name'], n, flow, distances)
            if transform.params_hash(facilities, locations) != declaration['transform_params_sha256']:
                raise ValueError('QAP frozen transformation parameters differ')
            destination.write_bytes(transform.serialize(n, flow, distances))
        elif declaration['operation'] in ('scp_rail', 'scp_relabel'):
            from .scp_data import normalize_rail
            with tempfile.TemporaryDirectory(prefix='tcsexam-scp-') as temporary:
                canonical = source
                if declaration.get('rail'):
                    canonical = Path(temporary) / 'canonical.txt'
                    normalize_rail(source, canonical, declaration.get('compressed', False))
                if declaration['operation'] == 'scp_rail':
                    shutil.copyfile(canonical, destination)
                else:
                    if transform is None:
                        raise ValueError('SCP relabeling implementation is missing')
                    m, n, costs, matrix = transform.load_instance(canonical)
                    costs, matrix, columns, row_order = transform.transform_instance(
                        declaration['official_stem'], m, n, costs, matrix,
                        suffix=declaration['seed_suffix'])
                    if transform.params_hash(columns, row_order) != declaration['transform_params_sha256']:
                        raise ValueError('SCP frozen transformation parameters differ')
                    destination.write_bytes(transform.serialize(m, n, costs, matrix))
        elif declaration['operation'] in ('jssp_relabel', 'jssp_generate', 'jssp_json'):
            if transform is None:
                raise ValueError('Job-shop input transformation is missing')
            with tempfile.TemporaryDirectory(prefix='tcsexam-jssp-') as temporary:
                canonical = source
                if declaration['operation'] == 'jssp_generate':
                    canonical = Path(temporary) / 'generated.txt'
                    transform.generate_instance(['gen_jssp.py', declaration['family'],
                                                 declaration['jobs'], declaration['machines'],
                                                 declaration['seed'], str(canonical)])
                elif declaration.get('source_format') == 'json':
                    data = load(source)
                    n, m = data['jobs'], data['machines']
                    operations = [[None for _ in range(m)] for _ in range(n)]
                    for operation in data['data']:
                        job, index = operation['job'], operation['operation']
                        if not (0 <= job < n and 0 <= index < m) or operations[job][index] is not None:
                            raise ValueError('Job-shop JSON repeats an operation or has an invalid index')
                        machine, duration = operation['machine'], operation['duration']
                        if not (0 <= machine < m and duration >= 0):
                            raise ValueError('Job-shop JSON has an invalid machine or duration')
                        operations[job][index] = (machine, duration)
                    if any(operation is None for row in operations for operation in row):
                        raise ValueError('Job-shop JSON is missing an operation')
                    canonical = Path(temporary) / 'canonical.txt'
                    canonical.write_bytes(transform.serialize(n, m, operations))
                if declaration.get('relabel'):
                    n, m, operations = transform.parse_instance(canonical)
                    operations, jobs, machines = transform.transform_instance(
                        declaration['official_stem'], n, m, operations)
                    if transform.params_hash(jobs, machines) != declaration['transform_params_sha256']:
                        raise ValueError('Job-shop frozen transformation parameters differ')
                    destination.write_bytes(transform.serialize(n, m, operations))
                else:
                    shutil.copyfile(canonical, destination)
        else:
            raise ValueError(f'Unknown official-file operation: {declaration["operation"]}')
        destination.chmod(int(expected[path]['mode'], 8))
        if destination.stat().st_size != expected[path]['bytes'] or digest(destination) != expected[path]['sha256']:
            raise ValueError(f'Official-file reconstructed bytes differ: {path}')
    return verify(output, rows)
