"""Validate the final data selection without downloading or transforming inputs."""
import hashlib
import json
from pathlib import Path

import pytest

from tcsexam.maxsat_data import validate_recipe
from tcsexam.resources import content_digest, digest
from tcsexam.solver_data_recipes import product_patch, validate_payload


ROOT = Path(__file__).resolve().parents[3]
SELECTION_PATH = ROOT / 'assets/data/solver/final-evaluation-selection.json'
EXCLUDED = {
    'maxsat-mse': {f'ex{i:03d}.wcnf' for i in (99, 110, 116, 121, 139, 146, 149, 166, 177, 186, 199)},
    'radiation-mznchallenge': {f'ex{i:03d}.dzn' for i in (*range(11, 20), 43, 44)},
}


@pytest.mark.parametrize('task,original_count,count,suffix', [
    ('maxsat-mse', 211, 200, 'wcnf'),
    ('radiation-mznchallenge', 47, 36, 'dzn'),
])
def test_final_selection_keeps_original_names_and_exact_input_contract(task, original_count, count, suffix):
    document = json.loads(SELECTION_PATH.read_text())
    assert document['id'] == 'public-disjoint-final-261105'
    selected = document['tasks'][task]
    expected = {f'ex{i:03d}.{suffix}' for i in range(1, original_count + 1)} - EXCLUDED[task]
    assert set(selected['excluded_keys']) == EXCLUDED[task]
    assert len(selected['retained_keys']) == len(expected) == count
    assert set(selected['retained_keys']) == expected
    assert selected['original_judged'] == original_count and selected['selected_judged'] == count
    resource = next(r for r in product_patch(ROOT) if r['id'] == f'solver-{task}-judging-data')
    manifest_path = ROOT / resource['files_manifest']
    files = json.loads(manifest_path.read_text())['files']
    recipe = json.loads((ROOT / resource['recipe']).read_text())
    names = validate_payload(files, 'hidden')
    assert {Path(name).name.removesuffix('.xz') for name in names} == expected
    assert names == {row['path'] for row in recipe['outputs']}
    assert len(files) == len(recipe['outputs']) == count
    assert digest(manifest_path) == selected['files_manifest_sha256'] == resource['manifest_sha256']
    assert resource['content_digest'] == content_digest(files, '/')
    assert recipe['content_version'] == selected['content_version'] == resource['content_version']
    assert recipe['evaluation_selection'] == {
        'id': document['id'], 'path': 'assets/data/solver/final-evaluation-selection.json'}
    evidence = json.loads((ROOT / recipe['distribution_evidence']).read_text())
    if task == 'maxsat-mse':
        assert evidence['compressed_manifest']['sha256'] == resource['manifest_sha256']
        assert evidence['compressed_manifest']['files'] == count
    else:
        assert evidence['manifest_sha256'] == resource['manifest_sha256']
        assert {row['path'] for row in evidence['inputs']} == names
        assert evidence['files'] == count
    if task == 'maxsat-mse':
        validate_recipe(ROOT, resource, files)
        contract = selected['retained_plaintext_contract']
        values = [{k: row[k] for k in contract['fields']} for row in recipe['outputs']]
        encoded = json.dumps(values, sort_keys=True, separators=(',', ':')).encode()
        assert hashlib.sha256(encoded).hexdigest() == contract['sha256']
        historical = json.loads((ROOT / 'assets/data/solver/maxsat-mse/original211-files.json').read_text())['files']
        historical_by_path = {r['path']: r for r in historical}
        assert all(r['original_compressed_sha256'] == historical_by_path[r['path']]['sha256']
                   for r in recipe['outputs'])
        # A missing retained row fails the existing generator's exact-set check.
        with pytest.raises(ValueError, match='output selection differs'):
            validate_recipe(ROOT, resource, files[:-1])


@pytest.mark.parametrize('task', sorted(EXCLUDED))
def test_public_input_identity_is_unchanged_and_sources_are_disjoint(task):
    selected = json.loads(SELECTION_PATH.read_text())['tasks'][task]
    public = selected['public_data_identity']
    assert digest(ROOT / public['recipe_path']) == public['recipe_sha256']
    assert digest(ROOT / public['files_manifest_path']) == public['files_manifest_sha256']
    public_recipe = json.loads((ROOT / public['recipe_path']).read_text())
    public_files = json.loads((ROOT / public['files_manifest_path']).read_text())['files']
    final_recipe = json.loads((ROOT / f'assets/data/solver/solver-{task}-judging-data-recipe.json').read_text())
    if task == 'maxsat-mse':
        public_members = {r['source_member'] for r in public_recipe['outputs'] if 'source_member' in r}
        final_members = {r['source_member'] for r in final_recipe['outputs']}
        assert len(public_members) == selected['public'] == 11
        assert not public_members & final_members
    else:
        final_files = json.loads((ROOT / selected['files_manifest']).read_text())['files']
        assert len(public_files) == selected['public'] == 15
        assert not {r['sha256'] for r in public_files} & {r['sha256'] for r in final_files}
        assert len(final_recipe['sources']) == 12
        source_ids = {r['source_id'] for r in final_recipe['outputs'] if r['operation'] == 'copy'}
        assert source_ids == {r['id'] for r in final_recipe['sources']}


def test_selection_contains_no_local_paths_or_platform_identifiers():
    text = SELECTION_PATH.read_text()
    for value in ('/home/', '/mnt/', '/root/', 'sandbox_id', 'container_id', 'run_id'):
        assert value not in text.lower()
    selection = json.loads(text)
    assert set(selection) == {'schema_version', 'id', 'description', 'policy', 'tasks'}
    common = {'original_judged', 'selected_judged', 'public', 'retained_keys',
              'excluded_keys', 'content_version', 'files_manifest',
              'files_manifest_sha256', 'original_files_manifest_sha256',
              'public_data_identity'}
    for name, task in selection['tasks'].items():
        extra = {'retained_plaintext_contract'} if name == 'maxsat-mse' else set()
        assert set(task) == common | extra
