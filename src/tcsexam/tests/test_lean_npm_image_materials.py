import hashlib
import json
from pathlib import Path

from tcsexam.checks import internal_reference_categories


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "assets/environments/lean-base"
NPM = BASE / "proofwidgets-npm"
THIRD = ROOT / "docs/licenses/third-party"
EVIDENCE = THIRD / "proofwidgets-npm-license-materials.json"
MATERIALS = THIRD / "lean-public-rebuild-mathlib-materials.json"
STATUS = BASE / "rebuild-status.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    return json.loads(path.read_text())


GAP_IDS = {"victory_vendor_root_mit_notice", "isaacs_cliui_vendored_eastasianwidth_notice"}


def missing_ids(record):
    return {
        item if isinstance(item, str) else item["id"]
        for item in record["missing_evidence"]
    }


def has_complete_gap_evidence():
    victory = load_json(NPM / "packages/victory-vendor/source.json")
    supplementary = victory.get("supplementary_project_notice")
    if not supplementary or not all(
        supplementary.get(field) for field in ("url", "ref", "sha256", "bytes", "installed_file")
    ):
        return False
    if not (NPM / "packages/victory-vendor" / supplementary["installed_file"]).is_file():
        return False
    cliui = load_json(NPM / "packages/@isaacs/cliui/source.json")
    if "vendored_modules_file" in cliui:
        modules = load_json(NPM / "packages/@isaacs/cliui" / cliui["vendored_modules_file"])["modules"]
    else:
        modules = cliui.get("vendored_modules", [])
    if len(modules) != 7:
        return False
    east = [module for module in modules if module["module"] == "eastasianwidth"]
    if len(east) != 1:
        return False
    for module in modules:
        notice = module.get("notice", {})
        if not all(notice.get(field) for field in ("url", "sha256", "bytes", "installed_file")):
            return False
        if not (NPM / "packages/@isaacs/cliui" / notice["installed_file"]).is_file():
            return False
        if not module.get("version") or not module.get("source"):
            return False
    return True


def test_two_boundary_gaps_have_attributed_supplemental_evidence():
    assert has_complete_gap_evidence() is True
    victory = load_json(NPM / "packages/victory-vendor/source.json")
    assert victory["license"] == "MIT AND ISC"
    assert len(victory["original_notice_files"]) == 13
    assert victory["root_license_review"]["root_license_present"] is False
    supplementary = victory["supplementary_project_notice"]
    assert supplementary["url"] == "https://registry.npmjs.org/victory/-/victory-36.9.2.tgz"
    assert supplementary["ref"] == "victory@36.9.2 / package/LICENSE.txt"
    assert supplementary["archive_sha256"] == "6e833af3569663d7bb85154d8b7fe6bc46a1d0453e3bba3570526f913413ff65"
    assert supplementary["archive_bytes"] == 444489
    assert supplementary["sha256"] == "34dee5fd5e5cc756efb5ad4d64652bce719bdf5e900ca5d7538253e737930bc4"
    assert supplementary["bytes"] == 1626
    license_path = NPM / "packages/victory-vendor" / supplementary["installed_file"]
    assert sha256(license_path) == supplementary["sha256"]
    assert license_path.stat().st_size == 1626
    assert "Formidable Labs" in license_path.read_text()
    assert "not an original file from the victory-vendor archive" in supplementary["origin"]
    manifest = load_json(NPM / "source-manifest.json")
    victory_row = next(row for row in manifest["packages"] if row["lock_path"] == "node_modules/victory-vendor")
    assert victory_row["has_supplementary_notice"] is True
    assert victory_row["original_notice_count"] == 13

    cliui = load_json(NPM / "packages/@isaacs/cliui/source.json")
    review = cliui["vendored_review"]
    assert review["module_count"] == 7
    assert review["all_modules_mapped"] is True
    assert review["reused_original_notice_count"] == 6
    assert review["supplemental_fixed_cliui_source_notice_count"] == 1
    mapping = load_json(NPM / "packages/@isaacs/cliui" / cliui["vendored_modules_file"])
    modules = mapping["modules"]
    assert [module["module"] for module in modules] == [
        "ansi-regex", "ansi-styles", "eastasianwidth", "emoji-regex",
        "string-width", "strip-ansi", "wrap-ansi",
    ]
    expected_versions = {
        "ansi-regex": "6.2.2", "ansi-styles": "6.2.3", "eastasianwidth": "0.3.0",
        "emoji-regex": "10.6.0", "string-width": "7.2.0",
        "strip-ansi": "7.2.0", "wrap-ansi": "9.0.2",
    }
    for module in modules:
        name = module["module"]
        notice = module["notice"]
        assert module["version"] == expected_versions[name]
        assert module["vendored_paths"] == [
            f"dist/commonjs/{name}/index.js", f"dist/esm/{name}/index.js",
        ]
        assert module["cliui_source"]["commit"] == "b33b76c344fc3e76cca1a6e8d8cf25ae09f33fc0"
        assert module["cliui_source"]["license_sha256"] == notice["sha256"]
        installed = NPM / "packages/@isaacs/cliui" / notice["installed_file"]
        assert installed.stat().st_size == notice["bytes"]
        assert sha256(installed) == notice["sha256"]
        if name == "eastasianwidth":
            assert notice["kind"] == "supplemental_fixed_cliui_source"
            assert notice["ref"] == "b33b76c344fc3e76cca1a6e8d8cf25ae09f33fc0"
            assert notice["sha256"] == "94aa6016fb9d436508366433e9caba061443ca58f4c7eb515caec7badf90ae5a"
            assert notice["bytes"] == 1043
            assert "Copyright komagata" in installed.read_text()
            assert "not an original npm dist NOTICE" in notice["origin"]
            assert module["source"]["archive_sha256"] == "8b52fac4f929a5de61bbef98594907848b8587c46b7417abe4e66acf65a38552"
            assert module["source"]["package_json_sha256"] == "32ffd87591938680573e7ccf18e507d7e0c79e0e25bbc15d77288d097b69690e"
            assert notice["source_lock_path"] is None
        else:
            independent = load_json(NPM / "packages" / name / "source.json")
            original = independent["original_notice_files"][0]
            assert notice["kind"] == "reused_fixed_lock_original_notice"
            assert notice["source_lock_path"] == independent["lock_path"]
            assert installed.read_bytes() == (NPM / "packages" / name / original["installed_file"]).read_bytes()
            assert "not an original cliui npm archive NOTICE" in notice["origin"]


def test_lock_and_all_387_source_records_match_exactly():
    lock = load_json(NPM / "package-lock.json")
    evidence = load_json(EVIDENCE)
    manifest = load_json(NPM / "source-manifest.json")
    assert (NPM / "package-lock.json").stat().st_size == 172140
    assert sha256(NPM / "package-lock.json") == evidence["lock_file_sha256"]
    assert len(lock["packages"]) - 1 == len(evidence["packages"]) == 387
    assert manifest["all_lock_entries_mapped"] is True
    complete = has_complete_gap_evidence()
    assert manifest["npm_notice_materials_ready"] is complete
    if complete:
        assert manifest["missing_evidence"] == []
    else:
        assert missing_ids(manifest) == GAP_IDS
    assert manifest["license_conflicts"] == []
    expected = {package["lock_path"]: package for package in evidence["packages"]}
    assert {row["lock_path"] for row in manifest["packages"]} == set(lock["packages"]) - {""}
    assert len(manifest["packages"]) == 387
    for row in manifest["packages"]:
        lock_path = row["lock_path"]
        package = expected[lock_path]
        source = load_json(NPM / row["directory"] / "source.json")
        assert source["lock_path"] == lock_path
        assert source["name"] == package["name"]
        assert source["version"] == package["version"] == row["version"]
        assert source["license"] == package["license"]
        assert source["package_license"] == package["package_license"]
        assert source["author"] == package["author"]
        assert source["dev_dependency"] == package["dev"] == row["dev_dependency"]
        assert source["lock_entry"] == lock["packages"][lock_path]
        archive = source["source_archive"]
        assert archive["official_url"] == package["resolved"] == lock["packages"][lock_path]["resolved"]
        assert archive["integrity"] == package["integrity"] == lock["packages"][lock_path]["integrity"]
        assert archive["integrity_verified_in_prior_review"] is True
        assert archive["sha256"] == package["sha256"]
        assert archive["bytes"] == package["bytes"]
        assert archive["installed_in_image"] is False
        assert archive["revalidated_for_this_integration"] is False
        assert source["payload_linkage"] == "not_asserted"
        assert source["node_modules_or_package_binary_installed"] is False
        assert source["name_basis"] == package.get("name_basis")


def test_all_notice_files_match_evidence_and_keep_origin_limitations():
    evidence = load_json(EVIDENCE)
    manifest = load_json(NPM / "source-manifest.json")
    original_count = 0
    supplementary_count = 0
    standard_count = 0
    no_original_count = 0
    for row in manifest["packages"]:
        package = next(p for p in evidence["packages"] if p["lock_path"] == row["lock_path"])
        directory = NPM / row["directory"]
        source = load_json(directory / "source.json")
        if not package["original_notice_files"]:
            no_original_count += 1
        assert len(source["original_notice_files"]) == len(package["original_notice_files"])
        for expected, actual in zip(package["original_notice_files"], source["original_notice_files"]):
            installed = directory / actual["installed_file"]
            assert actual["path"] == expected["path"]
            assert actual["origin"] == "Exact fixed npm archive notice text."
            assert installed.stat().st_size == expected["bytes"]
            assert sha256(installed) == expected["sha256"]
            assert installed.read_bytes() == (THIRD / expected["text_file"]).read_bytes()
            original_count += 1
        expected_supplement = package.get("supplementary_project_notice")
        actual_supplement = source["supplementary_project_notice"]
        if package["lock_path"] == "node_modules/victory-vendor":
            assert expected_supplement is None
            assert actual_supplement["sha256"] == "34dee5fd5e5cc756efb5ad4d64652bce719bdf5e900ca5d7538253e737930bc4"
            assert actual_supplement["bytes"] == 1626
            assert "not an original file from the victory-vendor archive" in actual_supplement["origin"]
            supplementary_count += 1
        else:
            assert bool(actual_supplement) == bool(expected_supplement)
            if expected_supplement:
                assert actual_supplement["url"] == expected_supplement["url"]
                assert actual_supplement["ref"] == expected_supplement["ref"]
                assert actual_supplement["sha256"] == expected_supplement["sha256"]
                assert actual_supplement["origin"].startswith("Supplemental same-project notice")
                assert "not represented as an original file" in actual_supplement["origin"]
                assert source["notice_basis"] == package["notice_basis"]
                installed = directory / actual_supplement["installed_file"]
                assert installed.read_bytes() == (THIRD / expected_supplement["text_file"]).read_bytes()
                supplementary_count += 1
        expected_standard = package.get("standard_license_text")
        actual_standard = source["standard_license_text"]
        assert bool(actual_standard) == bool(expected_standard)
        if expected_standard:
            assert package["lock_path"] == "node_modules/is-reference"
            assert actual_standard["url"] == "https://spdx.org/licenses/MIT.txt"
            assert "not an upstream package NOTICE" in actual_standard["origin"]
            assert "not a fabricated upstream copyright notice" in source["notice_basis"]
            installed = directory / actual_standard["installed_file"]
            assert installed.read_bytes() == (THIRD / expected_standard["text_file"]).read_bytes()
            standard_count += 1
        assert source["original_notice_files"] or source["supplementary_project_notice"] or source["standard_license_text"]
    vendored = load_json(NPM / "packages/@isaacs/cliui/vendored-modules.json")["modules"]
    supplementary_count += sum(module["notice"]["kind"] == "supplemental_fixed_cliui_source" for module in vendored)
    assert sum(module["notice"]["kind"] == "reused_fixed_lock_original_notice" for module in vendored) == 6
    assert original_count == manifest["original_notice_file_count"] == 364
    assert supplementary_count == manifest["supplementary_notice_count"] == 44
    assert standard_count == manifest["standard_license_text_count"] == 1
    assert no_original_count == manifest["packages_without_original_notice_count"] == 43


def test_dev_optional_platform_and_nested_lock_entries_are_preserved():
    manifest = load_json(NPM / "source-manifest.json")
    dev_count = 0
    optional_count = 0
    platform_count = 0
    for row in manifest["packages"]:
        source = load_json(NPM / row["directory"] / "source.json")
        lock_entry = source["lock_entry"]
        dev_count += source["dev_dependency"]
        optional_count += bool(lock_entry.get("optional"))
        platform_count += bool(lock_entry.get("os") or lock_entry.get("cpu"))
        assert row["optional"] == bool(lock_entry.get("optional"))
        assert row["os"] == lock_entry.get("os")
        assert row["cpu"] == lock_entry.get("cpu")
    assert dev_count == manifest["dev_dependency_count"] == 106
    assert manifest["non_dev_dependency_count"] == 281
    assert optional_count == manifest["optional_package_count"] == 26
    assert platform_count == manifest["platform_specific_package_count"] == 26
    optional = load_json(NPM / "packages/@rollup/rollup-linux-x64-gnu/source.json")
    assert optional["lock_entry"]["optional"] is True
    assert optional["lock_entry"]["os"] == ["linux"]
    assert optional["lock_entry"]["cpu"] == ["x64"]
    assert optional["lock_entry"]["libc"] == ["glibc"]
    nested = NPM / "packages/@react-three/fiber/node_modules/zustand/source.json"
    assert nested.is_file()
    assert load_json(nested)["lock_path"] == "node_modules/@react-three/fiber/node_modules/zustand"
    webgl = load_json(NPM / "packages/webgl-constants/source.json")
    assert webgl["license"] is None
    assert "license" not in webgl["lock_entry"]
    assert "do not declare a license" in webgl["license_metadata_note"]
    assert (NPM / "packages/webgl-constants/notices/original/package/LICENSE").read_text().startswith("MIT License\n")
    limitations = manifest["metadata_limitations"]
    assert len(limitations) == 1
    assert limitations[0]["lock_path"] == "node_modules/webgl-constants"
    assert limitations[0]["missing_evidence"] is False
    assert limitations[0]["license_conflict"] is False
    assert not [path for path in NPM.rglob("*") if path.is_file() and path.suffix in {".js", ".wasm", ".tgz"}]


def test_checksums_and_docker_entry_cover_all_npm_materials():
    dockerfile = (BASE / "Dockerfile").read_text()
    assert "COPY proofwidgets-npm/ /usr/share/doc/tcsexam/proofwidgets-npm/" in dockerfile
    assert dockerfile.count("sha256sum -c SHA256SUMS") == 4
    assert sha256(BASE / "NOTICE.md") in dockerfile
    assert "/usr/share/doc/tcsexam/proofwidgets-npm/" in (BASE / "NOTICE.md").read_text()
    entries = {}
    for line in (NPM / "SHA256SUMS").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        entries[relative] = digest
    files = {
        path.relative_to(NPM).as_posix(): path
        for path in NPM.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    assert entries.keys() == files.keys()
    assert len(entries) == (806 if has_complete_gap_evidence() else 797)
    for relative, path in files.items():
        assert entries[relative] == sha256(path)


def test_npm_notice_manifest_preserves_distribution_scope():
    manifest = load_json(NPM / "source-manifest.json")
    assert manifest["npm_notice_materials_ready"] is has_complete_gap_evidence()
    assert manifest["missing_evidence"] == []
    assert manifest["license_conflicts"] == []
    assert len(manifest["packages"]) == 387
    status = load_json(STATUS)
    assert str(NPM.relative_to(ROOT)) in status["source_materials"]
    assert "candidate_validation" not in status



def test_public_npm_materials_have_no_internal_references():
    paths = [BASE / "Dockerfile", BASE / "NOTICE.md", MATERIALS, STATUS]
    paths.extend(path for path in NPM.rglob("*") if path.is_file())
    for path in paths:
        assert internal_reference_categories(path.read_text()) == []
