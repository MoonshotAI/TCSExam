import hashlib
import json
from pathlib import Path
import tarfile

from tcsexam.checks import internal_reference_categories


ROOT = Path(__file__).resolve().parents[3]
LEAN_BASE = ROOT / "assets/environments/lean-base"
GRAPHVIZ = LEAN_BASE / "graphviz-epl"
SOURCE_MANIFEST = GRAPHVIZ / "source-manifest.json"
MATERIALS = ROOT / "docs/licenses/third-party/lean-public-rebuild-mathlib-materials.json"
STATUS = LEAN_BASE / "rebuild-status.json"


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sha512(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha512').hexdigest()


def archive_member(archive, root, relative):
    with tarfile.open(archive, "r:gz") as bundle:
        return bundle.extractfile(root + "/" + relative).read()


def test_complete_fixed_source_archives_have_real_hashes_and_readable_members(prepared_lean_source_inputs):
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    assert manifest["archive_set_complete"] is True
    for component in ("graphviz", "wrapper"):
        record = manifest[component]["archive"]
        archive = GRAPHVIZ / record["file"]
        assert archive.is_file()
        assert archive.stat().st_size == record["bytes"]
        assert sha256(archive) == record["sha256"]
        assert sha512(archive) == record["sha512"]
        assert record["full_archive_downloaded"] is True
        assert record["archive_read_verified"] is True
        assert record["independently_verified"] is True
        assert record["signature_verified"] is False
        assert record["official_url"].startswith(("https://gitlab.com/", "https://github.com/"))
        with tarfile.open(archive, "r:gz") as bundle:
            assert len(bundle.getmembers()) == record["member_count"]
            assert bundle.getnames()[0].split("/")[0] == record["archive_root"]
    graphviz = manifest["graphviz"]["archive"]
    assert graphviz["sha512"] == graphviz["expected_sha512_from_wrapper_portfile"]
    wrapper = manifest["wrapper"]["archive"]
    assert archive_member(GRAPHVIZ / graphviz["file"], graphviz["archive_root"], "LICENSE") == (GRAPHVIZ / "EPL-2.0.txt").read_bytes()
    assert archive_member(GRAPHVIZ / wrapper["file"], wrapper["archive_root"], "LICENSE") == (GRAPHVIZ / "WRAPPER-APACHE-2.0.txt").read_bytes()


def test_wrapper_modifications_and_build_rules_match_the_fixed_archive(prepared_lean_source_inputs):
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    wrapper = manifest["wrapper"]["archive"]
    checked = []
    for path in sorted((GRAPHVIZ / "build-rules").rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(GRAPHVIZ / "build-rules").as_posix()
        assert archive_member(GRAPHVIZ / wrapper["file"], wrapper["archive_root"], relative) == path.read_bytes()
        checked.append(relative)
    assert len(checked) == 27
    for required in manifest["build_inputs"]["principal_source_paths"]:
        assert (GRAPHVIZ / required).is_file()
    port = (GRAPHVIZ / "build-rules/vcpkg-overlays/graphviz/portfile.cmake").read_text()
    assert "file(COPY ${CMAKE_CURRENT_LIST_DIR}/CMakeLists.txt DESTINATION ${SOURCE_PATH})" in port
    assert "file(COPY ${CMAKE_CURRENT_LIST_DIR}/cmake/config_checks.cmake DESTINATION ${SOURCE_PATH}/cmake)" in port
    assert "GVPLUGIN_CURRENT" in port
    assert manifest["build_inputs"]["wasm_rebuild_executed"] is False
    assert manifest["build_inputs"]["bit_identical_wasm_claimed"] is False


def test_notice_and_source_offer_provide_a_human_entry_without_apache_mislabeling():
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    notice = (LEAN_BASE / "NOTICE.md").read_text()
    readme = (GRAPHVIZ / "README.md").read_text()
    offer = (GRAPHVIZ / "SOURCE-OFFER.md").read_text()
    assert (GRAPHVIZ / "EPL-2.0.txt").read_text().startswith("Eclipse Public License - v 2.0\n")
    for text in (notice, readme, offer):
        assert "Graphviz" in text
        assert "EPL-2.0" in text
        assert "wrapper" in text
    for text in (notice, readme):
        assert "Apache-2.0" in text
    assert "wrapper license does not apply to Graphviz" in notice
    assert "wrapper license does not cover Graphviz" in readme
    assert "/usr/share/doc/tcsexam/graphviz-epl/" in notice
    assert "/usr/share/doc/tcsexam/graphviz-epl/" in offer
    assert "without network access" in offer
    for component in ("graphviz", "wrapper"):
        archive = manifest[component]["archive"]
        assert archive["official_url"] in offer
        assert archive["sha256"] in offer
        assert archive["sha512"] in offer
        assert str(archive["bytes"]) in offer
    assert "verifies the complete archives against the declared sizes and hashes" in offer
    assert "Other browser components" in readme or "other browser dependencies" in readme


def test_docker_context_installs_and_verifies_every_material_without_payload_changes(prepared_lean_source_inputs):
    dockerfile = (LEAN_BASE / "Dockerfile").read_text()
    assert "COPY NOTICE.md /usr/share/doc/tcsexam/README.md" in dockerfile
    assert "COPY graphviz-epl/ /usr/share/doc/tcsexam/graphviz-epl/" in dockerfile
    assert "sha256sum -c SHA256SUMS" in dockerfile
    assert sha256(LEAN_BASE / "NOTICE.md") in dockerfile
    assert "graphvizDisplay.js" not in dockerfile
    assert "widget/js" not in dockerfile
    for line in dockerfile.splitlines():
        if line.startswith("COPY "):
            source = line.split()[1]
            assert not Path(source).is_absolute()
            assert ".." not in Path(source).parts
            assert (LEAN_BASE / source).exists()
    checksums = {}
    for line in (GRAPHVIZ / "SHA256SUMS").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        checksums[relative] = digest
    files = {
        path.relative_to(GRAPHVIZ).as_posix(): path
        for path in GRAPHVIZ.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    assert checksums.keys() == files.keys()
    assert len(checksums) == 34
    for relative, path in files.items():
        assert checksums[relative] == sha256(path)


def test_corresponding_source_declaration_matches_build_inputs():
    materials = json.loads(MATERIALS.read_text())
    graphviz = materials["proofwidgets_graphviz"]
    source = graphviz["corresponding_source"]
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    assert graphviz["wrapper"]["license"] == "Apache-2.0"
    assert graphviz["program"]["license"] == "EPL-2.0"
    for component, prefix in (("graphviz", "graphviz_archive"),
                              ("wrapper", "wrapper_and_build_source")):
        declared = manifest[component]["archive"]
        for field in ("bytes", "sha256", "sha512", "member_count"):
            assert source[prefix + "_" + field] == declared[field]
        assert source[prefix + "_file"] == str((GRAPHVIZ / declared["file"]).relative_to(ROOT))
    assert graphviz["generated_browser_notice_source_sufficient"] is False
    assert "image_integration" not in graphviz



def test_public_graphviz_documents_and_json_have_no_internal_references():
    paths = [LEAN_BASE / "Dockerfile", LEAN_BASE / "NOTICE.md", MATERIALS, STATUS]
    paths.extend(
        path for path in GRAPHVIZ.rglob("*")
        if path.is_file() and path.suffix != ".gz"
    )
    upstream_ci_example = GRAPHVIZ / "build-rules/.github/instructions/troubleshooting.md"
    for path in paths:
        text = path.read_text()
        if path == upstream_ci_example:
            assert "/home/runner/.cache/ms-playwright" in text
            text = text.replace("/home/runner/.cache/ms-playwright", "upstream-ci-cache")
        assert internal_reference_categories(text) == []
