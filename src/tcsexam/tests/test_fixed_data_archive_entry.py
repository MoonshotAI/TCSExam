"""Exercise explicit archive selection with small synthetic input-only files."""
from argparse import Namespace
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from tcsexam.build import ImageBuilder, build_definition
from tcsexam.fixed_data_archive import effective_resource, recipe_choices
from tcsexam.resources import content_digest, prepare_resource


NAME = 'qbf-judging'


def fixture(root, *, bad_member=False):
    root.mkdir(exist_ok=True)
    (root / 'assets/data/solver/archive-import').mkdir(parents=True)
    (root / 'assets/data/Dockerfile').write_text('FROM scratch\nCOPY rootfs/ /\n')
    (root / 'original-decision.json').write_text('{}\n')
    payload = b'p cnf 1 1\ne 1 0\n1 0\n'
    row = dict(path='opt/qbf-judge300/ex001.qdimacs.xz', bytes=len(payload),
               mode='0644', sha256=hashlib.sha256(payload).hexdigest())
    manifest = root / 'manifest.json'
    manifest.write_text(json.dumps({'files': [row]}))
    archive = root / 'input.tar.gz'
    with tarfile.open(archive, 'w:gz') as out:
        member = tarfile.TarInfo(row['path'])
        member.mode, member.size = 0o644, len(payload)
        out.addfile(member, io.BytesIO(payload))
        if bad_member:
            member = tarfile.TarInfo('undeclared-secret')
            member.size = 1
            out.addfile(member, io.BytesIO(b'x'))
    source = dict(id='qbf-judging-fixed-archive', url=None,
                  bytes=archive.stat().st_size,
                  sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    alternative = dict(format='fixed_data_archive', archive_format='tar+gzip',
                       task_id='qbf-qbfeval', data_split='hidden', source=source,
                       manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                       generator_paths=['src/tcsexam/fixed_data_archive.py'])
    recipe_path = 'assets/data/solver/archive-import/' + NAME + '-recipe.json'
    (root / recipe_path).write_text(json.dumps(alternative))
    (root / 'default.json').write_text(json.dumps({'input_id': 'original-rootfs'}))
    (root / 'src/tcsexam').mkdir(parents=True)
    (root / 'src/tcsexam/resources.py').write_text('# synthetic dispatch\n')
    (root / 'src/tcsexam/build.py').write_text('# synthetic build\n')
    (root / 'src/tcsexam/fixed_data_archive.py').write_text('# synthetic archive implementation\n')
    product = dict(id=NAME, type='data', task_id='qbf-qbfeval', data_split='hidden',
                   recipe='default.json', recipe_format='frozen_directory',
                   files_manifest='manifest.json', manifest_sha256=alternative['manifest_sha256'],
                   content_version='old-frozen-version', content_digest=content_digest([row]),
                   target_root='/', dependencies=['unused-original-builder'],
                   distribution='redistributable', public_upload_allowed=True,
                   distribution_evidence='original-decision.json', harbor_verified=True,
                   verification_scope={'old': 'retain'})
    (root / 'assets/images.json').write_text(json.dumps({'images': [product]}))
    return product, archive, source, row


def options(root, archive):
    return Namespace(data_recipe=[NAME + '=fixed_archive'],
                     input=['qbf-judging-fixed-archive=' + str(archive)], cache=root / 'cache')


def test_five_choices_only_and_no_implicit_fallback(tmp_path, monkeypatch):
    product, archive, source, row = fixture(tmp_path)
    monkeypatch.setattr('tcsexam.resources.download', lambda *a, **k: pytest.fail('Unexpected network'))
    for bad in ['unknown=fixed_archive', NAME + '=anything', '../other=fixed_archive']:
        with pytest.raises(ValueError, match='Unknown declared'):
            recipe_choices([bad])
    with pytest.raises(ValueError, match='Duplicate'):
        recipe_choices([NAME + '=fixed_archive'] * 2)
    with pytest.raises(ValueError, match='acquisition remains pending|undeclared data candidate'):
        prepare_resource(tmp_path, NAME, tmp_path / 'cache', {source['id']: archive})
    with pytest.raises(ValueError, match='explicit --input'):
        prepare_resource(tmp_path, NAME, tmp_path / 'cache', args=options(tmp_path, archive))


def test_effective_resource_preserves_identity_rights_and_removes_original_builder(tmp_path):
    original, archive, source, row = fixture(tmp_path)
    frozen = copy.deepcopy(original)
    chosen = effective_resource(tmp_path, original, [NAME + '=fixed_archive'])
    assert original == frozen
    for key in ['id', 'task_id', 'data_split', 'target_root', 'content_digest', 'files_manifest',
                'manifest_sha256', 'content_version', 'distribution', 'public_upload_allowed',
                'distribution_evidence', 'harbor_verified', 'verification_scope']:
        assert chosen[key] == original[key]
    assert chosen['dependencies'] == []
    assert chosen['recipe_format'] == 'fixed_data_archive'
    definition = build_definition(tmp_path, chosen)
    assert definition['dependencies'] == [] and 'official_builder' not in definition
    assert definition['source_inputs'] == [source]
    (tmp_path / 'src/tcsexam/fixed_data_archive.py').write_text('# revised synthetic implementation\n')
    changed = effective_resource(tmp_path, original, [NAME + '=fixed_archive'])
    assert changed['data_recipe_signature'] != chosen['data_recipe_signature']
    assert build_definition(tmp_path, changed) != definition


def test_explicit_sha_checked_before_cache_reuse_and_atomic_import(tmp_path):
    original, archive, source, row = fixture(tmp_path)
    args = options(tmp_path, archive)
    rootfs = prepare_resource(tmp_path, NAME, args.cache, {source['id']: archive}, args=args)
    assert (rootfs / row['path']).is_file()
    assert 'routes' in rootfs.parts
    marker = json.loads((rootfs.parent / '.complete.json').read_text())
    assert marker['selected_data_recipe'] == 'fixed_archive'
    assert marker['source_sha256'] == source['sha256']
    assert prepare_resource(tmp_path, NAME, args.cache, {source['id']: archive}, args=args) == rootfs
    archive.write_bytes(b'x' * source['bytes'])
    with pytest.raises(ValueError, match='hash or size'):
        prepare_resource(tmp_path, NAME, args.cache, {source['id']: archive}, args=args)
    assert (rootfs / row['path']).is_file()


def test_failed_archive_does_not_publish_cache(tmp_path):
    product, archive, source, row = fixture(tmp_path, bad_member=True)
    args = options(tmp_path, archive)
    with pytest.raises(ValueError, match='undeclared or special'):
        prepare_resource(tmp_path, NAME, args.cache, {source['id']: archive}, args=args)
    assert not list(args.cache.rglob('.complete.json'))


def test_builder_uses_selected_resource_before_dependencies_and_cache(tmp_path, monkeypatch):
    product, archive, source, row = fixture(tmp_path)
    args = options(tmp_path, archive)
    monkeypatch.setattr('tcsexam.build.resolved_images', lambda *a: ({}, {}))
    builder = ImageBuilder(tmp_path, [], args)
    assert builder.records[NAME]['selected_data_recipe'] == 'fixed_archive'
    assert builder.records[NAME]['dependencies'] == []
    calls = []
    def cached(identity, signature, reference):
        calls.append(identity)
        return dict(reference=reference, local=True)
    monkeypatch.setattr(builder, 'cached', cached)
    builder.prepare_product(NAME)
    assert calls == [NAME]
    second = ImageBuilder(tmp_path, [], args)
    monkeypatch.setattr(second, 'cached', lambda *a: pytest.fail('SHA check must precede image cache'))
    archive.write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash or size'):
        second.prepare_product(NAME)


def test_build_cli_accepts_explicit_recipe_and_local_inputs(tmp_path, monkeypatch):
    from tcsexam.cli import main
    product, archive, source, row = fixture(tmp_path)
    captured = []
    monkeypatch.setattr('tcsexam.cli.resolve', lambda args: (tmp_path, []))
    def build(root, rows, args):
        captured.append(args)
        return {'model_started': False}
    monkeypatch.setattr('tcsexam.build.build_selection', build)
    assert main(['build', '--root', str(tmp_path), '--data-recipe', NAME + '=fixed_archive',
                 '--input', source['id'] + '=' + str(archive)]) == 0
    assert captured[0].data_recipe == [NAME + '=fixed_archive']
    assert captured[0].input == [source['id'] + '=' + str(archive)]


def test_resources_cli_rejects_selection_for_another_product(tmp_path):
    from tcsexam.cli import main
    fixture(tmp_path)
    with pytest.raises(SystemExit) as error:
        main(['resources', '--root', str(tmp_path), '--resource', NAME,
              '--data-recipe', 'solver-maxsat-mse-judging-data=fixed_archive'])
    assert error.value.code == 2


def test_declaration_split_mismatch_is_rejected_before_input_access(tmp_path):
    product, archive, source, row = fixture(tmp_path)
    path = tmp_path / ('assets/data/solver/archive-import/' + NAME + '-recipe.json')
    recipe = json.loads(path.read_text())
    recipe['data_split'] = 'public'
    path.write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match='differs from the frozen data identity'):
        effective_resource(tmp_path, product, [NAME + '=fixed_archive'])


def test_complete_cache_content_is_still_checked(tmp_path):
    product, archive, source, row = fixture(tmp_path)
    args = options(tmp_path, archive)
    rootfs = prepare_resource(tmp_path, NAME, args.cache, {source['id']: archive}, args=args)
    (rootfs / row['path']).write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='Content differs'):
        prepare_resource(tmp_path, NAME, args.cache, {source['id']: archive}, args=args)


def test_all_five_real_options_preserve_split_rights_and_exact_declared_version():
    from tcsexam.fixed_data_archive import FIXED_ARCHIVE_PRODUCTS
    root = Path(__file__).resolve().parents[3]
    products = {r['id']: r for r in json.loads((root / 'assets/images.json').read_text())['images']
                if r.get('id')}
    assert len(FIXED_ARCHIVE_PRODUCTS) == 5
    for name in FIXED_ARCHIVE_PRODUCTS:
        old = products[name]
        selected = effective_resource(root, old, [name + '=fixed_archive'])
        for field in ['id', 'task_id', 'data_split', 'target_root', 'distribution', 'public_upload_allowed',
                      'distribution_evidence', 'product_prepared', 'public_image']:
            assert selected.get(field) == old.get(field)
        if name == 'solver-maxsat-mse-judging-data':
            assert selected['content_version'] == 'original-judging211-260912-v1'
            assert selected['manifest_sha256'] == 'ac00850349c32f7d853802c0a6e0b331615523b8b458eab9948f7ce419d719e1'
            expected = root / selected['files_manifest']
            assert hashlib.sha256(expected.read_bytes()).hexdigest() == selected['manifest_sha256']
            rows = json.loads(expected.read_text())['files']
            assert len(rows) == 211 and sum(row['bytes'] for row in rows) == 8332683020
            assert selected['content_digest'] == content_digest(rows, selected['target_root'])
            assert selected['source_inputs'][0]['id'] == 'solver-maxsat-mse-judging211-260912-fixed-archive'
            assert selected['source_inputs'][0]['sha256'] == '31bb63d866b10df1dfe5c1b2c65cf1655434d56bab5635f183a6c55a16cff012'
        else:
            for field in ('files_manifest', 'manifest_sha256', 'content_digest', 'content_version'):
                assert selected.get(field) == old.get(field)
        assert selected['source_inputs'][0]['url'] is None
        assert build_definition(root, selected)['dependencies'] == []


def test_saved_build_manifest_reconstructs_selected_definition(tmp_path):
    from tcsexam.build import definition_signature, validate_manifest
    product, archive, source, row = fixture(tmp_path)
    selected = effective_resource(tmp_path, product, [NAME + '=fixed_archive'])
    definition = build_definition(tmp_path, selected)
    record = dict(id=NAME, local=True, selected_data_recipe='fixed_archive',
                  data_recipe_signature=selected['data_recipe_signature'],
                  build_signature=definition_signature(definition, {}), build_inputs={})
    validate_manifest(tmp_path, {'images': [record]})
    record['data_recipe_signature'] = '0' * 64
    with pytest.raises(ValueError, match='Selected data recipe is stale'):
        validate_manifest(tmp_path, {'images': [record]})


def test_resources_cli_prepares_checked_synthetic_archive(tmp_path, capsys):
    from tcsexam.cli import main
    product, archive, source, row = fixture(tmp_path)
    (tmp_path / 'tasks').mkdir()
    (tmp_path / 'suites').mkdir()
    (tmp_path / 'suites/tasks.json').write_text(json.dumps({'tasks': []}))
    cache = tmp_path / 'cli-cache'
    assert main(['resources', '--root', str(tmp_path), '--resource', NAME,
                 '--data-recipe', NAME + '=fixed_archive', '--input',
                 source['id'] + '=' + str(archive), '--cache', str(cache)]) == 0
    rootfs = Path(capsys.readouterr().out.strip())
    assert rootfs.is_relative_to(cache) and (rootfs / row['path']).is_file()


def test_selected_and_default_cache_routes_can_coexist(tmp_path):
    product, archive, source, row = fixture(tmp_path)
    product['recipe_format'] = 'fixed_tar'
    (tmp_path / 'default.json').write_text(json.dumps({'source': dict(source, id='original-archive')}))
    (tmp_path / 'assets/images.json').write_text(json.dumps({'images': [product]}))
    args = options(tmp_path, archive)
    alternate = prepare_resource(tmp_path, NAME, args.cache, {source['id']: archive}, args=args)
    default = prepare_resource(tmp_path, NAME, args.cache, {'original-archive': archive})
    assert alternate != default
    assert (default / row['path']).read_bytes() == (alternate / row['path']).read_bytes()
    assert prepare_resource(tmp_path, NAME, args.cache, {source['id']: archive}, args=args) == alternate


def test_archive_version_must_match_the_selected_data_version(tmp_path):
    original, archive, source, row = fixture(tmp_path)
    path = tmp_path / 'assets/data/solver/archive-import' / (NAME + '-recipe.json')
    declaration = json.loads(path.read_text())
    declaration['content_version'] = 'next-explicit-data-v1'
    path.write_text(json.dumps(declaration))
    with pytest.raises(ValueError, match='frozen data identity'):
        effective_resource(tmp_path, original, [NAME + '=fixed_archive'])
    selected = effective_resource(tmp_path, dict(original, content_version='next-explicit-data-v1'),
                                  [NAME + '=fixed_archive'])
    assert selected['content_version'] == 'next-explicit-data-v1'
