import hashlib
import json
from pathlib import Path

from tcsexam.checks import internal_reference_categories


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "assets/environments/lean-base"
LAKE = BASE / "lean-components"
BROWSER = BASE / "browser-components"
GRAPHVIZ = BASE / "graphviz-epl"
THIRD = ROOT / "docs/licenses/third-party"
MATERIALS = THIRD / "lean-public-rebuild-mathlib-materials.json"
EMBEDDED = THIRD / "proofwidgets-embedded-components.json"
STATUS = BASE / "rebuild-status.json"


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_json(path):
    return json.loads(path.read_text())


def checksum_entries(base):
    result = {}
    for line in (base / "SHA256SUMS").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        result[relative] = digest
    return result


def test_nine_lake_licenses_preserve_component_identity_sources_and_notice_audit():
    materials = load_json(MATERIALS)
    expected = {component["name"]: component for component in materials["components"]}
    actual = {path.name for path in LAKE.iterdir() if path.is_dir()}
    assert actual == expected.keys()
    assert len(actual) == 9
    for name, component in expected.items():
        directory = LAKE / name
        source = load_json(directory / "source.json")
        assert source["name"] == name
        assert source["repository"] == component["repository"]
        assert source["commit"] == component["commit"] == source["actual_candidate_head"]
        assert source["source_archive_url"] == component["source_archive_url"]
        assert source["source_archive_content_independently_verified"] is False
        license_record = component["license"]
        installed = directory / "LICENSE"
        assert installed.stat().st_size == license_record["bytes"]
        assert sha256(installed) == license_record["sha256"]
        assert installed.read_bytes() == (THIRD / license_record["local_file"]).read_bytes()
        assert source["license"]["url"] == license_record["url"]
        notice = source["independent_notice"]
        assert notice["present"] is False
        assert notice["status"] == "no_independent_notice_found"
        assert notice["tree_http_status"] == 200
        assert notice["tree_truncated"] is False
        assert component["commit"] in notice["tree_api"]
        if name in {"mathlib", "batteries"}:
            assert notice["non_notice_copyright_files"][0]["path"] == ".vscode/copyright.code-snippets"
            assert "not an independent NOTICE" in notice["non_notice_copyright_files"][0]["role"]
        else:
            assert notice["non_notice_copyright_files"] == []
        assert not list(directory.glob("NOTICE*"))


def test_expat_and_emscripten_notices_keep_payload_and_build_input_scope():
    expat = load_json(BROWSER / "expat/source.json")
    assert expat["version_from_fixed_vcpkg_port"] == "2.8.1"
    assert expat["license"] == "MIT"
    assert expat["source_archive_content_independently_verified"] is False
    assert "confirms Expat is linked" in expat["payload_evidence"]
    assert "runtime version function was not executed" in expat["payload_evidence"]
    license_record = expat["license_text"]
    assert sha256(BROWSER / "expat/LICENSE") == license_record["sha256"]
    emscripten = load_json(BROWSER / "emscripten/source.json")
    assert emscripten["version_from_fixed_build_script"] == "6.0.0"
    assert emscripten["source_archive_content_independently_verified"] is False
    assert "exact linked runtime subset is not enumerated" in emscripten["coverage_scope"]
    assert len(emscripten["installed_notices"]) == 3
    for relative, record in zip(emscripten["installed_notices"], emscripten["license_texts"]):
        installed = BROWSER / "emscripten" / relative
        assert installed.stat().st_size == record["bytes"]
        assert sha256(installed) == record["sha256"]
        assert installed.read_bytes() == (THIRD / record["text_file"]).read_bytes()


def test_penrose_46_crates_have_exact_sources_and_83_scoped_notice_files():
    expected = load_json(EMBEDDED)["penrose_optimizer"]
    actual = load_json(BROWSER / "penrose-optimizer/source.json")
    assert actual["verified_crate_archives"] == actual["total_crate_archives"] == 46
    assert actual["original_notice_file_count"] == 77
    assert actual["supplementary_notice_file_count"] == 6
    assert actual["source_archive_content_independently_verified"] is False
    assert "not a claim all are linked" in actual["coverage_scope"]
    assert not list((BROWSER / "penrose-optimizer").rglob("*.crate"))
    crates = {crate["name"]: crate for crate in expected["crates"]}
    assert len(crates) == 46
    original_count = 0
    supplemental_count = 0
    for row in actual["crates"]:
        name = row["name"]
        crate = crates[name]
        directory = BROWSER / "penrose-optimizer" / row["directory"]
        source = load_json(directory / "source.json")
        assert source["version"] == crate["version"]
        assert source["license"] == crate["license"]
        assert source["source_url"] == crate["source_url"]
        assert source["checksum_sha256"] == crate["checksum_sha256"]
        assert source["bytes"] == crate["bytes"]
        assert source["archive_verified"] is True
        assert source["payload_linkage"] == "not_asserted"
        assert "does not assert linkage into wasm32" in source["inclusion_scope"]
        assert source["target_note"] == crate.get("target_note")
        for notice in source["original_notice_files"]:
            installed = directory / notice["installed_file"]
            assert "notices/original/" in notice["installed_file"]
            assert installed.stat().st_size == notice["bytes"]
            assert sha256(installed) == notice["sha256"]
            assert installed.read_bytes() == (THIRD / notice["text_file"]).read_bytes()
            original_count += 1
        supplemental = source["supplementary_project_notice"]
        if supplemental:
            installed = directory / supplemental["installed_file"]
            assert "notices/supplementary/" in supplemental["installed_file"]
            assert sha256(installed) == supplemental["sha256"]
            assert installed.read_bytes() == (THIRD / supplemental["text_file"]).read_bytes()
            assert "not represented as an originally shipped historical file" in source["notice_basis"]
            supplemental_count += 1
    assert original_count == 77
    assert supplemental_count == 6
    cargo_lock = BROWSER / "penrose-optimizer/build/Cargo.lock"
    assert sha256(cargo_lock) == expected["cargo_lock_sha256"]


def test_browser_manifest_distinguishes_payload_upstream_and_conservative_superset():
    manifest = load_json(BROWSER / "source-manifest.json")
    assert manifest["targeted_materials_ready"] is True
    assert manifest["overall_nested_review_complete"] is False
    assert manifest["generated_javascript_or_wasm_modified"] is False
    assert len(manifest["pending"]) == 3
    assert manifest["components"]["expat"]["payload_linkage"] == "linked_in_reviewed_graphviz_payload"
    assert "not enumerated" in manifest["components"]["emscripten"]["payload_linkage"]
    assert "individual crates not asserted" in manifest["components"]["penrose_optimizer"]["payload_linkage"]
    for item in manifest["verified_payload_files"]:
        assert len(bytes.fromhex(item["sha256"])) == 32
        assert item["bytes"] > 0
        assert manifest["proofwidgets_commit"] in item["source_url"]
        assert item["source_url"].endswith("/widget/" + item["path"])
        assert item["candidate_matches_fixed_upstream"] is True
        assert item["embedded_wasm_markers_from_reviewed_payload"] is True
    assert "rather than copying the Graphviz EPL rule" in manifest["source_policy"]


def test_all_new_material_checksums_and_docker_context_preserve_graphviz_28(prepared_lean_source_inputs):
    dockerfile = (BASE / "Dockerfile").read_text()
    assert "COPY lean-components/ /usr/share/doc/tcsexam/lean-components/" in dockerfile
    assert "COPY browser-components/ /usr/share/doc/tcsexam/browser-components/" in dockerfile
    assert "COPY graphviz-epl/ /usr/share/doc/tcsexam/graphviz-epl/" in dockerfile
    assert sha256(BASE / "NOTICE.md") in dockerfile
    assert dockerfile.count("sha256sum -c SHA256SUMS") == 4
    for base, count in ((LAKE, 19), (BROWSER, 142), (GRAPHVIZ, 34)):
        entries = checksum_entries(base)
        files = {
            path.relative_to(base).as_posix(): path
            for path in base.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS"
        }
        assert entries.keys() == files.keys()
        assert len(entries) == count
        for relative, path in files.items():
            assert entries[relative] == sha256(path)
    assert not list(LAKE.rglob("*.js")) + list(BROWSER.rglob("*.js"))
    assert not list(LAKE.rglob("*.wasm")) + list(BROWSER.rglob("*.wasm"))


def test_material_directories_are_declared_as_build_inputs():
    status = load_json(STATUS)
    for directory in (LAKE, BROWSER, GRAPHVIZ):
        assert str(directory.relative_to(ROOT)) in status["source_materials"]
        assert (directory / "SHA256SUMS").is_file()
    assert status["dockerfile"] == str((BASE / "Dockerfile").relative_to(ROOT))



def test_new_public_materials_have_no_internal_references():
    paths = [BASE / "Dockerfile", BASE / "NOTICE.md", MATERIALS, STATUS]
    for base in (LAKE, BROWSER):
        paths.extend(path for path in base.rglob("*") if path.is_file())
    for path in paths:
        assert internal_reference_categories(path.read_text()) == []
