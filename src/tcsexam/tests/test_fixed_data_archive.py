import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from tcsexam.fixed_data_archive import prepare_data, prepare_image_context


def fixture(tmp_path, *, qbf=False, extra=None):
    content = b'p cnf 1 1\ne 1 0\n1 0\n'
    name = 'opt/qbf-judge300/ex001.qdimacs.xz' if qbf else 'tests/instances/ex001.graph'
    row = dict(path=name, bytes=len(content), sha256=hashlib.sha256(content).hexdigest(), mode='0644')
    (tmp_path / 'manifest.json').write_text(json.dumps({'files': [row]}))
    archive = tmp_path / 'inputs.tar.gz'
    with tarfile.open(archive, 'w:gz') as output:
        member = tarfile.TarInfo(name)
        member.size, member.mode = len(content), 0o644
        output.addfile(member, io.BytesIO(content))
        if extra:
            output.addfile(extra, io.BytesIO(b'x') if extra.isfile() else None)
    recipe = dict(format='fixed_data_archive', task_id='qbf-qbfeval' if qbf else 'fixture',
                  data_split='hidden', archive_format='tar+gzip',
                  source=dict(id='fixed', url=None, bytes=archive.stat().st_size,
                              sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
                  manifest_sha256=hashlib.sha256((tmp_path / 'manifest.json').read_bytes()).hexdigest())
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    resource = dict(id='fixture', recipe='recipe.json', files_manifest='manifest.json')
    return resource, [row], {'fixed': archive}


def test_qbf_original_root_is_preserved_and_image_has_no_public_pin(tmp_path):
    resource, rows, inputs = fixture(tmp_path, qbf=True)
    context = tmp_path / 'context'
    result = prepare_image_context(tmp_path, resource, context, tmp_path / 'downloads', inputs=inputs)
    assert result['files'] == 1
    assert result['public_pin'] is None
    assert result['public_upload_performed'] is False
    assert (context / 'rootfs' / rows[0]['path']).is_file()
    assert 'FROM scratch' in (context / 'Dockerfile').read_text()
    assert 'hidden' in (context / 'Dockerfile').read_text()


@pytest.mark.parametrize('kind', ['extra', 'symlink', 'hardlink', 'traversal'])
def test_archive_rejects_extra_and_special_members(tmp_path, kind):
    member = tarfile.TarInfo('../escaped' if kind == 'traversal' else 'tests/instances/extra')
    member.size = 1
    if kind in ['symlink', 'hardlink']:
        member.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
        member.linkname = '/outside'
    resource, rows, inputs = fixture(tmp_path, extra=member)
    with pytest.raises(ValueError, match='undeclared or special|Unsafe archive path'):
        prepare_data(tmp_path, resource, rows, tmp_path / 'output', tmp_path / 'downloads', inputs=inputs)
    assert not (tmp_path.parent / 'escaped').exists()


def test_explicit_archive_is_required_and_wrong_digest_is_rejected(tmp_path):
    resource, rows, inputs = fixture(tmp_path)
    with pytest.raises(ValueError, match='explicit --input'):
        prepare_data(tmp_path, resource, rows, tmp_path / 'output', tmp_path / 'downloads')
    inputs['fixed'].write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash or size'):
        prepare_data(tmp_path, resource, rows, tmp_path / 'output', tmp_path / 'downloads', inputs=inputs)
