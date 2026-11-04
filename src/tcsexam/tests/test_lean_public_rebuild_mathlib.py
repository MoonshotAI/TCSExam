"""Check pinned Lean dependencies and the materials shipped with the base recipe."""
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from tcsexam.checks import internal_reference_categories

ROOT = Path(__file__).resolve().parents[3]
THIRD_PARTY = ROOT / 'docs/licenses/third-party'
BASE = ROOT / 'assets/environments/lean-base'
MATERIALS = THIRD_PARTY / 'lean-public-rebuild-mathlib-materials.json'
LAKE_MANIFEST = BASE / 'mathlib-lake-manifest.json'
CACHE_MANIFEST = THIRD_PARTY / 'lean-public-rebuild-evidence/mathlib-cache-ltar-manifest.jsonl'


def load(path):
    return json.loads(path.read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def has_complete_cache_coverage(materials, entries):
    cache = materials['cache']
    return (len(entries) == cache['entry_count']
            and len({row['path'] for row in entries}) == len(entries)
            and len({row['cache_key'] for row in entries}) == len(entries)
            and sum(row['bytes'] for row in entries) == cache['total_bytes']
            and sha256(CACHE_MANIFEST) == cache['manifest_sha256']
            and all(row['bytes'] > 0
                    and re.fullmatch(r'[0-9a-f]{16}', row['cache_key'])
                    and re.fullmatch(r'[0-9a-f]{64}', row['sha256'])
                    and PurePosixPath(row['path']).name == row['cache_key'] + '.ltar'
                    and row['source_url'] == cache['source_container_url'] + '/f/' + row['cache_key'] + '.ltar'
                    for row in entries))


def test_lake_components_match_fixed_commits_sources_and_license_bytes():
    materials = load(MATERIALS)
    manifest = load(LAKE_MANIFEST)
    expected = {'mathlib': materials['mathlib_commit']}
    expected.update({p['name']: p['rev'] for p in manifest['packages']})
    components = {c['name']: c for c in materials['components']}
    assert len(components) == len(materials['components']) == len(expected)
    assert set(components) == set(expected)
    assert materials['lean_toolchain'] in (BASE / 'Dockerfile').read_text()
    assert expected['mathlib'] in (BASE / 'Dockerfile').read_text()
    for name, commit in expected.items():
        component = components[name]
        assert component['commit'] == commit
        assert re.fullmatch(r'[0-9a-f]{40}', commit)
        assert component['commit_url'] == component['repository'] + '/commit/' + commit
        assert commit in component['source_archive_url']
        if name != 'mathlib':
            package = next(p for p in manifest['packages'] if p['name'] == name)
            assert package['url'].removesuffix('.git') == component['repository']
        license_record = component['license']
        assert license_record['id'] == ('MIT' if name == 'Cli' else 'Apache-2.0')
        assert commit in license_record['url']
        license_file = THIRD_PARTY / license_record['local_file']
        assert license_file.stat().st_size == license_record['bytes']
        assert sha256(license_file) == license_record['sha256']
        packaged = BASE / 'lean-components' / name
        assert (packaged / 'LICENSE').read_bytes() == license_file.read_bytes()
        source = load(packaged / 'source.json')
        assert source['name'] == name and source['commit'] == commit
        assert source['repository'] == component['repository']
        assert source['license']['sha256'] == license_record['sha256']
        assert source['source_archive_url'] == component['source_archive_url']


def test_lake_material_checksum_inventory_is_complete_and_copied_into_image():
    directory = BASE / 'lean-components'
    components = {c['name'] for c in load(MATERIALS)['components']}
    checksums = {}
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        checksum, name = line.split('  ', 1)
        assert name not in checksums
        assert sha256(directory / name) == checksum
        checksums[name] = checksum
    assert set(checksums) == {'README.md'} | {
        name + '/' + file for name in components for file in ('LICENSE', 'source.json')}
    dockerfile = (BASE / 'Dockerfile').read_text()
    assert 'COPY lean-components/ /usr/share/doc/tcsexam/lean-components/' in dockerfile
    assert 'cd /usr/share/doc/tcsexam/lean-components' in dockerfile
    assert 'sha256sum -c SHA256SUMS' in dockerfile


def test_cache_inventory_binds_every_archive_to_hash_size_and_public_source():
    materials = load(MATERIALS)
    entries = [json.loads(line) for line in CACHE_MANIFEST.read_text().splitlines()]
    assert has_complete_cache_coverage(materials, entries)
    assert CACHE_MANIFEST.stat().st_size == materials['cache']['manifest_bytes']
    assert not has_complete_cache_coverage(materials, entries[:-1])
    changed = copy.deepcopy(entries)
    changed[0]['source_url'] = 'https://example.org/unpinned.ltar'
    assert not has_complete_cache_coverage(materials, changed)
    changed = copy.deepcopy(entries)
    changed[0]['bytes'] += 1
    assert not has_complete_cache_coverage(materials, changed)


def test_graphviz_keeps_its_separate_license_and_pinned_corresponding_source():
    materials = load(MATERIALS)
    graphviz = materials['proofwidgets_graphviz']
    manifest = load(BASE / 'graphviz-epl/source-manifest.json')
    proofwidgets = next(c for c in materials['components'] if c['name'] == 'proofwidgets')
    assert graphviz['proofwidgets_commit'] == manifest['proofwidgets']['commit'] == proofwidgets['commit']
    assert graphviz['program']['license'] == manifest['graphviz']['license'] == 'EPL-2.0'
    assert graphviz['program']['version'] == manifest['graphviz']['version'] == '15.0.0'
    assert graphviz['wrapper']['license'] == manifest['wrapper']['license'] == 'Apache-2.0'
    assert graphviz['wrapper']['wrapper_license_does_not_cover_graphviz'] is True
    assert graphviz['wrapper']['commit'] == manifest['wrapper']['commit']
    license_record = graphviz['program']['license_text']
    license_file = THIRD_PARTY / license_record['local_file']
    assert license_file.read_text().startswith('Eclipse Public License - v 2.0\n')
    assert sha256(license_file) == license_record['sha256']
    assert (BASE / 'graphviz-epl/EPL-2.0.txt').read_bytes() == license_file.read_bytes()
    sources = graphviz['corresponding_source']
    for key, prefix in [('graphviz', 'graphviz_archive'), ('wrapper', 'wrapper_and_build_source')]:
        archive = manifest[key]['archive']
        assert archive['official_url'] == sources[prefix + '_url']
        assert archive['bytes'] == sources[prefix + '_bytes'] > 0
        for algorithm, length in [('sha256', 64), ('sha512', 128)]:
            assert archive[algorithm] == sources[prefix + '_' + algorithm]
            assert re.fullmatch(r'[0-9a-f]{' + str(length) + '}', archive[algorithm])
    port = sources['port_file']
    assert sha256(THIRD_PARTY / port['local_file']) == port['sha256']
    assert manifest['graphviz']['archive']['sha512'] in (THIRD_PARTY / port['local_file']).read_text()
    dockerfile = (BASE / 'Dockerfile').read_text()
    assert 'COPY graphviz-epl/ /usr/share/doc/tcsexam/graphviz-epl/' in dockerfile
    offer = (BASE / 'graphviz-epl/SOURCE-OFFER.md').read_text()
    assert 'EPL-2.0' in offer and 'source/' in offer


def test_material_metadata_has_no_internal_endpoints():
    for path in (MATERIALS, CACHE_MANIFEST, LAKE_MANIFEST):
        assert internal_reference_categories(path.read_text()) == []
