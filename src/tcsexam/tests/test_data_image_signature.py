"""Track every data-image packaging input, independent of instance bytes."""
import hashlib
import json

import pytest

from tcsexam.build import build_definition, definition_signature
from tcsexam.resources import stage_data_context


@pytest.fixture
def resource(tmp_path):
    def write(path, value):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value)
        target.chmod(0o644)
        return target

    write('assets/data/Dockerfile', 'FROM scratch\nCOPY rootfs /payload/rootfs\n')
    write('src/tcsexam/resources.py', '# preparation implementation\n')
    write('src/tcsexam/build.py', '# build implementation\n')
    for path in ('evidence.json', 'distribution.json', 'LICENSE.txt',
                 'docs/licenses/third-party/BPPLIB-CC-BY-NC-ND-4.0.txt'):
        write(path, 'original materials\n')
    license_file = tmp_path / 'LICENSE.txt'
    recipe = {'license_files': [{'path': 'LICENSE.txt', 'bytes': license_file.stat().st_size,
                                'sha256': hashlib.sha256(license_file.read_bytes()).hexdigest()}]}
    write('recipe.json', json.dumps(recipe))
    write('rootfs/input.txt', 'input\n')
    entries = [{'path': 'input.txt', 'bytes': 6, 'mode': '0644',
                'sha256': hashlib.sha256(b'input\n').hexdigest()}]
    manifest = write('files.json', json.dumps({'files': entries}))
    row = {'id': 'bpplib-development', 'type': 'data', 'recipe': 'recipe.json',
           'files_manifest': 'files.json', 'target_root': '/', 'content_version': 'v1',
           'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
           'distribution': 'local_prepare', 'public_upload_allowed': False,
           'distribution_evidence': 'distribution.json'}
    return tmp_path, row


@pytest.mark.parametrize('path,evidence_field', [
    ('assets/data/Dockerfile', None), ('distribution.json', None),
    ('evidence.json', 'evidence'), ('LICENSE.txt', None),
    ('docs/licenses/third-party/BPPLIB-CC-BY-NC-ND-4.0.txt', None),
])
def test_packaged_file_changes_invalidate_the_build_signature(resource, path, evidence_field):
    root, row = resource
    if evidence_field:
        row[evidence_field] = path
    before = definition_signature(build_definition(root, row), {})
    context = stage_data_context(root, row['id'], root / 'rootfs', root / 'context', row)
    assert (context / ('Dockerfile' if path.endswith('Dockerfile') else 'licenses/' + path.split('/')[-1])).is_file()
    source = root / path
    source.write_text(source.read_text() + 'changed\n')
    assert definition_signature(build_definition(root, row), {}) != before
    if path == 'LICENSE.txt':
        with pytest.raises(ValueError, match='license hash or size'):
            stage_data_context(root, row['id'], root / 'rootfs', root / 'invalid-context', row)


@pytest.mark.parametrize('key,value', [('content_version', 'v2'),
                                      ('distribution', 'redistributable'),
                                      ('public_upload_allowed', True)])
def test_packaged_metadata_changes_invalidate_the_build_signature(resource, key, value):
    root, row = resource
    before = definition_signature(build_definition(root, row), {})
    row[key] = value
    context = stage_data_context(root, row['id'], root / 'rootfs', root / 'context', row)
    assert json.loads((context / 'manifest/content.json').read_text())[key] == value
    assert definition_signature(build_definition(root, row), {}) != before


def test_build_implementation_change_invalidates_resource_signature(resource):
    root, row = resource
    before = build_definition(root, row)
    source = root / 'src/tcsexam/build.py'
    source.write_text(source.read_text() + '# changed resource build behavior\n')
    after = build_definition(root, row)
    assert definition_signature(after, {}) != definition_signature(before, {})
    assert after['manifest_sha256'] == before['manifest_sha256']
