import copy
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from tcsexam.atcoder_data import extract_inputs, selection

ROOT = Path(__file__).resolve().parents[3]


def recipe(task, split):
    return json.loads((ROOT / 'assets/data/solver' /
                       f'solver-{task}-{split}-data-recipe.json').read_text())


def test_ahc041_retains_all_105_public_inputs_and_exact_generated_split():
    data = recipe('christmas-tree-ahc041', 'development')
    rows = json.loads((ROOT / 'assets/data/solver/'
                       'solver-christmas-tree-ahc041-development-data-files.json').read_text())['files']
    _, outputs = selection(rows, data)
    official = {r['source_member'] for r in outputs.values() if 'source_member' in r}
    assert official == {f'tools/in/{n:04d}.txt' for n in range(100)}
    generated = {Path(path).name: r['seed'] for path, r in outputs.items() if 'seed' in r}
    assert len(generated) == 5
    hidden = recipe('christmas-tree-ahc041', 'judging')['outputs']
    assert len(hidden) == 45
    assert len({r['seed'] for r in hidden}) == 45
    assert not set(generated.values()) & {r['seed'] for r in hidden}
    mapping = json.loads((ROOT / 'assets/data/solver/christmas-tree-ahc041/transform-manifest.json').read_text())['instances']
    assert {f'h{n:02d}.txt' for n in range(50)} == set(generated) | {mapping[r['transform_key']]['official'] + '.txt' for r in hidden}


def test_selection_rejects_missing_paths_and_duplicate_seeds():
    rows = [{'path': 'tests/instances/a.txt'}, {'path': 'tests/instances/b.txt'}]
    data = {'outputs': [{'path': r['path'], 'seed': 1234 + n} for n, r in enumerate(rows)]}
    selection(rows, data)
    corrupt = copy.deepcopy(data)
    corrupt['outputs'][1]['seed'] = 1234
    with pytest.raises(ValueError, match='duplicate'):
        selection(rows, corrupt)
    corrupt = copy.deepcopy(data)
    corrupt['outputs'][1]['path'] = 'tests/instances/c.txt'
    with pytest.raises(ValueError, match='paths'):
        selection(rows, corrupt)
    corrupt = copy.deepcopy(data)
    corrupt['outputs'][0]['source_member'] = '../outside'
    with pytest.raises(ValueError, match='one source'):
        selection(rows, corrupt)


def test_archive_extracts_only_checked_generator_and_selected_instances(tmp_path):
    payload = b'dummy checked data\n'
    checked = lambda path: {'path': path, 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}
    names = ['tools/Cargo.toml', 'tools/Cargo.lock', 'tools/src/bin/gen.rs', 'tools/src/lib.rs']
    data = {'generator_files': [checked(path) for path in names],
            'calibration_files': [checked(f'tools/in/{n:04d}.txt') for n in range(100)],
            'outputs': [{'path': 'app/instances/0000.txt', 'source_member': 'tools/in/0000.txt'}]}
    rows = [dict(checked('app/instances/0000.txt'), mode='0644')]
    archive = tmp_path / 'tools.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        for row in data['generator_files'] + data['calibration_files']:
            z.writestr(row['path'], payload)
        z.writestr('tools/private-answer.txt', b'never extract this')
    output = tmp_path / 'out'
    work = tmp_path / 'work'
    extract_inputs(archive, work, output, rows, data)
    assert (output / rows[0]['path']).read_bytes() == payload
    assert not (work / 'tools/private-answer.txt').exists()
    data['generator_files'][0]['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='hash'):
        extract_inputs(archive, tmp_path / 'work2', tmp_path / 'out2', rows, data)


def test_all_solver_pairs_keep_existing_ids_and_both_consumers():
    from tcsexam.solver_data_recipes import product_patch, data_pairs
    pairs = data_pairs(ROOT)
    assert len(pairs) == 30
    assert next(p for p in pairs if p['task_id'] == 'bpp-bpplib')['hidden'] == 'bpplib-judging'
    assert next(p for p in pairs if p['task_id'] == 'qbf-qbfeval')['public'] == 'qbf-public'
    records = product_patch(ROOT)
    assert len(records) == len({r['id'] for r in records}) == 60
    assert sum(r['data_split'] == 'hidden' for r in records) == 30
    assert all(len(r['consumers']) == 2 for r in records)
    assert all(r.get('public_pull_verified') is not True for r in records)


def test_frozen_candidate_copies_only_allowlist_and_rejects_symlinks(tmp_path):
    from tcsexam.solver_data_recipes import prepare_frozen_directory
    root = tmp_path / 'repo'
    root.mkdir()
    (root / 'recipe.json').write_text(json.dumps({'input_id': 'candidate-input'}))
    row = {'path': 'tests/instances/one.dat', 'bytes': 4,
           'sha256': hashlib.sha256(b'data').hexdigest(), 'mode': '0644'}
    source = tmp_path / 'source'
    (source / 'tests/instances').mkdir(parents=True)
    (source / row['path']).write_bytes(b'data')
    (source / 'answer.secret').write_bytes(b'excluded')
    resource = {'id': 'candidate', 'recipe': 'recipe.json', 'data_split': 'hidden'}
    output = tmp_path / 'output'
    assert prepare_frozen_directory(root, resource, [row], output,
                                    inputs={'candidate-input': source}) == {'files': 1, 'bytes': 4}
    assert not (output / 'answer.secret').exists()
    with pytest.raises(ValueError, match='acquisition remains pending'):
        prepare_frozen_directory(root, resource, [row], tmp_path / 'missing')
    (source / row['path']).unlink()
    (source / row['path']).symlink_to(source / 'answer.secret')
    with pytest.raises(ValueError, match='contains a link'):
        prepare_frozen_directory(root, resource, [row], tmp_path / 'bad',
                                 inputs={'candidate-input': source})


def test_product_patch_refreshes_late_manifest_without_erasing_evidence(tmp_path):
    from tcsexam.solver_data_recipes import product_patch
    (tmp_path / 'suites').mkdir()
    (tmp_path / 'suites/tasks.json').write_text(json.dumps({'tasks': [{'id': 'late', 'track': 'solver'}]}))
    assets = tmp_path / 'assets'
    (assets / 'data/solver').mkdir(parents=True)
    name = 'solver-late-judging-data'
    original = {'id': name, 'type': 'data', 'content_version': 'frozen-inputs-261029-v1',
                'missing_frozen_manifest': True, 'recipe_format': 'unavailable',
                'harbor_verified': True, 'verification_scope': {'example': 'preserve'}}
    (assets / 'images.json').write_text(json.dumps({'images': [original]}))
    row = {'path': 'tests/instances/one.txt', 'sha256': '1' * 64, 'bytes': 42, 'mode': '0644'}
    manifest = assets / 'data/solver' / (name + '-files.json')
    manifest.write_text(json.dumps({'files': [row]}))
    result = next(r for r in product_patch(tmp_path) if r['id'] == name)
    assert result['files'] == 1 and result['bytes'] == 42
    assert result['manifest_sha256'] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert result['recipe_format'] == 'frozen_directory'
    assert 'missing_frozen_manifest' not in result
    assert result['harbor_verified'] is True
    assert result['verification_scope'] == original['verification_scope']
    (assets / 'images.json').write_text(json.dumps({'images': [result]}))
    assert next(r for r in product_patch(tmp_path) if r['id'] == name) == result


def test_mqlib_replay_uses_saved_permutation_without_new_random_mapping():
    import importlib.util
    from tcsexam.maxcut_data import transform_raw
    path = ROOT / 'assets/data/solver/maxcut-mqlib/transform.py'
    spec = importlib.util.spec_from_file_location('frozen_mqlib_test_transform', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = b'# original name\n3 2\n1 2 -0.500\n2 3 2\n'
    expected = b'3 2\n1 2 2\n1 3 -0.500\n'
    record = {'perm': [3, 1, 2],
              'sha256_orig_bytes': hashlib.sha256(original).hexdigest(),
              'sha256_new_bytes': hashlib.sha256(expected).hexdigest()}
    assert transform_raw(original, record, module) == expected
    assert module.MASTER_SEED_TAG == 'tcshard-transform-20260831'
    record['perm'] = [1, 1, 3]
    with pytest.raises(ValueError, match='bijection'):
        transform_raw(original, record, module)


def test_fresh_mqlib_product_retains_declared_public_library_zip(tmp_path):
    from tcsexam.solver_data_recipes import product_patch
    (tmp_path / 'suites').mkdir()
    (tmp_path / 'suites/tasks.json').write_text(json.dumps({
        'tasks': [{'id': 'maxcut-mqlib', 'track': 'solver'}]}))
    assets = tmp_path / 'assets'
    data = assets / 'data/solver'
    data.mkdir(parents=True)
    (assets / 'images.json').write_text(json.dumps({'images': []}))
    name = 'solver-maxcut-mqlib-development-data'
    row = {'path': 'opt/mqlib-instances/public-graph.zip', 'sha256': '1' * 64,
           'bytes': 42, 'mode': '0644'}
    (data / (name + '-files.json')).write_text(json.dumps({'files': [row]}))
    (data / (name + '-recipe.json')).write_text(json.dumps({'format': 'official_mqlib'}))
    result = next(r for r in product_patch(tmp_path) if r['id'] == name)
    assert result['recipe_format'] == 'official_mqlib'
    assert result['files'] == 1
    assert result['data_split'] == 'public'
    assert result['public_upload_allowed'] is False


def test_official_single_file_archive_checks_frozen_content_and_member_count(tmp_path):
    import io
    import lzma
    import tarfile
    from tcsexam.official_file_data import prepare_data
    root = tmp_path / 'repo'
    root.mkdir()
    source = tmp_path / 'official.tar.xz'
    def archive(names):
        with tarfile.open(source, 'w:xz') as tar:
            for name, data in names:
                member = tarfile.TarInfo(name)
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
    archive([('instance.gr', b'p tw 2 1\n1 2\n')])
    payload = b'p tw 2 1\n1 2\n'
    row = {'path': 'app/instances/instance.gr', 'bytes': len(payload),
           'sha256': hashlib.sha256(payload).hexdigest(), 'mode': '0644'}
    data = {'sources': [{'id': 'fixed', 'bytes': source.stat().st_size,
                         'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}],
            'outputs': [{'path': row['path'], 'source_id': 'fixed', 'operation': 'tar_single_file'}]}
    (root / 'recipe.json').write_text(json.dumps(data))
    resource = {'recipe': 'recipe.json'}
    result = prepare_data(root, resource, [row], tmp_path / 'output', tmp_path / 'downloads',
                          inputs={'fixed': source})
    assert result == {'files': 1, 'bytes': len(payload)}
    archive([('instance.gr', payload), ('extra-answer.out', b'unselected')])
    data['sources'][0].update(bytes=source.stat().st_size,
                              sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    (root / 'recipe.json').write_text(json.dumps(data))
    with pytest.raises(ValueError, match='exactly one regular file'):
        prepare_data(root, resource, [row], tmp_path / 'bad-output', tmp_path / 'downloads',
                     inputs={'fixed': source})


def test_official_archive_copies_only_selected_input_and_checks_hash(tmp_path):
    from tcsexam.official_archive_data import prepare_data
    root = tmp_path / 'repo'
    root.mkdir()
    archive = tmp_path / 'official.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('private/101.gr', b'p ocr 1 1 1\n1 2\n')
        z.writestr('solutions/101.sol', b'not selected')
    payload = b'p ocr 1 1 1\n1 2\n'
    row = {'path': 'tests/instances/101.gr', 'bytes': len(payload),
           'sha256': hashlib.sha256(payload).hexdigest(), 'mode': '0644'}
    source = {'id': 'official', 'format': 'zip', 'bytes': archive.stat().st_size,
              'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
    recipe_data = {'sources': [source], 'outputs': [
        {'path': row['path'], 'source_id': source['id'], 'source_member': 'private/101.gr'}]}
    (root / 'recipe.json').write_text(json.dumps(recipe_data))
    output = tmp_path / 'output'
    assert prepare_data(root, {'recipe': 'recipe.json'}, [row], output, tmp_path / 'downloads',
                         inputs={'official': archive}) == {'files': 1, 'bytes': len(payload)}
    assert not (output / 'solutions').exists()
    corrupt = dict(row, sha256='0' * 64)
    with pytest.raises(ValueError, match='content differs'):
        prepare_data(root, {'recipe': 'recipe.json'}, [corrupt], tmp_path / 'bad', tmp_path / 'downloads',
                     inputs={'official': archive})
