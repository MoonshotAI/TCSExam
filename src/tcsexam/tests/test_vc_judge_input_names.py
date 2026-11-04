import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    generic = module(ROOT / 'assets/environments/solver/judge-runtime/prepare.py', 'vc_original_prepare')
    monkeypatch.setitem(sys.modules, 'compressed_prepare', generic)
    wrapper = module(ROOT / 'assets/environments/solver/vc-pace2019/judge/prepare_vc.py', 'vc_prepare')
    monkeypatch.setenv('INSTANCE_SET', 'hidden')
    return wrapper, tmp_path


def fixed_input(directory, name='vc-exact_006.xz', data=b'p td 2 1\n1 2\n'):
    packed = lzma.compress(data)
    (directory / name).write_bytes(packed)
    manifest = directory / 'manifest.json'
    manifest.write_text(json.dumps({'files': [{'path': 'tests/instances/' + name,
        'bytes': len(packed), 'sha256': hashlib.sha256(packed).hexdigest()}]}))
    return manifest, packed, data


def test_hidden_alias_is_readable_and_idempotent(inputs):
    wrapper, root = inputs
    manifest, packed, data = fixed_input(root)
    wrapper.prepare(root, manifest)
    assert (root / 'vc-exact_006.gr').is_symlink()
    assert (root / 'vc-exact_006.gr').readlink() == Path('vc-exact_006')
    assert (root / 'vc-exact_006.gr').read_bytes() == data
    assert (root / 'vc-exact_006.xz').read_bytes() == packed
    wrapper.prepare(root, manifest)
    assert (root / 'vc-exact_006').read_bytes() == data


def test_correct_gr_suffix_is_not_added_twice(inputs):
    wrapper, root = inputs
    manifest, _, data = fixed_input(root, 'vc-exact_006.gr.xz')
    wrapper.prepare(root, manifest)
    wrapper.prepare(root, manifest)
    assert (root / 'vc-exact_006.gr').read_bytes() == data
    assert not (root / 'vc-exact_006.gr.gr').exists()


@pytest.mark.parametrize('conflict', ['file', 'wrong_link', 'different_plain'])
def test_conflicting_inputs_fail_without_overwrite(inputs, conflict):
    wrapper, root = inputs
    manifest, packed, _ = fixed_input(root)
    if conflict == 'file':
        (root / 'vc-exact_006.gr').write_bytes(b'other')
    elif conflict == 'wrong_link':
        (root / 'vc-exact_006.gr').symlink_to('other')
    else:
        (root / 'vc-exact_006').write_bytes(b'other')
    with pytest.raises(ValueError, match='overwriting|alias differs|input differs'):
        wrapper.prepare(root, manifest)
    assert (root / 'vc-exact_006.xz').read_bytes() == packed


@pytest.mark.parametrize('problem', ['missing', 'wrong_bytes', 'unknown_path', 'duplicate'])
def test_missing_or_unfixed_source_fails(inputs, problem):
    wrapper, root = inputs
    manifest, _, _ = fixed_input(root)
    records = json.loads(manifest.read_text())
    if problem == 'missing':
        (root / 'vc-exact_006.xz').unlink()
    elif problem == 'wrong_bytes':
        data = bytearray((root / 'vc-exact_006.xz').read_bytes()); data[-1] ^= 1
        (root / 'vc-exact_006.xz').write_bytes(data)
    elif problem == 'unknown_path':
        records['files'][0]['path'] = 'tests/instances/../outside.xz'
    else:
        records['files'] *= 2
    manifest.write_text(json.dumps(records))
    with pytest.raises(ValueError):
        wrapper.prepare(root, manifest)
    assert not (root / 'vc-exact_006.gr').exists()


def test_public_preparation_keeps_generic_names(inputs, monkeypatch):
    wrapper, root = inputs
    manifest, _, data = fixed_input(root)
    monkeypatch.setenv('INSTANCE_SET', 'public')
    wrapper.prepare(root, manifest)
    assert (root / 'vc-exact_006').read_bytes() == data
    assert not (root / 'vc-exact_006.gr').exists()


def test_hidden_dockerfile_selects_exact_manifest_and_wrapper():
    directory = ROOT / 'assets/environments/solver/vc-pace2019/judge'
    hidden = (directory / 'Dockerfile.hidden').read_text()
    public = (directory / 'Dockerfile.public').read_text()
    assert 'prepare.py /judge/compressed_prepare.py' in hidden
    assert 'prepare_vc.py /judge/prepare.py' in hidden
    assert 'solver-vc-pace2019-judging-data-files.json /judge/vc-instance-manifest.json' in hidden
    assert 'prepare_vc.py' not in public
    fixed = json.loads((ROOT / 'assets/data/solver/solver-vc-pace2019-judging-data-files.json').read_text())['files']
    assert len(fixed) == 100
    assert {Path(r['path']).name for r in fixed} == {f'vc-exact_{n:03}.xz' for n in range(2, 201, 2)}
