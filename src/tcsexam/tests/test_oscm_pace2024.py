import copy
import hashlib
import json
from pathlib import Path
import stat
from unittest.mock import patch
import zipfile

import pytest

from tcsexam.build import build_definition
from tcsexam.inventory import classification, refresh
from tcsexam.oscm_pace2024 import prepare_public_data
from tcsexam.resources import content_digest, digest, stage_data_context


ROOT = Path(__file__).resolve().parents[3]
TASK = "oscm-pace2024"
DATA_ID = "solver-oscm-pace2024-development-data"
EVIDENCE = "docs/licenses/third-party/oscm-pace2024-source.json"
NOTICE = "docs/licenses/third-party/PACE2024-OSCM-NOTICE.txt"
MIT = "docs/licenses/third-party/PACE2024-Testsets-MIT.txt"
RECORDS = {
    row["id"]: row
    for row in json.loads((ROOT / "assets/images.json").read_text())["images"]
    if row.get("id")
}


def load(path):
    return json.loads((ROOT / path).read_text())


def test_recipe_manifest_distribution_and_build_graph():
    record = RECORDS[DATA_ID]
    recipe = load(record["recipe"])
    rows = load(record["files_manifest"])["files"]
    paths = {row["path"] for row in rows}
    assert len(rows) == record["files"] == 173
    assert sum(row["bytes"] for row in rows) == record["bytes"] == 5001663
    assert {row["mode"] for row in rows} == {"0644"}
    assert {f"app/instances/{number}.gr" for number in range(1, 101)} <= paths
    assert {f"app/testsets/medium_test_set/instances/{number}.gr"
            for number in range(1, 61)} <= paths
    assert len([path for path in paths if path.startswith("app/testsets/tiny_test_set/")]) == 13
    assert digest(ROOT / record["files_manifest"]) == record["manifest_sha256"] == (
        "765234f6e1ec8b787995ff72f6c192bcace2934f396fc0aca6add5f2b72c0df6"
    )
    assert content_digest(rows, "/") == record["content_digest"]
    assert record["recipe_format"] == "official_zip"
    assert record["source_inputs"] == [recipe["sources"]["exact_public"],
                                       recipe["sources"]["testsets"]]
    assert "source_input" not in record
    assert "source_input_file" not in record
    assert recipe["archive_format"] == "zip"
    assert "source_paths" not in recipe
    assert "compression" not in recipe
    assert recipe["sources"]["exact_public"] == {
        "id": "pace-2024-oscm-exact-public-zip",
        "url": "https://pacechallenge.org/2024/exact-public.zip",
        "bytes": 1013555,
        "sha256": "2b047d7327691820ab041452ebc77410143af16bd5415fe4c42a16f1894e2e10",
    }
    assert recipe["sources"]["testsets"] == {
        "id": "pace-2024-oscm-testsets-603fd742-zip",
        "url": ("https://codeload.github.com/PhKindermann/Pace2024-Testsets/zip/"
                "603fd742fd525971cd78d93195d0eca7256056e9"),
        "bytes": 134770,
        "sha256": "23f30c72bd057c8ecfd7b86e6ed08b7f09c2448407ce1a7cb3d6f83a97209517",
    }
    policy = recipe["archive_policy"]
    assert policy["exact_public"] == {"directories": [], "additional_files": [],
                                      "checked_files": []}
    assert len(policy["testsets"]["directories"]) == 7
    assert len(policy["testsets"]["additional_files"]) == 75
    assert len(policy["testsets"]["checked_files"]) == 2
    assert recipe["generator_paths"] == ["src/tcsexam/oscm_pace2024.py"]
    assert recipe["license_files"] == [
        {"path": NOTICE, "bytes": 3063,
         "sha256": "f12c1b873bad90db815c83ea23998301f891fc65bf740f2f11a111e5d3008b4a"},
        {"path": MIT, "bytes": 1069,
         "sha256": "0d2c12b508572359c08666901c3bf1d510db7ac870e4e105050f9e75ee8b594a"},
    ]
    assert record["distribution"] == "local_prepare"
    assert record["public_upload_allowed"] is False
    assert record["distribution_evidence"] == EVIDENCE
    assert record["product_prepared"] is False
    assert record["image_digest"] is None
    assert record["public_image"] is None
    assert record["public_pull_verified"] is False
    assert record["status"] == "local_preparation_required"
    assert record["previous_image_digest"] == (
        "sha256:ef031669224d968d23097c0143588890d8f1baa11fc3e8ba70ba41f0cd711ae0"
    )
    definition = build_definition(ROOT, record)
    assert definition["official_builder"] == recipe["build"]["builder_image"]
    assert definition["pull_args"] == {
        "TCSEXAM_OFFICIAL_BUILDER": recipe["build"]["builder_image"]
    }
    online = build_definition(ROOT, RECORDS[f"dev-online-{TASK}"])
    assert online["dependencies"] == sorted([DATA_ID, f"{DATA_ID[:-4]}tools"])
    offline = build_definition(ROOT, RECORDS[f"dev-offline-{TASK}"])
    assert offline["dependencies"] == [f"dev-online-{TASK}"]
    backend = build_definition(ROOT, RECORDS[f"backend-online-{TASK}"])
    assert backend["dependencies"] == sorted([f"dev-online-{TASK}",
                                               f"solver-{TASK}-judging-data"])
    public = build_definition(ROOT, RECORDS[f"backend-public-online-{TASK}"])
    assert public["dependencies"] == sorted([f"dev-online-{TASK}", DATA_ID])
    assert build_definition(ROOT, RECORDS[f"{TASK}-backend-base"])["dependencies"] == [f"dev-online-{TASK}"]
    public_backend = build_definition(ROOT, RECORDS[f"backend-public-online-{TASK}"])
    assert public_backend["dependencies"] == sorted([f"dev-online-{TASK}", DATA_ID])
    for identity in (f"dev-online-{TASK}", f"dev-offline-{TASK}",
                     f"{TASK}-backend-base", f"backend-online-{TASK}",
                     f"backend-public-online-{TASK}", f"verifier-offline-{TASK}"):
        assert RECORDS[identity]["distribution"] == "unresolved"
        assert RECORDS[identity]["public_upload_allowed"] is False
        assert RECORDS[identity]["public_image"] is None


def test_source_record_partitions_license_scope():
    evidence = load(EVIDENCE)
    combined = evidence["combined_product"]
    assert combined["output_files"] == 173
    assert combined["output_bytes"] == 5001663
    assert combined["distribution"] == "local_prepare"
    assert combined["public_upload_allowed"] is False
    assert combined["derived_image_public_upload_allowed"] is False
    assert digest(ROOT / combined["manifest"]) == combined["manifest_sha256"]
    assert content_digest(load(combined["manifest"])["files"], "/") == combined["content_digest"]
    exact = evidence["exact_track_public_instances"]
    assert exact["files"] == 100
    assert exact["plaintext_bytes"] == 4793799
    assert exact["license_review"]["upstream_data_license"] == "not provided"
    assert exact["license_review"]["public_upload_allowed"] is False
    testsets = evidence["testsets"]
    assert testsets["files"] == 73
    assert testsets["medium_files"] == 60
    assert testsets["tiny_files"] == 13
    assert testsets["plaintext_bytes"] == 207864
    assert testsets["license"]["spdx"] == "MIT"
    assert "Only the 60 medium and 13 tiny" in testsets["license"]["coverage"]
    for declaration in (combined, exact["license_review"], testsets["license"]):
        assert "CC0-1.0" not in declaration
    assert digest(ROOT / NOTICE) == combined["notice_sha256"]
    assert digest(ROOT / MIT) == testsets["license"]["sha256"]
    assert (ROOT / MIT).read_bytes() == (
        ROOT / "tasks/solver/online/oscm-pace2024/environment/app/testsets/LICENSE"
    ).read_bytes()
    notice = (ROOT / NOTICE).read_text()
    assert "public_upload_allowed=false" in notice
    assert "covers only the 60 medium and" in notice
    assert "No data license is" in notice
    assert evidence["verification"]["public_upload_performed"] is False
    assert evidence["verification"]["hidden_judging_executed"] is False
    assert evidence["verification"]["precomputed_answers_used"] is False
    assert evidence["verification"]["reference_answers_used"] is False
    from tcsexam.checks import internal_reference_categories
    assert internal_reference_categories(json.dumps(evidence)) == []
    decisions = load("docs/licenses/third-party/distribution-decisions.json")
    assert decisions["integration_complete"] is False
    assert decisions["enforced_by_exporter"] is False
    decision = next(row for row in decisions["resources"]
                    if row["id"] == "oscm-pace2024-public-development-local-preparation")
    assert decision["local_preparation_products"] == [DATA_ID]
    assert decision["public_upload_allowed"] is False
    assert decision["licenses"] == []
    assert decision["component_licenses"] == {
        "exact_public_100": "not provided",
        "testsets_73": "MIT",
    }
    assert "accepted_fixed_products" not in decision
    assert "Hidden judging data" in decision["decision_scope"]
    assert "solution/precomputed answers" in decision["decision_scope"]


def _member_for_output(recipe, path):
    if path.startswith("app/instances/"):
        return "exact_public", Path(path).name
    root = recipe["selection"]["testsets"]["archive_root"]
    if "/medium_test_set/" in path:
        return "testsets", f"{root}/medium_test_set/instances/{Path(path).name}"
    return "testsets", f"{root}/tiny_test_set/instances/{Path(path).name}"


def _write_preparation_fixture(tmp_path, wrong_plaintext=False):
    recipe = copy.deepcopy(load(RECORDS[DATA_ID]["recipe"]))
    original_rows = load(RECORDS[DATA_ID]["files_manifest"])["files"]
    rows = []
    plain = {"exact_public": {}, "testsets": {}}
    for original in original_rows:
        data = b"binary fixture\x00" + original["path"].encode() + b"\n"
        source, member = _member_for_output(recipe, original["path"])
        plain[source][member] = data
        rows.append({"path": original["path"], "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest(), "mode": "0644"})
        if wrong_plaintext and original["path"] == "app/instances/1.gr":
            plain[source][member] = b"wrong official plaintext"
    archives = {}
    for source in ("exact_public", "testsets"):
        archive = tmp_path / f"{source}.zip"
        with zipfile.ZipFile(archive, "w") as output:
            policy = recipe["archive_policy"][source]
            for directory in policy["directories"]:
                output.writestr(directory + "/", b"")
            checked = {row["path"]: row for row in policy["checked_files"]}
            for member in policy["additional_files"]:
                if member in checked:
                    if member.endswith("/LICENSE"):
                        data = (ROOT / "tasks/solver/online/oscm-pace2024/environment/app/testsets/LICENSE").read_bytes()
                    else:
                        data = (ROOT / "tasks/solver/online/oscm-pace2024/environment/app/testsets/README.md").read_bytes()
                else:
                    data = b"unused generated solution fixture\n"
                output.writestr(member, data)
            for member, data in plain[source].items():
                output.writestr(member, data)
        archives[source] = archive
        recipe["sources"][source].update(url=None, bytes=archive.stat().st_size,
                                         sha256=digest(archive))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    inputs = {recipe["sources"][name]["id"]: path for name, path in archives.items()}
    return recipe, rows, inputs, plain


def _run_fixture_preparation(tmp_path, wrong_plaintext=False):
    recipe, rows, inputs, plain = _write_preparation_fixture(tmp_path, wrong_plaintext)
    output = tmp_path / "output"
    output.mkdir()
    prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                        output, tmp_path / "downloads", inputs)
    return output, plain


def _accept_changed_archive(tmp_path, recipe, inputs, source):
    archive = inputs[recipe["sources"][source]["id"]]
    recipe["sources"][source].update(bytes=archive.stat().st_size, sha256=digest(archive))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))


def _prepare_changed_archive(tmp_path, recipe, rows, inputs):
    prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                        tmp_path / "changed-output", tmp_path / "downloads", inputs)


def test_prepare_recreates_173_binary_outputs_from_both_zips(tmp_path):
    output, plain = _run_fixture_preparation(tmp_path)
    files = [path for path in output.rglob("*") if path.is_file()]
    assert len(files) == 173
    assert sum(path.stat().st_size for path in files) == sum(
        len(data) for source in plain.values() for data in source.values())
    assert {path.stat().st_mode & 0o777 for path in files} == {0o644}
    for source, members in plain.items():
        for data in members.values():
            assert data in [path.read_bytes() for path in files]
    assert not list(output.rglob("*.sol"))
    assert not list(output.rglob("*.xz"))


def test_prepare_downloads_both_official_sources_with_fixed_builder(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    for name, url in (("exact_public", "https://pacechallenge.org/2024/exact-public.zip"),
                      ("testsets", "https://codeload.github.com/fixed.zip")):
        recipe["sources"][name]["url"] = url
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    (tmp_path / "output").mkdir()
    with patch("tcsexam.oscm_pace2024.acquire_official_builder", return_value="fixed-builder") as builder, \
            patch("tcsexam.oscm_pace2024.download_official",
                  side_effect=lambda source, *args, **kwargs: inputs[source["id"]]) as download:
        prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            tmp_path / "output", tmp_path / "downloads")
    builder.assert_called_once()
    assert [call.args[0]["id"] for call in download.call_args_list] == [
        "pace-2024-oscm-exact-public-zip", "pace-2024-oscm-testsets-603fd742-zip"
    ]


def test_prepare_rejects_wrong_source_hash(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["sources"]["exact_public"]["id"]]
    archive.write_bytes(archive.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="hash or size differs"):
        prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            tmp_path / "output", tmp_path / "downloads", inputs)


def test_prepare_rejects_wrong_output_hash(tmp_path):
    with pytest.raises(ValueError, match="official plaintext.*differs"):
        _run_fixture_preparation(tmp_path, wrong_plaintext=True)


def test_prepare_rejects_undeclared_member(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["sources"]["exact_public"]["id"]]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("101.gr", b"undeclared")
    _accept_changed_archive(tmp_path, recipe, inputs, "exact_public")
    with pytest.raises(ValueError, match="undeclared.*101.gr"):
        _prepare_changed_archive(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_duplicate_member(tmp_path):
    recipe, rows, inputs, plain = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["sources"]["exact_public"]["id"]]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("1.gr", plain["exact_public"]["1.gr"])
    _accept_changed_archive(tmp_path, recipe, inputs, "exact_public")
    with pytest.raises(ValueError, match="Duplicate OSCM archive member: 1.gr"):
        _prepare_changed_archive(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_path_traversal(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["sources"]["exact_public"]["id"]]
    replacement = tmp_path / "traversal.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            name = "../1.gr" if member.filename == "1.gr" else member.filename
            output.writestr(name, source.read(member))
    inputs[recipe["sources"]["exact_public"]["id"]] = replacement
    _accept_changed_archive(tmp_path, recipe, inputs, "exact_public")
    with pytest.raises(ValueError, match="Unsafe archive path"):
        _prepare_changed_archive(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_link_member(tmp_path):
    recipe, rows, inputs, plain = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["sources"]["exact_public"]["id"]]
    replacement = tmp_path / "link.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            if member.filename == "1.gr":
                link = zipfile.ZipInfo("1.gr")
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                output.writestr(link, "2.gr")
            else:
                output.writestr(member, source.read(member))
    inputs[recipe["sources"]["exact_public"]["id"]] = replacement
    _accept_changed_archive(tmp_path, recipe, inputs, "exact_public")
    with pytest.raises(ValueError, match="special OSCM member: 1.gr"):
        _prepare_changed_archive(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_undeclared_directory(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["sources"]["exact_public"]["id"]]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("unexpected/", b"")
    _accept_changed_archive(tmp_path, recipe, inputs, "exact_public")
    with pytest.raises(ValueError, match="Undeclared OSCM archive directory"):
        _prepare_changed_archive(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_missing_member(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["sources"]["exact_public"]["id"]]
    replacement = tmp_path / "missing.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            if member.filename != "1.gr":
                output.writestr(member, source.read(member))
    inputs[recipe["sources"]["exact_public"]["id"]] = replacement
    _accept_changed_archive(tmp_path, recipe, inputs, "exact_public")
    with pytest.raises(ValueError, match="missing declared members.*1.gr"):
        _prepare_changed_archive(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_changed_mit_text(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["sources"]["testsets"]["id"]]
    replacement = tmp_path / "changed-license.zip"
    license_name = recipe["archive_policy"]["testsets"]["checked_files"][0]["path"]
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            data = b"changed MIT text" if member.filename == license_name else source.read(member)
            output.writestr(member, data)
    inputs[recipe["sources"]["testsets"]["id"]] = replacement
    _accept_changed_archive(tmp_path, recipe, inputs, "testsets")
    with pytest.raises(ValueError, match="checked upstream file"):
        _prepare_changed_archive(tmp_path, recipe, rows, inputs)


def _stage_fixture(tmp_path):
    record = copy.deepcopy(RECORDS[DATA_ID])
    payload = b"binary graph fixture\x00\n"
    rows = [{"path": "app/instances/1.gr", "bytes": len(payload),
             "sha256": hashlib.sha256(payload).hexdigest(), "mode": "0644"}]
    manifest = tmp_path / record["files_manifest"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": rows}))
    record["manifest_sha256"] = digest(manifest)
    recipe = tmp_path / record["recipe"]
    recipe.write_text(json.dumps(load(record["recipe"])))
    evidence = tmp_path / EVIDENCE
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text((ROOT / EVIDENCE).read_text())
    for relative in (NOTICE, MIT):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / relative).read_bytes())
    dockerfile = tmp_path / "assets/data/Dockerfile"
    dockerfile.parent.mkdir(parents=True, exist_ok=True)
    dockerfile.write_text("FROM scratch\nCOPY rootfs/ /payload/rootfs/\n")
    (tmp_path / "assets/images.json").write_text(json.dumps({"images": [record]}))
    rootfs_file = tmp_path / "rootfs/app/instances/1.gr"
    rootfs_file.parent.mkdir(parents=True)
    rootfs_file.write_bytes(payload)
    rootfs_file.chmod(0o644)
    return payload


def test_stage_data_context_has_notice_mit_and_local_only_metadata(tmp_path):
    payload = _stage_fixture(tmp_path)
    context = stage_data_context(tmp_path, DATA_ID, tmp_path / "rootfs", tmp_path / "context")
    names = sorted(path.name for path in (context / "licenses").iterdir())
    assert names == ["PACE2024-OSCM-NOTICE.txt", "PACE2024-Testsets-MIT.txt",
                     "oscm-pace2024-source.json"]
    assert (context / "rootfs/app/instances/1.gr").read_bytes() == payload
    metadata = json.loads((context / "manifest/content.json").read_text())
    assert metadata["distribution"] == "local_prepare"
    assert metadata["public_upload_allowed"] is False


def test_inventory_refresh_changes_only_oscm_public_data_scope(tmp_path):
    exact = f"tasks/solver/online/{TASK}/environment/app/instances/1.gr"
    medium = f"tasks/solver/online/{TASK}/environment/app/testsets/medium_test_set/instances/1.gr"
    tiny = f"tasks/solver/online/{TASK}/environment/app/testsets/tiny_test_set/instances/star_6.gr"
    mit = f"tasks/solver/online/{TASK}/environment/app/testsets/LICENSE"
    solution = f"tasks/solver/online/{TASK}/environment/app/testsets/medium_test_set/solutions/1.sol"
    hidden = f"tasks/solver/online/{TASK}/tests/instances/101.gr"
    answer = f"tasks/solver/online/{TASK}/solution/precomputed/101.sol"
    verifier = f"tasks/solver/online/{TASK}/environment/app/public_runner.py"
    unrelated = "tasks/theorem/example/environment/app/Main.lean"
    for path in (exact, medium, tiny, mit):
        assert classification(path) == ("public_development", "local_prepare", EVIDENCE)
    for path in (solution, hidden, verifier):
        assert classification(path)[1] == "unresolved"
    assert classification(answer)[1] == "private_only"
    assets = tmp_path / "assets"
    assets.mkdir()
    rows = [{"path": path, "bytes": 1, "retained_field": "unchanged"}
            for path in (exact, medium, tiny, mit, solution, hidden, answer, verifier, unrelated)]
    (assets / "files.json").write_text(json.dumps({"files": rows}))
    images = json.dumps({"schema_version": 4, "images": [
        {"id": "lean-base", "build": {"kind": "custom", "retained": True}},
        {"id": "unrelated", "build": {"retained": True}},
    ]}, indent=2) + "\n"
    (assets / "images.json").write_text(images)
    refresh(tmp_path)
    assert (assets / "images.json").read_text() == images
    updated = {row["path"]: row for row in json.loads((assets / "files.json").read_text())["files"]}
    for path in (exact, medium, tiny, mit):
        assert updated[path]["distribution"] == "local_prepare"
        assert updated[path]["distribution_evidence"] == EVIDENCE
    for path in (solution, hidden, verifier, unrelated):
        assert updated[path]["distribution"] == "unresolved"
    assert updated[answer]["distribution"] == "private_only"
    assert all(row["retained_field"] == "unchanged" for row in updated.values())
