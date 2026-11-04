"""Keep historical98 and adopted211 data identities distinct."""
import hashlib
import json
from pathlib import Path

import pytest

from tcsexam.resources import content_digest
from tcsexam.solver_data_recipes import product_patch

ROOT = Path(__file__).resolve().parents[3]
NAME = 'solver-maxsat-mse-judging-data'
VERSION = 'original-judging211-260912-v1'


def test_original211_manifest_matches_every_pinned_reference_key():
    manifest = ROOT / 'assets/data/solver/maxsat-mse/original211-files.json'
    rows = json.loads(manifest.read_text())['files']
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == 'ac00850349c32f7d853802c0a6e0b331615523b8b458eab9948f7ce419d719e1'
    assert len(rows) == len({r['path'] for r in rows}) == 211
    assert sum(r['bytes'] for r in rows) == 8332683020
    keys = {Path(r['path']).name.removesuffix('.xz') for r in rows}
    current_manifest = ROOT / f'assets/data/solver/{NAME}-files.json'
    assert hashlib.sha256(current_manifest.read_bytes()).hexdigest() == '39812c49fe6fce8c0aa759704e63cb11bc03982f70e4ef5259341a7af579a61e'
    current = json.loads(current_manifest.read_text())['files']
    assert content_digest(current, '/') == 'sha256:ebe3c76067d945cadaaaa9227857bc9aac72a49df08d802e4265443ccbe55ba8'
    assert len(current) == 211
    assert keys == {Path(r['path']).name.removesuffix('.xz') for r in current}
    for protocol in ('online', 'offline'):
        path = ROOT / f'tasks/solver/{protocol}/maxsat-mse/tests/reference.json'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == '5b112ce3b4f049e05a4295e4bceb62e7e4b64c5df0bfaf0bb8f54a133861361b'
        assert keys == set(json.loads(path.read_text())['instances'])
    history = ROOT / 'assets/data/solver/history/maxsat-mse-canonical98-261030'
    old = json.loads((history / 'files.json').read_text())['files']
    assert len(old) == 98
    assert hashlib.sha256((history / 'files.json').read_bytes()).hexdigest() == '6b05630fc35b918aaf60c2c2c60661b0eb1777aecd81fcac34bf5abaa6ad5f89'
    assert json.loads((history / 'recipe.json').read_text())['format'] == 'official_maxsat_generator'
    assert content_digest(old) != content_digest(rows)


def synthetic_version(root, version=VERSION):
    (root / 'suites').mkdir()
    (root / 'suites/tasks.json').write_text(json.dumps({'tasks': [{'id': 'maxsat-mse', 'track': 'solver'}]}))
    directory = root / 'assets/data/solver'
    directory.mkdir(parents=True)
    oldrow = {'path': 'tests/instances/ex001.wcnf.xz', 'bytes': 3, 'mode': '0644', 'sha256': '1' * 64}
    old = {'id': NAME, 'type': 'data', 'content_version': 'frozen-inputs-261029-v1',
           'content_digest': content_digest([oldrow]), 'recipe_format': 'official_maxsat_generator',
           'source_input': {'id': 'obsolete98'}, 'dependencies': ['obsolete-builder'],
           'harbor_verified': True, 'verification_scope': {'historical98': 'preserved'}}
    (root / 'assets/images.json').write_text(json.dumps({'images': [old]}))
    row = dict(oldrow, bytes=4, sha256='2' * 64)
    (directory / (NAME + '-files.json')).write_text(json.dumps({'files': [row]}))
    (directory / (NAME + '-recipe.json')).write_text(json.dumps({
        'format': 'frozen_directory', 'content_version': version,
        'input_id': 'original211-explicit-rootfs', 'history': [{'content_version': 'canonical98-history'}]}))
    return old


def test_versioned_input_uses_separate_cache_identity_and_retains_historical_acceptance(tmp_path):
    old = synthetic_version(tmp_path)
    row = next(r for r in product_patch(tmp_path) if r['id'] == NAME)
    assert row['content_version'] == VERSION
    assert row['content_digest'] != old['content_digest']
    assert row['previous_content_digest'] == old['content_digest']
    assert row['content_verification_refresh_required'] is True
    assert row['harbor_verified'] is True
    assert row['verification_scope'] == old['verification_scope']
    assert row['data_history'] == [{'content_version': 'canonical98-history'}]
    assert row['dependencies'] == [] and 'source_input' not in row
    (tmp_path / 'assets/images.json').write_text(json.dumps({'images': [row]}))
    assert next(r for r in product_patch(tmp_path) if r['id'] == NAME) == row


@pytest.mark.parametrize('version', ['../canonical98', '/tmp/cache', '', 'uppercase/V1'])
def test_content_version_cannot_escape_cache_namespace(tmp_path, version):
    synthetic_version(tmp_path, version)
    with pytest.raises(ValueError, match='safe cache component'):
        product_patch(tmp_path)
