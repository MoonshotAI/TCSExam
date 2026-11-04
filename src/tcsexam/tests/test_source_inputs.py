import hashlib
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from tcsexam import cli, source_inputs


@pytest.fixture
def materials(tmp_path):
    root = tmp_path / 'checkout'
    directory = root / source_inputs.GRAPHVIZ
    directory.mkdir(parents=True)
    (root / 'tasks').mkdir()
    (root / 'suites').mkdir()
    (root / 'suites/tasks.json').write_text('{}')
    payloads = {'graphviz': b'fixed graphviz archive', 'wrapper': b'fixed wrapper archive'}
    manifest = {}
    for name, data in payloads.items():
        manifest[name] = {'archive': {
            'file': f'source/{name}.tar.gz', 'official_url': f'https://upstream.example/{name}.tar.gz',
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'sha512': hashlib.sha512(data).hexdigest(),
        }}
    (directory / 'source-manifest.json').write_text(json.dumps(manifest))
    return root, tmp_path / 'cache', payloads, manifest


def install_downloads(monkeypatch, payloads):
    calls = []
    def download(url, timeout):
        calls.append(url)
        return io.BytesIO(payloads[Path(url).name.removesuffix('.tar.gz')])
    monkeypatch.setattr(source_inputs, 'urlopen', download)
    return calls


def test_downloads_exact_inputs_and_reuses_verified_cache(materials, monkeypatch):
    root, cache, payloads, manifest = materials
    calls = install_downloads(monkeypatch, payloads)
    report = source_inputs.prepare_source_inputs(root, cache)
    assert len(calls) == 2
    assert {r['acquisition'] for r in report['prepared']} == {'public_download'}
    for name, data in payloads.items():
        path = root / source_inputs.GRAPHVIZ / manifest[name]['archive']['file']
        assert path.read_bytes() == data
        path.unlink()
    report = source_inputs.prepare_source_inputs(root, cache, offline=True)
    assert len(calls) == 2
    assert {r['acquisition'] for r in report['prepared']} == {'verified_cache'}
    assert not list(cache.rglob('.source-*'))


def test_explicit_import_and_hot_context_are_verified_without_network(materials, monkeypatch):
    root, cache, payloads, manifest = materials
    inputs = {}
    for name, data in payloads.items():
        path = root.parent / (name + '.tar.gz')
        path.write_bytes(data)
        inputs[name] = path
    monkeypatch.setattr(source_inputs, 'urlopen', lambda *a, **kw: pytest.fail('unexpected network'))
    report = source_inputs.prepare_source_inputs(root, cache, inputs, offline=True)
    assert {r['acquisition'] for r in report['prepared']} == {'explicit_input'}
    assert {r['acquisition'] for r in source_inputs.prepare_source_inputs(root, cache)['prepared']} == {'verified_context'}
    path = root / source_inputs.GRAPHVIZ / manifest['graphviz']['archive']['file']
    path.write_bytes(b'x' * len(payloads['graphviz']))
    with pytest.raises(ValueError, match='sha256 mismatch'):
        source_inputs.prepare_source_inputs(root, cache, inputs)


def test_corrupt_hot_cache_fails_even_when_context_is_valid(materials, monkeypatch):
    root, cache, payloads, manifest = materials
    install_downloads(monkeypatch, payloads)
    source_inputs.prepare_source_inputs(root, cache)
    record = manifest['wrapper']['archive']
    path = cache / 'lean-source-inputs' / (record['sha256'] + '.tar.gz')
    path.write_bytes(b'x' * len(payloads['wrapper']))
    with pytest.raises(ValueError, match='sha256 mismatch'):
        source_inputs.prepare_source_inputs(root, cache)


@pytest.mark.parametrize('data', [b'too short', b'x' * 100, b'x' * len(b'fixed graphviz archive')])
def test_bad_download_is_never_installed(materials, monkeypatch, data):
    root, cache, payloads, manifest = materials
    monkeypatch.setattr(source_inputs, 'urlopen', lambda *a, **kw: io.BytesIO(data))
    with pytest.raises(ValueError, match='use --input graphviz=PATH'):
        source_inputs.prepare_source_inputs(root, cache)
    assert not list(cache.rglob('*.tar.gz'))
    assert not list(cache.rglob('.source-*'))
    assert not (root / source_inputs.GRAPHVIZ / 'source/graphviz.tar.gz').exists()


def test_missing_or_wrong_explicit_source_fails_before_network(materials, monkeypatch):
    root, cache, _, _ = materials
    monkeypatch.setattr(source_inputs, 'urlopen', lambda *a, **kw: pytest.fail('unexpected network'))
    with pytest.raises(ValueError, match='regular file'):
        source_inputs.prepare_source_inputs(root, cache, {'wrapper': root / 'missing'})
    bad = root / 'bad.tar.gz'
    bad.write_bytes(b'wrong')
    with pytest.raises(ValueError, match='size mismatch'):
        source_inputs.prepare_source_inputs(root, cache, {'wrapper': bad})
    with pytest.raises(ValueError, match='Missing graphviz'):
        source_inputs.prepare_source_inputs(root, cache, offline=True)


def test_blocked_public_download_reports_explicit_fallback(materials, monkeypatch):
    root, cache, _, _ = materials
    def blocked(*args, **kwargs):
        raise HTTPError('https://upstream.example', 403, 'Forbidden', {}, None)
    monkeypatch.setattr(source_inputs, 'urlopen', blocked)
    with pytest.raises(ValueError, match='HTTPError.*--input graphviz=PATH'):
        source_inputs.prepare_source_inputs(root, cache)


def test_reads_are_bounded_and_missing_source_cli_is_clear(materials, monkeypatch, capsys):
    root, cache, payloads, _ = materials
    class Bounded(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= source_inputs.BLOCK_SIZE
            return super().read(size)
    monkeypatch.setattr(source_inputs, 'urlopen', lambda url, **kw: Bounded(payloads[Path(url).stem.split('.')[0]]))
    source_inputs.prepare_source_inputs(root, cache)
    assert cli.main(['source-inputs', '--root', str(root), '--cache', str(cache), '--offline']) == 0
    assert 'verified_context' in capsys.readouterr().out


@pytest.mark.parametrize('values', [['unknown=x'], ['graphviz='], ['graphviz=x', 'graphviz=y']])
def test_input_names_are_explicit_and_unique(values):
    with pytest.raises(ValueError, match='unique graphviz=PATH'):
        source_inputs.explicit_sources(values)
