"""Small graph fixtures cover the adopted permutation and failure boundaries."""
import copy
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import random
from unittest.mock import patch

import pytest
from tcsexam.graph_relabel_data import validate_recipe

ROOT = Path(__file__).resolve().parents[3]
WORKER = ROOT / 'assets/data/solver/graph-relabel/worker.py'
spec = importlib.util.spec_from_file_location('pace_graph_transform', WORKER)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def test_dfvs_empty_rows_and_repeated_directed_edges_have_the_adopted_bytes():
    source = b'% fixture\n4 5 0\n2 2\n3\n4 1\n\n'
    actual, info = worker.transform(source, 'e_001.xz', 'dfvs-pace2022')
    assert actual == b'4 5 0\n3 3\n\n4\n1 2\n'
    assert info['n'] == 4 and info['m'] == 5
    assert info['sha256_orig_tokens'] != info['sha256_new_tokens']
    assert info['output_sha256_plain'] == hashlib.sha256(actual).hexdigest()


def test_oscm_preserves_fixed_labels_and_edge_multiset_including_duplicates():
    source = b'c fixture\np ocr 2 3 5\n1 3\n1 3\n2 4\n5 1\n2 5\n'
    actual, info = worker.transform(source, '191.gr', 'oscm-pace2024')
    assert actual == b'p ocr 2 3 5\n1 3\n2 4\n1 4\n1 3\n2 5\n'
    assert (info['n1'], info['n2'], info['m']) == (2, 3, 5)
    rng = random.Random(worker.seed('191.gr'))
    rho = list(range(1, 4)); rng.shuffle(rho)
    inverse = {2 + new: 2 + old for old, new in enumerate(rho, 1)}
    from collections import Counter
    decoded = Counter((int(u), inverse[int(v)]) for u, v in (line.split() for line in actual.decode().splitlines()[1:]))
    assert decoded == Counter([(1, 3), (1, 3), (2, 4), (1, 5), (2, 5)])


def test_seed_includes_the_original_basename_suffix():
    assert worker.seed('e_001.xz') != worker.seed('e_001')
    assert worker.seed('101.gr') != worker.seed('101')
    expected = hashlib.sha256(b'tcshard-transform-20260831:e_001.xz').digest()[:8]
    assert worker.seed('e_001.xz') == int.from_bytes(expected, 'big')


@pytest.mark.parametrize('task,source', [('dfvs-pace2022', b'2 1 0\n3\n\n'),
                                        ('oscm-pace2024', b'p ocr 2 2 1\n1 2\n')])
def test_invalid_vertex_labels_fail_before_output(task, source):
    with pytest.raises(ValueError, match='Invalid'):
        worker.transform(source, 'example', task)


def test_transform_cannot_be_applied_to_a_development_product():
    resource = {'id': 'solver-dfvs-pace2022-development-data'}
    recipe = {'format': 'official_dfvs_xz', 'graph_transform': {
        'task_id': 'dfvs-pace2022', 'id': 'vertex-relabeling-v1',
        'seed_tag': worker.SEED_TAG, 'implementation_path': WORKER.relative_to(ROOT).as_posix(),
        'implementation_sha256': hashlib.sha256(WORKER.read_bytes()).hexdigest()}}
    with pytest.raises(ValueError, match='hidden-data product'):
        validate_recipe(ROOT, resource, [], recipe)


def test_public_dfvs_and_plain_archive_dispatch_keep_their_original_branches(tmp_path):
    from tcsexam.dfvs_pace2022 import prepare_public_data
    from tcsexam.official_archive_data import prepare_data
    # Malformed public fixture reaches the established selection check, never transform.
    (tmp_path / 'recipe.json').write_text(json.dumps({'selection': {}}))
    with patch('tcsexam.graph_relabel_data.prepare_data') as transform:
        with pytest.raises(ValueError, match='selection parameter'):
            prepare_public_data(tmp_path, {'recipe': 'recipe.json'}, [], tmp_path, tmp_path)
        (tmp_path / 'recipe.json').write_text(json.dumps({'outputs': [], 'sources': []}))
        with patch('tcsexam.official_archive_data.verify', return_value='original-branch'):
            assert prepare_data(tmp_path, {'recipe': 'recipe.json'}, [], tmp_path, tmp_path) == 'original-branch'
        transform.assert_not_called()


def test_generation_report_must_match_every_original_token_seed_and_plaintext_hash():
    from tcsexam.graph_relabel_data import verify_generation_report
    _, contract = worker.transform(b'1 1 0\n1\n', 'e_001.xz', 'dfvs-pace2022')
    policy = {'task_id': 'dfvs-pace2022', 'id': 'vertex-relabeling-v1', 'seed_tag': worker.SEED_TAG}
    declaration = {'path': 'tests/instances/e_001.xz', 'bytes': 64, 'sha256': 'a'*64,
                   'transform_contract': contract}
    row = dict(contract, path=declaration['path'], bytes=64, sha256='a'*64)
    recipe = {'graph_transform': policy, 'outputs': [declaration]}
    report = {'task_id': policy['task_id'], 'transform_id': policy['id'], 'seed_tag': policy['seed_tag'], 'files': [row]}
    assert verify_generation_report(recipe, report) == report
    for key in ['seed_hex', 'sha256_orig_tokens', 'sha256_new_tokens', 'output_sha256_plain', 'sha256']:
        broken = copy.deepcopy(report); broken['files'][0][key] = '0'*64
        with pytest.raises(ValueError, match='original transformation contract'):
            verify_generation_report(recipe, broken)
    broken = copy.deepcopy(report); broken['files'].append(row)
    with pytest.raises(ValueError, match='omits or repeats'):
        verify_generation_report(recipe, broken)


@pytest.mark.parametrize('task', ['dfvs-pace2022', 'oscm-pace2024'])
def test_full_judging_contracts_bind_the_original_token_hashes_and_reject_raw_or_partial_sets(task):
    from tcsexam.solver_data_recipes import product_patch
    resource = next(row for row in product_patch(ROOT) if row['id'] == f'solver-{task}-judging-data')
    recipe = json.loads((ROOT/resource['recipe']).read_text())
    rows = json.loads((ROOT/resource['files_manifest']).read_text())['files']
    validate_recipe(ROOT, resource, rows, recipe)
    assert resource['data_split'] == 'hidden'
    assert resource['public_upload_allowed'] is False
    assert resource['distribution_evidence'] == f'docs/licenses/third-party/{task}-hidden-source.json'
    assert all(row['transform_contract']['sha256_orig_tokens'] != row['transform_contract']['sha256_new_tokens'] for row in recipe['outputs'])
    with pytest.raises(ValueError, match='complete judging selection'):
        validate_recipe(ROOT, resource, rows[:-1], recipe)
    wrong = copy.deepcopy(recipe); wrong['outputs'][0]['source_member'] = 'other-official-instance'
    with pytest.raises(ValueError, match='source-member mapping'):
        validate_recipe(ROOT, resource, rows, wrong)
    wrong = copy.deepcopy(recipe); wrong['outputs'][0]['path'] = 'app/instances/public-instance'
    with pytest.raises(ValueError, match='complete judging selection'):
        validate_recipe(ROOT, resource, rows, wrong)
    wrong = copy.deepcopy(recipe); wrong['graph_transform']['implementation_sha256'] = '0'*64
    with pytest.raises(ValueError, match='implementation'):
        validate_recipe(ROOT, resource, rows, wrong)
    if task == 'dfvs-pace2022':
        wrong = copy.deepcopy(recipe); wrong['compression']['threads'] = 2
        with pytest.raises(ValueError, match='single-thread'):
            validate_recipe(ROOT, resource, rows, wrong)
