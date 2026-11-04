"""Verify fixed system-source descriptors without requiring execution reports."""
import copy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote, urlsplit

from tcsexam.checks import internal_reference_categories

ROOT = Path(__file__).resolve().parents[3]
THIRD_PARTY = ROOT / 'docs/licenses/third-party'
MATERIALS = THIRD_PARTY / 'lean-public-rebuild-system-materials.json'
DESCRIPTORS = THIRD_PARTY / 'lean-public-rebuild-source-descriptors'


def load():
    return json.loads(MATERIALS.read_text())


def recorded_binaries(materials):
    records = {}
    for source in materials['source_packages']:
        for binary in source['binary_packages']:
            key = binary['package'], binary['version'], binary['architecture']
            assert key not in records
            assert binary['version'] == source['source_version']
            records[key] = source
    return records


def complete_descriptors(materials):
    return (bool(materials['source_packages']) and not materials['missing']
            and all(source['verified_dsc'] is True
                    and (THIRD_PARTY / source['dsc_file']).is_file()
                    and hashlib.sha256((THIRD_PARTY / source['dsc_file']).read_bytes()).hexdigest() == source['dsc_sha256']
                    for source in materials['source_packages']))


def test_each_binary_has_one_pinned_corresponding_source_version():
    materials = load()
    records = recorded_binaries(materials)
    assert materials['covered_binary_package_count'] == len(records)
    assert materials['listed_binary_package_count'] == len(records)
    assert materials['source_version_count'] == len(materials['source_packages'])
    assert len({(r['source_package'], r['source_version']) for r in materials['source_packages']}) == len(materials['source_packages'])
    assert materials['missing_source_descriptor_count'] == len(materials['missing']) == 0


def test_source_descriptors_preserve_signatures_hashes_and_exact_file_lists():
    materials = load()
    paths = set()
    source_file_count = 0
    for source in materials['source_packages']:
        path = (THIRD_PARTY / source['dsc_file']).resolve()
        assert path.parent == DESCRIPTORS.resolve()
        assert path not in paths
        paths.add(path)
        data = path.read_bytes()
        assert len(data) == source['dsc_bytes']
        assert hashlib.sha256(data).hexdigest() == source['dsc_sha256']
        assert urlsplit(source['dsc_url']).netloc == 'launchpad.net'
        assert '/+archive/primary/+sourcefiles/' in urlsplit(source['dsc_url']).path
        assert urlsplit(source['dsc_effective_url']).netloc == 'launchpadlibrarian.net'
        text = data.decode('utf-8')
        assert re.search(rf'(?m)^Source: {re.escape(source["source_package"])}$', text)
        assert re.search(rf'(?m)^Version: {re.escape(source["source_version"])}$', text)
        signature = (text.startswith('-----BEGIN PGP SIGNED MESSAGE-----\n')
                     and '-----BEGIN PGP SIGNATURE-----' in text
                     and text.rstrip().endswith('-----END PGP SIGNATURE-----'))
        assert source['openpgp_signature_retained'] is signature
        package_list = re.search(r'(?ms)^Package-List:\n(.*?)(?=^[A-Z][A-Za-z0-9-]*:)', text)
        assert package_list
        assert {b['package'] for b in source['binary_packages']} <= {
            line.split()[0] for line in package_list.group(1).splitlines()}
        checksums = re.search(r'(?ms)^Checksums-Sha256:\n(.*?)(?=^[A-Z][A-Za-z0-9-]*:)', text)
        assert checksums
        expected = []
        for line in checksums.group(1).splitlines():
            match = re.fullmatch(r' ([0-9a-f]{64}) ([0-9]+) (.+)', line)
            assert match
            checksum, size, filename = match.groups()
            expected.append({'filename': filename, 'bytes': int(size), 'sha256': checksum})
        assert [{k: row[k] for k in ('filename', 'bytes', 'sha256')}
                for row in source['source_files']] == expected
        for row in source['source_files']:
            assert row['url'] == source['dsc_url'].rsplit('/', 1)[0] + '/' + quote(row['filename'], safe='+')
        source_file_count += len(expected)
    assert paths == set(DESCRIPTORS.glob('*.dsc'))
    assert materials['verified_source_descriptor_count'] == len(paths)
    assert materials['source_file_metadata_count'] == source_file_count


def test_descriptor_coverage_requires_actual_hashes_and_preserves_limits():
    materials = load()
    assert complete_descriptors(materials)
    assert materials['complete'] is True
    changed = copy.deepcopy(materials)
    changed['source_packages'][0]['dsc_sha256'] = '0' * 64
    assert not complete_descriptors(changed)
    changed = copy.deepcopy(materials)
    changed['source_packages'][0]['verified_dsc'] = False
    assert not complete_descriptors(changed)
    # Retaining signed descriptors does not claim independent signature verification.
    assert materials['openpgp_verified'] is False
    assert materials['full_source_archives_downloaded'] is False


def test_public_source_metadata_has_no_internal_endpoints():
    assert internal_reference_categories(MATERIALS.read_text()) == []
