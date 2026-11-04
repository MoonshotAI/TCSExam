"""Public runtime composition must never expand a hidden-data dependency."""
from copy import deepcopy
import json
from pathlib import Path

from tcsexam.solver_recipes import solver_runtime_manifest

ROOT = Path(__file__).resolve().parents[3]


def test_recipes_cover_every_solver_role_and_preserve_input():
    original = json.loads((ROOT / 'assets/images.json').read_text())
    before = deepcopy(original)
    result = solver_runtime_manifest(ROOT, original)
    assert original == before
    rows = [r for r in result['images'] if r.get('source_recipe_generator') == 'tcsexam.solver_recipes']
    for role, count in [('development', 60), ('verifier', 30), ('backend', 30), ('public_backend', 30)]:
        selected = [r for r in rows if r.get('runtime_role') == role]
        assert len(selected) == count
        for row in selected:
            assert (ROOT / row['build']['dockerfile']).is_file()
            assert row['product_prepared'] is False
            assert row['runtime_verified'] is False
    support_ids = {r['id'] for r in rows if not r.get('runtime_role')}
    assert support_ids == {
        'ce-pace2021-backend-base',
        'dfvs-pace2022-backend-base',
        'oscm-pace2024-backend-base',
        'vc-pace2019-backend-base',
        'solver-qbf-qbfeval-development-tools',
        'solver-itc2021-sports-timetabling-development-tools',
    }
    assert len(rows) == 150 + len(support_ids)
    assert solver_runtime_manifest(ROOT, result) == result


def test_public_runtime_has_no_hidden_transitive_dependency():
    rows = solver_runtime_manifest(ROOT, json.loads((ROOT / 'assets/images.json').read_text()))['images']
    by_id = {r['id']: r for r in rows if r.get('id')}
    hidden = {'bpplib-judging', 'qbf-judging'} | {f'solver-{d.name}-judging-data' for d in (ROOT/'tasks/solver/online').iterdir()}
    hidden.update(r['id'] for r in rows if r.get('runtime_role') == 'backend')
    def dependencies(identity, seen):
        assert identity not in hidden
        if identity in seen:
            return
        seen.add(identity)
        for parent in by_id.get(identity, {}).get('dependencies', []):
            dependencies(parent, seen)
    for row in rows:
        if row.get('source_recipe_generator') and row.get('runtime_role') in {'development','public_backend'}:
            dependencies(row['id'], set())


def test_four_legacy_bases_have_source_builds_with_no_frozen_private_parent():
    rows = solver_runtime_manifest(ROOT, json.loads((ROOT/'assets/images.json').read_text()))['images']
    by_id = {r['id']: r for r in rows if r.get('id')}
    for task in ('ce-pace2021','dfvs-pace2022','oscm-pace2024','vc-pace2019'):
        row = by_id[f'{task}-backend-base']
        assert row['build']['image_args'] == {'TCSEXAM_CLEAN_TOOLS_IMAGE': f'dev-online-{task}'}
        assert row['product_prepared'] is False


def test_new_public_payload_consumers_read_only_common_rootfs():
    for task in ('ds-pace2025','hs-pace2025','jsplib-jssp','scp-orlib','tw-heuristic'):
        source = (ROOT/f'tasks/solver/online/{task}/environment/Dockerfile').read_text()
        copies = [line for line in source.splitlines() if line.startswith('COPY --from=')]
        assert any('/payload/rootfs/app/instances/' in line for line in copies)
        assert not any('/opt/jssp-data/' in line or '/opt/tw-public/' in line or '/data/' in line for line in copies)


def test_public_service_map_requires_distinct_prepared_split_references():
    import pytest
    from tcsexam.solver_recipes import solver_public_image_map
    document = json.loads((ROOT/'assets/images.json').read_text())
    refs = {"bpp-bpplib-online-backend":"tcsexam/bpp-hidden:current", "backend-public-online-bpp-bpplib":"tcsexam/bpp-public:current"}
    assert solver_public_image_map(ROOT, document, refs, tasks={"bpp-bpplib"}) == {"tcsexam/bpp-hidden:current":"tcsexam/bpp-public:current"}
    with pytest.raises(ValueError, match="unavailable"):
        solver_public_image_map(ROOT, document, {}, tasks={"bpp-bpplib"})
    refs["backend-public-online-bpp-bpplib"] = refs["bpp-bpplib-online-backend"]
    with pytest.raises(ValueError, match="independently"):
        solver_public_image_map(ROOT, document, refs, tasks={"bpp-bpplib"})


def test_repeated_recipe_generation_retains_new_acceptance():
    original = json.loads((ROOT/'assets/images.json').read_text())
    generated = solver_runtime_manifest(ROOT, original)
    row = next(r for r in generated['images'] if r.get('id') == 'bpp-bpplib-online-backend')
    row.update(product_prepared=True, runtime_verified=True, status='accepted_current_source')
    repeated = solver_runtime_manifest(ROOT, generated)
    row = next(r for r in repeated['images'] if r.get('id') == 'bpp-bpplib-online-backend')
    assert row['product_prepared'] is True and row['runtime_verified'] is True
    assert row['status'] == 'accepted_current_source'
