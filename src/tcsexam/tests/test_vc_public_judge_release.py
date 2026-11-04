import hashlib
import json
from pathlib import Path
import stat
import re

from tcsexam.checks import internal_reference_categories

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "tasks/solver/online/vc-pace2019"
MATERIALS = TASK / "tests/public-release"
RECORD_PATH = ROOT / "docs/licenses/third-party/vc-public-judge-image.json"


def load(path=RECORD_PATH):
    return json.loads(Path(path).read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_file_expectations(system):
    expected = {}
    for source in system["debian"]["source_packages"]:
        for file in source["source_files"]:
            path = "/usr/share/tcsexam/source-packages/debian/" + file["filename"]
            expected[path] = (file["sha256"], file["bytes"], "0644")
    python = system["python_runtime"]
    expected["/usr/share/tcsexam/source-packages/" + python["source_file"]] = (
        python["sha256"], python["bytes"], "0644")
    for distribution in system["python_distributions"]:
        expected["/usr/share/tcsexam/source-packages/" + distribution["source_file"]] = (
            distribution["sha256"], distribution["bytes"], "0644")
    return expected


def declared_file_expectations(declaration):
    expected = {}
    for row in declaration["files"]:
        source = MATERIALS / row["source"]
        assert source.is_file()
        expected[row["target"]] = (sha256(source), source.stat().st_size, row["mode"])
    return expected


def test_project_data_and_validator_materials_are_byte_exact_copies():
    copies = {
        "LICENSE-TCSExam": ROOT / "LICENSE",
        "NOTICE-TCSExam": ROOT / "NOTICE",
        "CC-BY-4.0.txt": ROOT / "docs/licenses/CC-BY-4.0.txt",
        "PACE2019-VC-NOTICE.txt": ROOT / "docs/licenses/third-party/PACE2019-VC-NOTICE.txt",
        "vc_validate.cpp": TASK / "environment/app/vc_validate.cpp",
        "LICENSE-vc_validate": TASK / "environment/app/LICENSE-vc_validate",
    }
    for name, original in copies.items():
        assert (MATERIALS / name).read_bytes() == original.read_bytes()
    validator = load(MATERIALS / "vc-validate-source.json")
    assert validator["source_sha256"] == sha256(MATERIALS / "vc_validate.cpp")
    assert validator["license_sha256"] == sha256(MATERIALS / "LICENSE-vc_validate")
    assert validator["source_modified_for_release"] is False
    assert validator["build"]["original_binary_retained"] is True
    assert validator["build"]["byte_identical"] is False
    assert validator["license"] == "GPL-3.0"
    commit = validator["reviewed_commit"]
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    assert validator["source_url"] == validator["upstream"].replace(
        "https://github.com/", "https://raw.githubusercontent.com/") + "/" + commit + "/" + validator["upstream_path"]
    assert load()["checker_rebuild"]["source_record"]["source_sha256"] == validator["source_sha256"]


def test_build_instructions_use_the_same_fixed_public_toolchain():
    validator = load(MATERIALS / "vc-validate-source.json")
    toolchain = validator["build"]["toolchain"]
    assert toolchain.startswith("docker.io/library/gcc@sha256:")
    script = (MATERIALS / "build-vc_validate.sh").read_text()
    instructions = (MATERIALS / "BUILD-vc_validate.md").read_text()
    assert toolchain in script
    assert toolchain in instructions
    assert "g++ -std=c++11 -O3" in script
    assert validator["reviewed_commit"] in instructions
    # Git records the executable flag; CI checkouts can add write permissions.
    mode = stat.S_IMODE((MATERIALS / "build-vc_validate.sh").stat().st_mode)
    assert mode & 0o111 == 0o111


def test_system_source_coverage_is_complete_and_internally_consistent():
    system = load(MATERIALS / "system-dependencies.json")
    debian = system["debian"]
    sources = debian["source_packages"]
    binaries = {name for source in sources for name in source["binary_packages"]}
    files = source_file_expectations(system)
    debian_files = [file for source in sources for file in source["source_files"]]
    assert system["complete"] is True
    assert debian["installed_binary_packages"] == len(binaries) == 151
    assert debian["copyright_files_present"] == 151
    assert debian["copyright_files_missing"] == []
    assert debian["unique_source_versions"] == len(sources) == 86
    assert debian["covered_binary_packages"] == 151
    assert debian["full_source_archives_included"] is True
    assert debian["all_dsc_checksums_verified"] is True
    assert all(source["all_dsc_checksums_verified"] for source in sources)
    assert debian["apt_repository_metadata_authenticated_source_packages"] == 78
    assert len(debian["direct_snapshot_source_packages"]) == 8
    assert debian["dsc_openpgp_independently_verified"] is False
    assert len(debian_files) == 278
    assert sum(file["bytes"] for file in debian_files) == 546497313
    assert len(files) == 280
    assert system["python_runtime"]["official_dockerfile_sha256_verified"] is True
    assert [row["version"] for row in system["python_distributions"]] == ["25.0.1"]


def test_material_declaration_covers_sources_licenses_and_safe_target_modes():
    record = load()
    declaration = load(MATERIALS / "image-materials.json")
    system = load(MATERIALS / "system-dependencies.json")
    expected = declared_file_expectations(declaration) | source_file_expectations(system)
    assert declaration["expected_regular_additions"] == len(expected)
    targets = [row["target"] for row in declaration["files"]]
    assert len(set(targets)) == len(targets)
    for row in declaration["files"]:
        assert row["mode"] in {"0644", "0755"}
        assert Path(row["source"]).name == row["source"]
        assert row["target"].startswith("/") and ".." not in Path(row["target"]).parts
        assert bool((MATERIALS / row["source"]).stat().st_mode & 0o111) == (row["mode"] == "0755")
    assert set(record["licenses_and_sources"].values()) <= set(expected)
    assert "/opt/vc/corresponding-source/vc_validate.cpp" in expected
    assert "/opt/vc/corresponding-source/LICENSE-vc_validate" in expected
    assert declaration["public_upload_allowed_by_this_file"] is False


def test_public_release_materials_have_no_internal_endpoints():
    paths = [RECORD_PATH] + sorted(path for path in MATERIALS.rglob("*") if path.is_file())
    for path in paths:
        if path.suffix in (".json", ".md", ".txt", ".sh", ".cpp", "") or path.name.startswith(("LICENSE", "NOTICE")):
            assert internal_reference_categories(path.read_text()) == [], path


def test_public_product_uses_only_the_public_data_recipe():
    rows = load(ROOT / "assets/images.json")["images"]
    row = next(row for row in rows if row.get("id") == "backend-public-online-vc-pace2019")
    assert row["distribution"] == "redistributable"
    assert row["public_upload_allowed"] is True
    assert "source_product" not in row["build"]
    public_data = "solver-vc-pace2019-development-data"
    assert row["build"]["image_args"]["TCSEXAM_JUDGE_DATA_IMAGE"] == public_data
    assert "solver-vc-pace2019-judging-data" not in row["dependencies"]
    assert row["distribution_evidence"] == "docs/licenses/third-party/vc-public-judge-image.json"
    dockerfile = (ROOT / row["build"]["dockerfile"]).read_text()
    assert "ARG TCSEXAM_JUDGE_DATA_IMAGE" in dockerfile
    assert "COPY --from=tcsexam_data /payload/rootfs/ /" in dockerfile
    assert "INSTANCE_SET=public" in dockerfile
    if row.get("public_pull_verified"):
        assert re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", row["public_image"])
