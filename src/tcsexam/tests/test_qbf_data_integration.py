"""Small synthetic fixtures exercise QBF registration and public dispatch."""
import hashlib
import json
from pathlib import Path

from tcsexam.build import build_definition
from tcsexam.resources import prepare_resource
from tcsexam.solver_data_recipes import product_patch


def fixture(root):
    (root / 'suites').mkdir()
    (root / 'suites/tasks.json').write_text(json.dumps({'tasks': [
        {'id': 'qbf-qbfeval', 'track': 'solver'}]}))
    (root / 'assets/data/qbf').mkdir(parents=True)
    (root / 'assets/data/Dockerfile').write_text('FROM scratch\nCOPY rootfs/ /\n')
    (root / 'existing-product-specific-decision.json').write_text('{}\n')
    data = b'p cnf 1 1\ne 1 0\n1 0\n'
    row = {'path': 'opt/qbf-judge300/ex001.qdimacs.xz', 'mode': '0644',
           'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    manifest = root / 'assets/data/qbf/files.json'
    manifest.write_text(json.dumps({'files': [row]}))
    source = {'id': 'official-artifact', 'bytes': 123, 'sha256': 'a' * 64,
              'url': 'https://example.invalid/official.tar.gz'}
    recipe = {'format': 'official_qbf_generator', 'sources': [source],
              'build': {'builder_image': 'ubuntu:22.04@sha256:' + '1' * 64},
              'generator_paths': ['src/tcsexam/qbf_data.py', 'worker.py']}
    (root / 'assets/data/qbf/judging.json').write_text(json.dumps(recipe))
    (root / 'worker.py').write_text('# synthetic fixed implementation\n')
    (root / 'src/tcsexam').mkdir(parents=True)
    (root / 'src/tcsexam/qbf_data.py').write_text('# synthetic module\n')
    (root / 'src/tcsexam/resources.py').write_text('# synthetic dispatch\n')
    (root / 'src/tcsexam/build.py').write_text('# synthetic build\n')
    product = {'id': 'qbf-judging', 'type': 'data', 'recipe_format': 'fixed_tar',
               'recipe': 'assets/data/qbf/judging.json',
               'files_manifest': 'assets/data/qbf/files.json',
               'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
               'target_root': '/', 'content_version': 'existing-version',
               'source_input': {'id': 'obsolete-tar'}, 'source_input_file': 'old.tar',
               'harbor_verified': True, 'verification_scope': {'retain': True},
               'distribution': 'permitted_data_image', 'public_upload_allowed': True,
               'distribution_evidence': 'existing-product-specific-decision.json'}
    (root / 'assets/images.json').write_text(json.dumps({'images': [product]}))
    return product, row, data, source


def test_special_qbf_id_refreshes_recipe_sources_and_preserves_accepted_facts(tmp_path):
    original, row, data, source = fixture(tmp_path)
    result = next(p for p in product_patch(tmp_path) if p['id'] == 'qbf-judging')
    assert result['recipe_format'] == 'official_qbf_generator'
    assert result['source_inputs'] == [source]
    assert 'source_input' not in result and 'source_input_file' not in result
    assert result['acquisition'] == {'preferred': 'local_build'}
    assert result['task_id'] == 'qbf-qbfeval' and result['data_split'] == 'hidden'
    assert result['target_root'] == '/' and result['files_manifest'] == original['files_manifest']
    assert result['harbor_verified'] and result['verification_scope'] == original['verification_scope']
    assert result['public_upload_allowed'] is True
    assert result['distribution'] == original['distribution']
    assert result['distribution_evidence'] == original['distribution_evidence']
    assert result['files'] == 1 and result['bytes'] == len(data)
    (tmp_path / 'assets/images.json').write_text(json.dumps({'images': [result]}))
    assert next(p for p in product_patch(tmp_path) if p['id'] == 'qbf-judging') == result


def test_qbf_build_identity_pins_builder_and_generator(tmp_path):
    fixture(tmp_path)
    product = next(p for p in product_patch(tmp_path) if p['id'] == 'qbf-judging')
    first = build_definition(tmp_path, product)
    assert first['official_builder'] == 'ubuntu:22.04@sha256:' + '1' * 64
    assert first['pull_args'] == {'TCSEXAM_OFFICIAL_BUILDER': first['official_builder']}
    (tmp_path / 'worker.py').write_text('# changed synthetic fixed implementation\n')
    assert build_definition(tmp_path, product)['source_digest'] != first['source_digest']


def test_public_resource_dispatch_uses_qbf_generator_and_atomic_checked_cache(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    root.mkdir()
    fixture(root)
    product = next(p for p in product_patch(root) if p['id'] == 'qbf-judging')
    (root / 'assets/images.json').write_text(json.dumps({'images': [product]}))
    calls = []
    def synthetic(root, resource, rows, output, downloads, **kwargs):
        calls.append(kwargs)
        target = Path(output) / rows[0]['path']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'p cnf 1 1\ne 1 0\n1 0\n')
        target.chmod(0o644)
    monkeypatch.setattr('tcsexam.qbf_data.prepare_data', synthetic)
    options = {'inputs': {'official-artifact': 'explicit-file'},
               'args': {'example': True}, 'builder_image': 'fixed-builder'}
    result = prepare_resource(root, 'qbf-judging', tmp_path / 'cache', **options)
    assert (result / 'opt/qbf-judge300/ex001.qdimacs.xz').is_file()
    assert calls == [options]
    assert prepare_resource(root, 'qbf-judging', tmp_path / 'cache', **options) == result
    assert len(calls) == 1
