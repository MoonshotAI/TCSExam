"""Small fixtures for exact official MaxSAT reconstruction and cache identity."""
import copy
import hashlib
import json
import lzma
from pathlib import Path

import pytest

from tcsexam import maxsat_data
from tcsexam.resources import content_digest, prepare_resource


NAME = 'solver-maxsat-mse-judging-data'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(root):
    (root / 'assets').mkdir()
    (root / 'worker.py').write_text('# fixture conversion worker\n')
    plain = b'p wcnf 2 2 4\n4 -2 1 0\n3 2 0\n'
    compressed = lzma.compress(plain)
    row = {'path': 'tests/instances/ex001.wcnf.xz', 'bytes': len(compressed),
           'sha256': sha(compressed), 'mode': '0644'}
    recipe = {'format': 'official_maxsat_generator', 'content_version': 'official211-fixture-v1',
              'plaintext_contract': maxsat_data.PLAINTEXT_CONTRACT,
              'archive_source_id': 'official-archive', 'xz_source_id': 'xz-source',
              'sources': [{'id': 'official-archive', 'filename': 'instances.zip',
                           'url': 'https://example.com/official.zip', 'bytes': 1, 'sha256': sha(b'z')},
                          {'id': 'xz-source', 'filename': 'xz-source.tar.gz',
                           'url': 'https://example.com/xz.tar.gz', 'bytes': 1, 'sha256': sha(b'x')}],
              'implementation_files': {'worker.py': {'destination': 'worker.py',
                                                     'sha256': sha((root / 'worker.py').read_bytes())}},
              'outputs': [{'path': row['path'], 'source_id': 'official-archive',
                           'source_member': 'weighted/example.wcnf.xz', 'operation': 'maxsat_relabel',
                           'canonical_format': 'original-v1',
                           'source_member_bytes': 80, 'source_expanded_limit_bytes': 4096,
                           'source_sha256_plain': sha(b'original canonical fixture'),
                           'output_sha256_plain': sha(plain), 'output_plaintext_bytes': len(plain),
                           'original_seed_name': 'fixture.wcnf', 'seed_hex': '1234567890abcdef',
                           'nvars': 2, 'nclauses': 2, 'top': 4}]}
    (root / 'recipe.json').write_text(json.dumps(recipe))
    (root / 'files.json').write_text(json.dumps({'files': [row]}))
    resource = {'id': NAME, 'type': 'data', 'task_id': 'maxsat-mse', 'data_split': 'hidden',
                'recipe': 'recipe.json', 'recipe_format': 'official_maxsat_generator',
                'content_version': recipe['content_version'], 'files_manifest': 'files.json',
                'manifest_sha256': sha((root / 'files.json').read_bytes()), 'target_root': '/'}
    (root / 'assets/images.json').write_text(json.dumps({'images': [resource]}))
    return resource, [row], recipe, plain, compressed


def report_fixture(root, rows, recipe, compressed):
    output = root / 'output'
    for row in rows:
        path = output / row['path']
        path.parent.mkdir(parents=True)
        path.write_bytes(compressed)
    records = []
    for row, declaration in zip(rows, recipe['outputs']):
        record = dict(declaration, bytes=row['bytes'], sha256=row['sha256'], source_expanded_bytes=100)
        records.append(record)
    report = root / 'report.json'
    report.write_text(json.dumps({'files': records}))
    return output, report


def test_exact_plaintext_report_is_verified_from_compressed_payload(tmp_path):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    assert maxsat_data.validate_recipe(tmp_path, resource, rows) == recipe
    output, report = report_fixture(tmp_path, rows, recipe, compressed)
    maxsat_data.verify_generation_report(recipe, rows, output, report)
    # A worker's claimed output SHA cannot substitute for the actual solver input.
    (output / rows[0]['path']).write_bytes(lzma.compress(plain.replace(b'-2', b' 2')))
    with pytest.raises(ValueError, match='output plaintext differs'):
        maxsat_data.verify_generation_report(recipe, rows, output, report)


@pytest.mark.parametrize('field', ['source_sha256_plain', 'output_sha256_plain', 'seed_hex',
                                   'source_member', 'source_id', 'output_plaintext_bytes',
                                   'nvars', 'nclauses', 'top', 'sha256', 'bytes', 'canonical_format'])
def test_worker_report_cannot_substitute_source_or_output_identity(tmp_path, field):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    output, report = report_fixture(tmp_path, rows, recipe, compressed)
    data = json.loads(report.read_text())
    value = data['files'][0][field]
    data['files'][0][field] = value + 1 if isinstance(value, int) else value + 'wrong'
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='generation report .* differs'):
        maxsat_data.verify_generation_report(recipe, rows, output, report)


@pytest.mark.parametrize('mutation', ['missing-output', 'duplicate-output', 'wrong-source-hash',
                                      'missing-output-hash', 'wrong-implementation', 'source-traversal',
                                      'foreign-source', 'private-input', 'duplicate-source'])
def test_recipe_contract_rejects_incomplete_or_unpinned_conversion(tmp_path, mutation):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    if mutation == 'missing-output': recipe['outputs'] = []
    elif mutation == 'duplicate-output': recipe['outputs'] *= 2
    elif mutation == 'wrong-source-hash': recipe['outputs'][0]['source_sha256_plain'] = 'not-a-hash'
    elif mutation == 'missing-output-hash': recipe['outputs'][0].pop('output_sha256_plain')
    elif mutation == 'wrong-implementation': (tmp_path / 'worker.py').write_text('# changed\n')
    elif mutation == 'source-traversal': recipe['outputs'][0]['source_member'] = '../outside'
    elif mutation == 'foreign-source': recipe['outputs'][0]['source_id'] = 'other-archive'
    elif mutation == 'private-input': recipe['sources'][0]['url'] = None
    elif mutation == 'duplicate-source': recipe['sources'].append(copy.deepcopy(recipe['sources'][0]))
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    with pytest.raises(ValueError):
        maxsat_data.validate_recipe(tmp_path, resource, rows)


def test_complete_payload_without_conversion_provenance_is_not_reused(tmp_path, monkeypatch):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    cache = tmp_path / 'cache'
    target = cache / NAME / resource['content_version']
    payload = target / 'rootfs' / rows[0]['path']
    payload.parent.mkdir(parents=True)
    payload.write_bytes(compressed)
    payload.chmod(0o644)
    (target / '.complete.json').write_text(json.dumps({'content_digest': content_digest(rows)}))
    monkeypatch.setattr(maxsat_data, 'prepare_data', lambda *a, **k: pytest.fail('Must not rebuild silently'))
    with pytest.raises(ValueError, match='cache provenance differs'):
        prepare_resource(tmp_path, NAME, cache)


def test_checked_cache_reuse_binds_recipe_and_rechecks_payload(tmp_path, monkeypatch):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    calls = []
    def generate(root, declaration, entries, output, downloads, **kwargs):
        calls.append(declaration['content_version'])
        destination = output / entries[0]['path']
        destination.parent.mkdir(parents=True)
        destination.write_bytes(compressed)
        destination.chmod(0o644)
    monkeypatch.setattr(maxsat_data, 'prepare_data', generate)
    rootfs = prepare_resource(tmp_path, NAME, tmp_path / 'cache')
    assert prepare_resource(tmp_path, NAME, tmp_path / 'cache') == rootfs
    assert len(calls) == 1
    recipe['outputs'][0]['source_sha256_plain'] = 'a' * 64
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match='cache provenance differs'):
        prepare_resource(tmp_path, NAME, tmp_path / 'cache')
    # Even a matching marker cannot hide changed compressed bytes.
    recipe['outputs'][0]['source_sha256_plain'] = sha(b'original canonical fixture')
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    (rootfs / rows[0]['path']).write_bytes(b'x' * len(compressed))
    with pytest.raises(ValueError, match='Content differs'):
        prepare_resource(tmp_path, NAME, tmp_path / 'cache')


def test_old_pack_recipe_remains_a_separate_non_relabel_contract(tmp_path):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    recipe.pop('plaintext_contract')
    recipe['outputs'][0] = {key: value for key, value in recipe['outputs'][0].items()
                             if key in ('path', 'source_member', 'source_sha256_plain')}
    recipe['outputs'][0]['operation'] = 'maxsat_pack'
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    assert maxsat_data.cache_identity(tmp_path, resource, rows) == {}
    recipe['plaintext_contract'] = maxsat_data.PLAINTEXT_CONTRACT
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match='relabel contract'):
        maxsat_data.validate_recipe(tmp_path, resource, rows)


def load_conversion_module(name):
    import importlib.util
    path = Path(__file__).resolve().parents[3] / 'assets/data/solver/maxsat-mse' / (name + '.py')
    spec = importlib.util.spec_from_file_location('fixture_maxsat_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('seed_name', ['example-01.wcnf', 'example-02.wcnf', 'example-03.wcnf'])
@pytest.mark.parametrize('raw', [
    b'c source comments\nh -3 1 0\n2 2 -1 0\nh 3 -2 0\n7 -3 0\n',
    b'c empty clauses and repeated zero tokens\np ignored header\nh 0\n2 0 1 0\n1 -1 1 0\n',
    b'c non-ascii comment \xff\n  h 3 -2 0  \n\n 4 -1 3 0\n',
])
def test_bounded_converter_and_relabel_match_original_bytes(tmp_path, seed_name, raw):
    convert = load_conversion_module('convert')
    transform = load_conversion_module('transform')
    bounded = load_conversion_module('bounded_transform')
    source = tmp_path / 'new-format.wcnf'
    source.write_bytes(raw)
    canonical = tmp_path / 'canonical-original.wcnf'
    convert.convert(str(source), str(canonical))
    generated = tmp_path / 'canonical-bounded.wcnf'
    metadata = bounded.canonicalize(source, generated, tmp_path / 'work')
    assert generated.read_bytes() == canonical.read_bytes()
    original_plain, nvars, top, clauses = transform.read_wcnf(str(canonical))
    seed = transform.derive_seed(seed_name)
    changed, permutation = transform.transform_clauses(nvars, clauses, seed)
    expected_plain = transform.serialize(nvars, top, changed)
    expected = dict(metadata, nclauses=len(clauses), seed_hex=f'{seed:016x}',
                    permutation_sha256=sha(json.dumps(permutation[1:], separators=(',', ':')).encode()),
                    output_sha256_plain=sha(expected_plain), output_plaintext_bytes=len(expected_plain))
    output = tmp_path / 'relabeled.wcnf'
    report = bounded.relabel(generated, output, seed_name, tmp_path / 'work', expected=expected)
    assert report == expected
    assert output.read_bytes() == expected_plain


@pytest.mark.parametrize('field', ['source_sha256_plain', 'output_sha256_plain', 'seed_hex',
                                   'permutation_sha256', 'output_plaintext_bytes', 'nvars', 'nclauses', 'top'])
def test_actual_relabel_rejects_each_wrong_contract_value(tmp_path, field):
    bounded = load_conversion_module('bounded_transform')
    source = tmp_path / 'canonical.wcnf'
    source.write_bytes(b'p wcnf 2 2 4\n4 1 -2 0\n3 -1 0\n')
    output = tmp_path / 'output.wcnf'
    good = bounded.relabel(source, output, 'small-seed', tmp_path / 'work')
    expected = dict(good)
    value = expected[field]
    expected[field] = value + 1 if isinstance(value, int) else '0' * len(value)
    with pytest.raises(ValueError, match='contract differs|seed differs'):
        bounded.relabel(source, output, 'small-seed', tmp_path / 'work', expected=expected)


@pytest.mark.parametrize('field,value', [('content_version', 'canonical98'),
                                         ('compression_tool_version', '5.2.5; false')])
def test_recipe_version_and_toolchain_cannot_escape_declared_identity(tmp_path, field, value):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    recipe[field] = value
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match='versions differ|XZ version'):
        maxsat_data.validate_recipe(tmp_path, resource, rows)


@pytest.mark.parametrize('field,value', [('compression_preset', 1), ('compression_preset', True),
                                         ('compression_threads', 16), ('compression_threads', '-1; false'),
                                         ('compression_tool_version', '5.8.4')])
def test_per_output_compression_must_match_the_fixed_toolchain(tmp_path, field, value):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    recipe['outputs'][0][field] = value
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match='compression parameters'):
        maxsat_data.validate_recipe(tmp_path, resource, rows)


def legacy_fixture(root):
    import io
    import tarfile
    resource, rows, recipe, plain, compressed = fixture(root)
    old_compressed = lzma.compress(plain, preset=9)
    assert sha(old_compressed) != rows[0]['sha256']
    old = dict(rows[0], sha256=sha(old_compressed), bytes=len(old_compressed))
    old_manifest = root / 'legacy211.json'
    old_manifest.write_text(json.dumps({'files': [old]}))
    archive = root / 'legacy-input.tar.gz'
    with tarfile.open(archive, 'w:gz') as out:
        entry = tarfile.TarInfo(old['path'])
        entry.size = len(old_compressed)
        entry.mode = 0o644
        out.addfile(entry, io.BytesIO(old_compressed))
    path = 'assets/data/solver/archive-import/' + NAME + '-recipe.json'
    legacy = {'recipe': path, 'files_manifest': 'legacy211.json',
              'manifest_sha256': sha(old_manifest.read_bytes()), 'content_version': 'legacy211-fixture-v1'}
    recipe['legacy_fixed_archive'] = legacy
    (root / 'recipe.json').write_text(json.dumps(recipe))
    source = dict(id='original211-fixed-archive', url=None, bytes=archive.stat().st_size,
                  sha256=sha(archive.read_bytes()))
    alternative = dict(format='fixed_data_archive', archive_format='tar+gzip', task_id='maxsat-mse',
                       data_split='hidden', source=source,
                       **{k: v for k, v in legacy.items() if k != 'recipe'})
    (root / path).parent.mkdir(parents=True)
    (root / path).write_text(json.dumps(alternative))
    return resource, rows, recipe, legacy, old, archive, source


def test_legacy_archive_keeps_its_original_bytes_version_and_cache_namespace(tmp_path, monkeypatch):
    from tcsexam.fixed_data_archive import effective_resource
    resource, rows, recipe, legacy, old, archive, source = legacy_fixture(tmp_path)
    original = copy.deepcopy(resource)
    selected = effective_resource(tmp_path, resource, {NAME: 'fixed_archive'})
    assert resource == original
    assert selected['files_manifest'] == legacy['files_manifest']
    assert selected['content_version'] == legacy['content_version']
    assert selected['manifest_sha256'] == legacy['manifest_sha256']
    assert selected['content_digest'] == content_digest([old]) != content_digest(rows)
    assert selected['source_inputs'] == [source]
    assert selected['recipe_format'] == 'fixed_data_archive' and selected['dependencies'] == []
    monkeypatch.setattr(maxsat_data, 'prepare_data', lambda *a, **k: pytest.fail('No official generation for explicit archive'))
    restored = prepare_resource(tmp_path, NAME, tmp_path / 'cache', {source['id']: archive}, resource=selected)
    assert 'routes' in restored.parts and legacy['content_version'] in restored.parts
    assert sha((restored / old['path']).read_bytes()) == old['sha256']
    assert resource['content_version'] not in restored.parts
    # Its existence never satisfies the ordinary official route's current cache.
    with pytest.raises(pytest.fail.Exception, match='No official generation'):
        prepare_resource(tmp_path, NAME, tmp_path / 'cache')


@pytest.mark.parametrize('mutation', ['archive-sha', 'version', 'undeclared-manifest', 'missing-declaration',
                                      'canonical98-subset', 'recipe-version'])
def test_legacy_identity_cannot_be_substituted_for_current_or_canonical98(tmp_path, mutation):
    from tcsexam.fixed_data_archive import effective_resource
    resource, rows, recipe, legacy, old, archive, source = legacy_fixture(tmp_path)
    path = tmp_path / legacy['recipe']
    alternative = json.loads(path.read_text())
    if mutation == 'archive-sha': alternative['manifest_sha256'] = '0' * 64
    elif mutation == 'version': alternative['content_version'] = 'canonical98'
    elif mutation == 'undeclared-manifest': alternative['files_manifest'] = 'files.json'
    elif mutation == 'missing-declaration': recipe.pop('legacy_fixed_archive')
    elif mutation == 'recipe-version': recipe['content_version'] = 'canonical98'
    elif mutation == 'canonical98-subset':
        recipe['outputs'].append(dict(recipe['outputs'][0], path='tests/instances/ex002.wcnf.xz'))
    path.write_text(json.dumps(alternative))
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match='archive alternative differs|archive selection differs'):
        effective_resource(tmp_path, resource, {NAME: 'fixed_archive'})


@pytest.mark.parametrize('wrong_report', [False, True])
def test_resources_cli_uses_official_route_and_requires_plaintext_proof(tmp_path, monkeypatch, capsys, wrong_report):
    from tcsexam.cli import main
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    recipe['build'] = {'builder_image': 'ubuntu:22.04@sha256:' + '1' * 64,
                       'cwd': '.', 'timeout_sec': 60}
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    (tmp_path / 'tasks').mkdir()
    (tmp_path / 'suites').mkdir()
    (tmp_path / 'suites/tasks.json').write_text(json.dumps({'tasks': []}))
    downloads = []
    monkeypatch.setattr(maxsat_data, 'acquire_official_builder', lambda *a, **k: 'sha256:' + '2' * 64)
    def download(source, cache, *args, **kwargs):
        downloads.append(source['id'])
        path = tmp_path / (source['id'] + '.fixture')
        path.write_bytes(b'z' if source['id'] == 'official-archive' else b'x')
        return path
    monkeypatch.setattr(maxsat_data, 'download_official', download)
    def container(command, timeout, logs, *, copy_in, copy_out):
        # Only transport/container execution is replaced. The CLI, dispatcher,
        # staging, both manifest checks, report checks and cache commit are real.
        staged = Path(copy_in[0][0].removesuffix('/.'))
        assert (staged / 'inputs/instances.zip').read_bytes() == b'z'
        assert (staged / 'xz-source.tar.gz').read_bytes() == b'x'
        assert json.loads((staged / 'recipe.json').read_text()) == recipe
        output = Path(copy_out[0][1])
        destination = output / rows[0]['path']
        destination.parent.mkdir(parents=True)
        destination.write_bytes(compressed)
        destination.chmod(0o644)
        record = dict(recipe['outputs'][0], bytes=rows[0]['bytes'], sha256=rows[0]['sha256'],
                      source_expanded_bytes=100)
        if wrong_report:
            record['source_sha256_plain'] = '0' * 64
        Path(copy_out[1][1]).write_text(json.dumps({'files': [record]}))
    monkeypatch.setattr(maxsat_data, 'run_official_container', container)
    monkeypatch.setattr('tcsexam.fixed_data_archive.prepare_data',
                        lambda *a, **k: pytest.fail('No private archive fallback'))
    cache = tmp_path / 'cli-cache'
    command = ['resources', '--root', str(tmp_path), '--resource', NAME, '--cache', str(cache)]
    if wrong_report:
        with pytest.raises(SystemExit) as error:
            main(command)
        assert error.value.code == 2
        assert not list(cache.rglob('.complete.json'))
    else:
        assert main(command) == 0
        rootfs = Path(capsys.readouterr().out.strip())
        marker = json.loads((rootfs.parent / '.complete.json').read_text())
        assert marker['maxsat_plaintext_contract'] == maxsat_data.PLAINTEXT_CONTRACT
        assert marker['maxsat_recipe_sha256'] == sha((tmp_path / 'recipe.json').read_bytes())
        assert lzma.decompress((rootfs / rows[0]['path']).read_bytes()) == plain
    assert downloads == ['official-archive', 'xz-source']


def worker_fixture(root, monkeypatch):
    import sys
    import zipfile
    bounded = load_conversion_module('bounded_transform')
    monkeypatch.setitem(sys.modules, 'bounded_transform', bounded)
    worker = load_conversion_module('rebuild211_worker')
    transform = load_conversion_module('transform')
    convert = load_conversion_module('convert')
    raw = b'c official fixture\nh 1 -3 0\n2 -1 2 0\n5 -2 0\n'
    source = root / 'raw.wcnf'
    source.write_bytes(raw)
    canonical = root / 'canonical.wcnf'
    convert.convert(str(source), str(canonical))
    canonical_plain, nvars, top, clauses = transform.read_wcnf(str(canonical))
    seed_name = 'selected-fixture.wcnf'
    seed = transform.derive_seed(seed_name)
    changed, permutation = transform.transform_clauses(nvars, clauses, seed)
    plain = transform.serialize(nvars, top, changed)
    packed = lzma.compress(raw)
    row = dict(path='tests/instances/ex001.wcnf.xz', source_id='official-archive',
               canonical_format='original-v1',
               source_member='weighted/selected.wcnf.xz', source_member_bytes=len(packed),
               source_expanded_limit_bytes=len(raw), original_seed_name=seed_name,
               seed_hex=f'{seed:016x}', nvars=nvars, nclauses=len(clauses), top=top,
               source_sha256_plain=sha(canonical_plain), output_sha256_plain=sha(plain),
               output_plaintext_bytes=len(plain),
               permutation_sha256=sha(json.dumps(permutation[1:], separators=(',', ':')).encode()))
    archive = root / 'official.zip'
    with zipfile.ZipFile(archive, 'w') as output:
        output.writestr(row['source_member'], packed)
    compressor = root / 'fixture-compressor'
    compressor.write_text('#!' + sys.executable + '\nimport lzma,sys\nsys.stdout.buffer.write(lzma.compress(sys.stdin.buffer.read()))\n')
    compressor.chmod(0o755)
    return worker, row, archive, compressor, plain


def test_actual_worker_processes_selected_official_member_and_reports_both_hashes(tmp_path, monkeypatch):
    import zipfile
    worker, row, archive, compressor, plain = worker_fixture(tmp_path, monkeypatch)
    destination = tmp_path / row['path']
    with zipfile.ZipFile(archive) as source:
        report = worker.rebuild_one(source, row, destination, tmp_path, compressor)
    assert lzma.decompress(destination.read_bytes()) == plain
    for field in ('source_sha256_plain', 'output_sha256_plain', 'seed_hex', 'nvars', 'nclauses',
                  'top', 'source_id', 'source_member', 'source_member_bytes', 'permutation_sha256',
                  'canonical_format'):
        assert report[field] == row[field]
    assert report['sha256'] == sha(destination.read_bytes())
    assert report['bytes'] == destination.stat().st_size
    assert report['source_expanded_bytes'] == row['source_expanded_limit_bytes']
    assert report['output_plaintext_bytes'] == len(plain)


@pytest.mark.parametrize('field,value', [('source_sha256_plain', '0' * 64),
                                         ('output_sha256_plain', '0' * 64),
                                         ('source_member_bytes', 1),
                                         ('source_expanded_limit_bytes', 1),
                                         ('source_expanded_limit_bytes', 0),
                                         ('source_expanded_limit_bytes', 9 * 1024 ** 3)])
def test_actual_worker_rejects_wrong_plaintext_or_source_bounds(tmp_path, monkeypatch, field, value):
    import zipfile
    worker, row, archive, compressor, plain = worker_fixture(tmp_path, monkeypatch)
    row[field] = value
    destination = tmp_path / row['path']
    with zipfile.ZipFile(archive) as source, pytest.raises(ValueError):
        worker.rebuild_one(source, row, destination, tmp_path, compressor)
    assert not destination.exists()


@pytest.mark.parametrize('style', ['original-v1', 'streaming-two-pass-v1'])
def test_strict_recipe_and_generation_report_bind_explicit_canonical_format(tmp_path, style):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    recipe['outputs'][0]['canonical_format'] = style
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    assert maxsat_data.validate_recipe(tmp_path, resource, rows) == recipe
    output, report = report_fixture(tmp_path, rows, recipe, compressed)
    maxsat_data.verify_generation_report(recipe, rows, output, report)
    changed = json.loads(report.read_text())
    changed['files'][0]['canonical_format'] = ('streaming-two-pass-v1' if style == 'original-v1'
                                              else 'original-v1')
    report.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='canonical_format differs'):
        maxsat_data.verify_generation_report(recipe, rows, output, report)


@pytest.mark.parametrize('style', [None, '', 'original-v0', 'unknown', True, [], {}])
def test_strict_recipe_rejects_missing_or_unknown_canonical_format(tmp_path, style):
    resource, rows, recipe, plain, compressed = fixture(tmp_path)
    if style is None:
        recipe['outputs'][0].pop('canonical_format')
    else:
        recipe['outputs'][0]['canonical_format'] = style
    (tmp_path / 'recipe.json').write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match='explicit canonical format'):
        maxsat_data.validate_recipe(tmp_path, resource, rows)


@pytest.mark.parametrize('raw,original_bytes,streaming_bytes', [
    (
        b'c original header\n5 2 0\nc between clauses\nh 1 -2 0\n3 -1 0\n',
        b'c converted from MSE new format (h-lines, no p-line)\n'
        b'c original header\nc between clauses\np wcnf 2 3 9\n'
        b'9 1 -2 0\n5 2 0\n3 -1 0\n',
        b'c converted from MSE new format (h-lines, no p-line), streaming two-pass\n'
        b'p wcnf 2 3 9\n5 2 0\n9 1 -2 0\n3 -1 0\n',
    ),
    (
        b'h -3 1 0\n4 2 0\nh -2 3 0\n2 -1 0\n',
        b'c converted from MSE new format (h-lines, no p-line)\n'
        b'p wcnf 3 4 7\n7 -3 1 0\n7 -2 3 0\n4 2 0\n2 -1 0\n',
        b'c converted from MSE new format (h-lines, no p-line), streaming two-pass\n'
        b'p wcnf 3 4 7\n7 -3 1 0\n4 2 0\n7 -2 3 0\n2 -1 0\n',
    ),
    (
        b'c empty clauses\n5 0\nh 0\n2 -1 0\n',
        b'c converted from MSE new format (h-lines, no p-line)\n'
        b'c empty clauses\np wcnf 1 3 8\n8  0\n5  0\n2 -1 0\n',
        b'c converted from MSE new format (h-lines, no p-line), streaming two-pass\n'
        b'p wcnf 1 3 8\n5  0\n8  0\n2 -1 0\n',
    ),
])
def test_canonical_formats_use_exact_historical_clause_order(tmp_path, raw, original_bytes, streaming_bytes):
    bounded = load_conversion_module('bounded_transform')
    original = load_conversion_module('convert')
    source = tmp_path / 'official.wcnf'
    source.write_bytes(raw)
    reference, default, streaming = (tmp_path / name for name in ('reference', 'default', 'streaming'))
    original.convert(str(source), str(reference))
    # Literal expected bytes bind the format separately from the implementation.
    # No style argument retains the original converter's hard-before-soft order.
    normal_report = bounded.canonicalize(source, default, tmp_path / 'work')
    two_pass_report = bounded.canonicalize(source, streaming, tmp_path / 'work', style='streaming-two-pass-v1')
    assert default.read_bytes() == reference.read_bytes() == original_bytes
    # Two-pass conversion replaces h with top while preserving input clause order.
    assert streaming.read_bytes() == streaming_bytes
    assert normal_report['source_sha256_plain'] == sha(original_bytes)
    assert two_pass_report['source_sha256_plain'] == sha(streaming_bytes)
    assert normal_report['source_sha256_plain'] != two_pass_report['source_sha256_plain']
    assert {key: normal_report[key] for key in ('nvars', 'nclauses', 'top')} == {
        key: two_pass_report[key] for key in ('nvars', 'nclauses', 'top')}
    with pytest.raises(ValueError, match='canonical format'):
        bounded.canonicalize(source, streaming, tmp_path / 'work', style='unknown')
