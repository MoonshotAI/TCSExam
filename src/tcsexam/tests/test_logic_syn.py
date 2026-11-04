import hashlib
import io
import json
from pathlib import Path
import tarfile

from tcsexam.build import build_definition
from tcsexam.inventory import classification, refresh
from tcsexam.logic_syn import prepare_public_data
from tcsexam.resources import content_digest, digest


ROOT = Path(__file__).resolve().parents[3]
TASK = "logic-syn-iwls2023"
DATA_ID = "solver-logic-syn-iwls2023-development-data"
TOOLS_ID = "solver-logic-syn-iwls2023-development-tools"
EVIDENCE = "docs/licenses/third-party/logic-syn-iwls2023-source.json"
IMAGES = json.loads((ROOT / "assets/images.json").read_text())["images"]
RECORDS = {row["id"]: row for row in IMAGES if row.get("id")}


def load(path):
    return json.loads((ROOT / path).read_text())


def test_public_data_manifest_and_fixed_official_source():
    record = RECORDS[DATA_ID]
    recipe = load(record["recipe"])
    rows = load(record["files_manifest"])["files"]
    expected = [f"app/instances/ex{index:02d}.truth" for index in range(100)]
    assert [row["path"] for row in rows if row["path"].endswith(".truth")] == expected
    assert [row["path"] for row in rows if not row["path"].endswith(".truth")] == [
        "app/instances/LICENSE"
    ]
    assert len(rows) == record["files"] == 101
    assert sum(row["bytes"] for row in rows) == record["bytes"]
    assert digest(ROOT / record["files_manifest"]) == record["manifest_sha256"]
    assert content_digest(rows, "/") == record["content_digest"]
    assert recipe["source"] == record["source_input"]
    assert recipe["source"]["url"] == (
        "https://codeload.github.com/alanminko/iwls2022-ls-contest/tar.gz/"
        "ee93f7ca742f172aa64a4a6e12a5b59944475bf0"
    )
    assert recipe["source"]["sha256"] == (
        "70c83b6c9fd453fc599758f1dfb490e0e86ddec7d6c36f706507f0a750196df2"
    )
    assert recipe["selection"]["truth_table_count"] == 100
    assert "source_paths" not in recipe
    assert not any(
        any(part in row["path"] for part in ("tests", "solution", "precomputed", "submissions"))
        for row in rows
    )
    license_row = rows[-1]
    assert license_row["sha256"] == load(EVIDENCE)["public_development_data"]["license"]["sha256"]
    assert record["distribution"] == "redistributable"
    assert record["distribution_evidence"] == EVIDENCE


def test_abc_recipe_transform_and_output_are_fixed():
    record = RECORDS[TOOLS_ID]
    recipe = load(record["recipe"])
    rows = load(record["files_manifest"])["files"]
    assert recipe["source"] == record["source_input"]
    assert recipe["source"]["url"].endswith(
        "/c6e8823c0b9f0c7c469a7538dc2a75b39da17cc4"
    )
    assert recipe["source"]["sha256"] == (
        "6384413f06b6eae900c9d05b48ee55b7107ef27f4eaea7c6096ed19956620010"
    )
    transform_path = ROOT / recipe["transform"]
    assert transform_path.is_file()
    assert digest(transform_path) == recipe["transform_sha256"]
    transform = load(recipe["transform"])
    assert {key: transform["metadata"][key] for key in ("uid", "gid", "uname", "gname")} == {
        "uid": 0, "gid": 0, "uname": "", "gname": ""
    }
    assert len(transform["excluded_paths"]) == 4
    assert transform["omitted_directory_entries"] == ["test", "test/gia"]
    assert transform["replacements"][".gitcommit"]["text"] == "$Format:%H$\n"
    assert "copyright.txt" in transform["member_mtimes"]
    assert "copyright.txt" in transform["mode_overrides"]
    assert len(rows) == 1
    assert rows[0]["path"] == "app/abc-src.tar.xz"
    assert rows[0]["sha256"] == (
        "8b6e0664e16ebe57074345d4704f6398cd7d07b5fc777d65e8366427497ad6d8"
    )
    assert record["content_digest"] == content_digest(rows, "/")
    assert record["distribution"] == "redistributable"
    assert record["distribution_evidence"] == EVIDENCE


def test_build_definitions_have_all_public_inputs():
    for identity in (DATA_ID, TOOLS_ID):
        definition = build_definition(ROOT, RECORDS[identity])
        assert definition["kind"] == "resource"
        assert (ROOT / RECORDS[identity]["recipe"]).is_file()
        assert (ROOT / RECORDS[identity]["files_manifest"]).is_file()
    online = build_definition(ROOT, RECORDS[f"dev-online-{TASK}"])
    assert online["kind"] == "docker"
    assert online["dependencies"] == sorted([DATA_ID, TOOLS_ID])
    assert online["image_args"] == {
        "TCSEXAM_PUBLIC_DATA_IMAGE": DATA_ID,
        "TCSEXAM_TOOLS_IMAGE": TOOLS_ID,
    }
    assert (ROOT / online["dockerfile"]).is_file()
    assert (ROOT / online["context"]).is_dir()
    offline = build_definition(ROOT, RECORDS[f"dev-offline-{TASK}"])
    assert offline["dependencies"] == [f"dev-online-{TASK}"]
    assert (ROOT / offline["dockerfile"]).is_file()
    assert (ROOT / offline["context"]).is_dir()


def test_inventory_refresh_preserves_only_public_development_classification(tmp_path):
    public_truth = f"tasks/solver/online/{TASK}/environment/app/instances/ex00.truth"
    public_abc = f"tasks/solver/online/{TASK}/environment/app/abc-src.tar.xz"
    hidden = f"tasks/solver/online/{TASK}/tests/instances/ex00.truth"
    answer = f"tasks/solver/online/{TASK}/solution/precomputed/ex00.aig"
    for path in (public_truth, public_abc):
        assert classification(path) == ("public_development", "redistributable", EVIDENCE)
    assert classification(hidden)[1] == "unresolved"
    assert classification(answer)[1] == "private_only"
    assets = tmp_path / "assets"
    assets.mkdir()
    rows = [{"path": path, "bytes": 1} for path in (public_truth, public_abc, hidden, answer)]
    (assets / "files.json").write_text(json.dumps({"files": rows}))
    (assets / "images.json").write_text(json.dumps({"images": IMAGES}))
    refresh(tmp_path)
    updated = {row["path"]: row for row in json.loads((assets / "files.json").read_text())["files"]}
    assert updated[public_truth]["distribution"] == "redistributable"
    assert updated[public_abc]["distribution"] == "redistributable"
    assert updated[public_truth]["distribution_evidence"] == EVIDENCE
    assert updated[hidden]["distribution"] == "unresolved"
    assert updated[answer]["distribution"] == "private_only"


def test_public_selection_does_not_copy_submissions_or_hidden_files(tmp_path):
    root_member = "iwls2022-ls-contest-ee93f7ca742f172aa64a4a6e12a5b59944475bf0"
    truth = b"01\n"
    license_bytes = b"MIT fixture\n"
    archive = tmp_path / "official.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        for name, data in (
            (f"{root_member}/benchmarks/ex00.truth", truth),
            (f"{root_member}/LICENSE", license_bytes),
            (f"{root_member}/submissions/ex00.aig", b"reference answer"),
            (f"{root_member}/tests/instances/ex00.truth", b"hidden"),
        ):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o644
            output.addfile(member, io.BytesIO(data))
    recipe = {
        "source": {
            "id": "fixture-iwls",
            "url": None,
            "bytes": archive.stat().st_size,
            "sha256": digest(archive),
        },
        "selection": {
            "source_root": root_member,
            "benchmark_directory": "benchmarks",
            "output_directory": "app/instances",
            "truth_table_count": 1,
            "license_member": "LICENSE",
            "license_output": "app/instances/LICENSE",
        },
    }
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    rows = [
        {"path": "app/instances/ex00.truth", "bytes": len(truth), "mode": "0644",
         "sha256": hashlib.sha256(truth).hexdigest()},
        {"path": "app/instances/LICENSE", "bytes": len(license_bytes), "mode": "0644",
         "sha256": hashlib.sha256(license_bytes).hexdigest()},
    ]
    output = tmp_path / "output"
    output.mkdir()
    prepare_public_data(tmp_path, {"recipe": "recipe.json"}, rows, output,
                        tmp_path / "downloads", {"fixture-iwls": archive})
    assert {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()} == {
        "app/instances/ex00.truth", "app/instances/LICENSE"
    }
    assert not list(output.rglob("*.aig"))


def test_distribution_decision_integration_flags_remain_pending():
    decisions = load("docs/licenses/third-party/distribution-decisions.json")
    assert decisions["integration_complete"] is False
    assert decisions["enforced_by_exporter"] is False


def test_distribution_guide_and_public_evidence_identify_the_same_products():
    from tcsexam.checks import internal_reference_categories

    guide = (ROOT / "docs/licenses/distribution.md").read_text()
    assert "third-party/logic-syn-iwls2023-source.json" in guide
    assert "MIT license for the 100 public truth tables" in guide
    assert "ABC archive has separate software terms" in guide
    evidence = load(EVIDENCE)
    assert evidence["abc_source"]["archive_ownership"] == {
        "uid": 0, "gid": 0, "uname": "", "gname": ""
    }
    assert internal_reference_categories(json.dumps(evidence)) == []
    for section in ("public_development_data", "abc_source"):
        license_record = evidence[section]["license"]
        local = license_record["local_copy"]
        assert digest(ROOT / local) == license_record["sha256"]
    decisions = load("docs/licenses/third-party/distribution-decisions.json")
    group = next(row for row in decisions["resources"] if row["id"] == "logic-syn-public-development")
    assert set(group["accepted_fixed_products"]) == {DATA_ID, TOOLS_ID}
    for identity in (DATA_ID, TOOLS_ID):
        assert RECORDS[identity]["public_upload_allowed"] is True
        assert RECORDS[identity]["public_image"] is None
        assert RECORDS[identity]["public_pull_verified"] is False
        assert RECORDS[identity]["status"] == "local_preparation_required"
    assert "hidden judging instances" in group["decision_scope"]
    assert "solution/precomputed answers" in group["decision_scope"]
