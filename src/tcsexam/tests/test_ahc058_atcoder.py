import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
from unittest.mock import patch
import zipfile

import pytest

from tcsexam.ahc058_atcoder import prepare_public_data
from tcsexam.build import build_definition
from tcsexam.checks import internal_reference_categories
from tcsexam.inventory import classification, refresh
from tcsexam.resources import content_digest, digest, stage_data_context


ROOT = Path(__file__).resolve().parents[3]
DATA_ID = "solver-ahc058-atcoder-development-data"
TASK = "ahc058-atcoder"
EVIDENCE = ROOT / "docs/licenses/third-party/ahc058-atcoder-source.json"
NOTICE = ROOT / "docs/licenses/third-party/AHC058-ATCODER-NOTICE.txt"
EVIDENCE_NAME = "docs/licenses/third-party/ahc058-atcoder-source.json"
RECORDS = {
    row["id"]: row
    for row in json.loads((ROOT / "assets/images.json").read_text())["images"]
    if row.get("id")
}


def load(path):
    path = Path(path)
    return json.loads((path if path.is_absolute() else ROOT / path).read_text())


def load_task_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_runner_i64_matches_scoring_at_signed_boundaries():
    runner = load_task_module(
        "ahc058_public_runner_for_i64_test",
        "tasks/solver/online/ahc058-atcoder/environment/public_runner.py",
    )
    scoring = load_task_module(
        "ahc058_scoring_for_i64_test",
        "tasks/solver/online/ahc058-atcoder/tests/scoring.py",
    )
    assert runner.MASK64 == scoring.MASK64 == (1 << 64) - 1
    values = (
        0, 1, -1, (1 << 63) - 1, 1 << 63, (1 << 63) + 1,
        (1 << 64) - 1, 1 << 64, (1 << 64) + 1,
        -(1 << 63), -(1 << 64), -(1 << 64) - 1, (1 << 65) + 123,
    )
    for value in values:
        assert runner.i64(value) == scoring.i64(value)


def test_official_source_manifest_and_public_seed_mappings_are_consistent():
    evidence = load(EVIDENCE)
    combined = evidence["combined_product"]
    manifest_path = ROOT / combined["manifest"]
    rows = load(manifest_path)["files"]
    assert len(rows) == combined["output_files"] == 105
    assert sum(row["bytes"] for row in rows) == combined["output_bytes"] == 34938
    assert {row["mode"] for row in rows} == {"0644"}
    assert digest(manifest_path) == combined["manifest_sha256"]
    assert content_digest(rows, "/") == combined["content_digest"]
    assert combined["distribution"] == "local_prepare"
    assert combined["public_upload_allowed"] is False
    official = evidence["official_tools"]
    assert official["archive_bytes"] == 49420
    assert official["archive_sha256"] == (
        "580fa32d99059c78dbe87310b6de771cb64c385c4bf461c7f2865336c9a99ac8"
    )
    assert official["writer"] == "itigo"
    assert evidence["official_instances"]["files"] == 100
    assert evidence["official_instances"]["plaintext_bytes"] == 33296
    generated = evidence["generated_public_instances"]["instances"]
    assert [row["seed"] for row in generated] == [
        250854218785, 51468017913079, 129837058162460,
        150636911777541, 161465247114690,
    ]
    manifest_by_path = {row["path"]: row for row in rows}
    for row in generated:
        expected = manifest_by_path[row["path"]]
        assert row["bytes"] == expected["bytes"]
        assert row["sha256"] == expected["sha256"]


def test_source_notice_preserves_local_only_scope_and_public_runner_boundary():
    evidence = load(EVIDENCE)
    combined = evidence["combined_product"]
    assert digest(NOTICE) == combined["notice_sha256"]
    assert NOTICE.stat().st_size == combined["notice_bytes"]
    notice = NOTICE.read_text()
    for expected in (
            "https://atcoder.jp/contests/ahc058/tasks/ahc058_a",
            "https://img.atcoder.jp/ahc058/UpvAVdx6.zip",
            "itigo",
            "local preparation only",
            "cargo run --release --locked --bin gen",
            "No complete\nrandom stream",
            "outside app/instances/"):
        assert expected in notice
    for generated in evidence["generated_public_instances"]["instances"]:
        assert f"{Path(generated['path']).name} = {generated['seed']}" in notice
    assert combined["derived_image_public_upload_allowed"] is False
    assert combined["local_preparation_grants_public_redistribution"] is False
    resource = RECORDS[DATA_ID]
    recipe = load(resource["recipe"])
    rows = load(resource["files_manifest"])["files"]
    assert resource["data_split"] == "public"
    assert resource["distribution"] == "local_prepare"
    assert resource["public_upload_allowed"] is False
    assert resource["public_image"] is None
    assert len(rows) == 105
    assert all(row["path"].startswith("app/instances/") for row in rows)
    assert recipe["selection"]["official"]["instance_count"] == 100
    assert recipe["selection"]["generated_public"] == [
        {"path": row["path"], "seed": row["seed"]}
        for row in evidence["generated_public_instances"]["instances"]
    ]
    assert recipe["source"]["sha256"] == evidence["official_tools"]["archive_sha256"]
    assert recipe["source"]["bytes"] == evidence["official_tools"]["archive_bytes"]
    assert any(row["path"] == NOTICE.relative_to(ROOT).as_posix()
               and row["sha256"] == digest(NOTICE)
               and row["bytes"] == NOTICE.stat().st_size
               for row in recipe["license_files"])
    assert internal_reference_categories(EVIDENCE.read_text()) == []
    assert internal_reference_categories(notice) == []
    decisions = load("docs/licenses/third-party/distribution-decisions.json")
    assert decisions["integration_complete"] is False
    assert decisions["enforced_by_exporter"] is False
    decision = next(row for row in decisions["resources"]
                    if row["id"] == "ahc058-atcoder-public-development-local-preparation")
    assert decision["local_preparation_products"] == [DATA_ID]
    assert decision["public_upload_allowed"] is False
    assert decision["licenses"] == []
    assert "accepted_fixed_products" not in decision
    assert "Hidden judging data" in decision["decision_scope"]
    assert "solution/precomputed answers" in decision["decision_scope"]


def test_recipe_distribution_and_development_build_graph():
    record = RECORDS[DATA_ID]
    recipe = load(record["recipe"])
    rows = load(record["files_manifest"])["files"]
    assert len(rows) == record["files"] == 105
    assert sum(row["bytes"] for row in rows) == record["bytes"] == 34938
    assert record["recipe_format"] == "official_zip"
    assert record["source_inputs"] == [recipe["source"]]
    assert "source_input" not in record
    assert "source_input_file" not in record
    assert "source_paths" not in recipe
    assert recipe["source"] == {
        "id": "ahc058-atcoder-official-tools-upvavdx6-zip",
        "url": "https://img.atcoder.jp/ahc058/UpvAVdx6.zip",
        "bytes": 49420,
        "sha256": "580fa32d99059c78dbe87310b6de771cb64c385c4bf461c7f2865336c9a99ac8",
    }
    assert recipe["generator_paths"] == ["src/tcsexam/ahc058_atcoder.py"]
    assert recipe["license_files"] == [{
        "path": "docs/licenses/third-party/AHC058-ATCODER-NOTICE.txt",
        "bytes": 2876,
        "sha256": "a4b56cc0814b2e63815cc310678b2ef318bd90500d2f253da741777ca3476c14",
    }]
    assert recipe["build"]["builder_image"] == (
        "rust:1.83-slim@sha256:0f0dc99eb74e410d9420149cbb2b9be84abe00e8dbed6a4201a591a2c81844df"
    )
    assert len(recipe["archive_policy"]["additional_files"]) == 8
    assert len(recipe["archive_policy"]["generator_files"]) == 4
    assert "tools/seeds.txt" not in recipe["archive_policy"]["generator_files"]
    assert record["distribution"] == "local_prepare"
    assert record["public_upload_allowed"] is False
    assert record["distribution_evidence"] == EVIDENCE_NAME
    assert record["product_prepared"] is False
    assert record["image_digest"] is None
    assert record["public_image"] is None
    assert record["public_pull_verified"] is False
    assert record["status"] == "local_preparation_required"
    assert record["previous_image_digest"] == (
        "sha256:06617ede310214f04d9d97341f539eac6040cee2bc341e2862e39f7ab1d8ad84"
    )
    definition = build_definition(ROOT, record)
    assert definition["official_builder"] == recipe["build"]["builder_image"]
    assert definition["pull_args"] == {
        "TCSEXAM_OFFICIAL_BUILDER": recipe["build"]["builder_image"]
    }
    online = build_definition(ROOT, RECORDS[f"dev-online-{TASK}"])
    assert online["dependencies"] == [DATA_ID]
    assert online["image_args"] == {"TCSEXAM_PUBLIC_DATA_IMAGE": DATA_ID}
    assert RECORDS[f"dev-online-{TASK}"]["distribution"] == "unresolved"
    assert RECORDS[f"dev-online-{TASK}"]["public_upload_allowed"] is False
    assert RECORDS[f"dev-online-{TASK}"]["public_image"] is None
    assert build_definition(ROOT, RECORDS[f"backend-online-{TASK}"])["dependencies"] == sorted([
        f"dev-online-{TASK}", f"solver-{TASK}-judging-data"])
    assert RECORDS[f"backend-online-{TASK}"]["runtime_verified"] is False
    assert RECORDS[f"backend-online-{TASK}"]["distribution"] == "unresolved"
    assert RECORDS[f"backend-online-{TASK}"]["public_upload_allowed"] is False


def _write_preparation_fixture(tmp_path, wrong_official=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    recipe = copy.deepcopy(load(RECORDS[DATA_ID]["recipe"]))
    original_rows = load(RECORDS[DATA_ID]["files_manifest"])["files"]
    official = {
        f"{number:04d}.txt": b"official fixture\x00" + f"{number:04d}\n".encode()
        for number in range(100)
    }
    expected_official = dict(official)
    if wrong_official:
        official["0000.txt"] = b"wrong official plaintext"
    generated = [
        b"generated fixture\x00" + declaration["path"].encode() + b"\n"
        for declaration in recipe["selection"]["generated_public"]
    ]
    rows = []
    for original in original_rows:
        name = Path(original["path"]).name
        data = (expected_official[name] if name[:1].isdigit()
                else generated[[row["path"] for row in recipe["selection"]["generated_public"]].index(original["path"])])
        rows.append({"path": original["path"], "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest(), "mode": "0644"})
    additional = {
        name: b"upstream fixture\x00" + name.encode() + b"\n"
        for name in recipe["archive_policy"]["additional_files"]
    }
    for declaration in recipe["archive_policy"]["checked_files"]:
        data = additional[declaration["path"]]
        declaration.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    archive = tmp_path / "official.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for directory in recipe["archive_policy"]["directories"]:
            output.writestr(directory + "/", b"")
        for name, data in additional.items():
            output.writestr(name, data)
        for name, data in official.items():
            output.writestr("tools/in/" + name, data)
    recipe["source"].update(url=None, bytes=archive.stat().st_size, sha256=digest(archive))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    inputs = {recipe["source"]["id"]: archive}
    return recipe, rows, inputs, expected_official, generated


def _run_fixture_preparation(tmp_path, wrong_generated=False, wrong_calibration=False,
                             use_download=False):
    recipe, rows, inputs, official, generated = _write_preparation_fixture(tmp_path)
    calls = []

    def execute(create_command, timeout_sec, log_directory, copy_in=(), copy_out=()):
        calls.append({"command": create_command, "copy_in": copy_in, "copy_out": copy_out})
        source = Path(copy_in[0][0].removesuffix("/."))
        assert not (source / "tools/seeds.txt").exists()
        assert not (source / "tools/src/bin/vis.rs").exists()
        assert (source / "tools/src/bin/gen.rs").is_file()
        assert (source / "tools/Cargo.lock").is_file()
        assert not (source / "app/instances").exists()
        public_seeds = (source / "tools/PUBLIC5.seeds.txt").read_text().splitlines()
        assert public_seeds == [str(row["seed"]) for row in recipe["selection"]["generated_public"]]
        calibration = (source / "tools/CALIBRATION100.seeds.txt").read_text().splitlines()
        assert calibration == [str(number) for number in range(100)]
        for remote, host in copy_out:
            destination = Path(host)
            if remote.endswith("generated-public5/."):
                for index, data in enumerate(generated):
                    if wrong_generated and index == 0:
                        data = b"wrong generated output"
                    (destination / f"{index:04d}.txt").write_bytes(data)
            elif remote.endswith("generated-calibration100/."):
                for name, data in official.items():
                    if wrong_calibration and name == "0000.txt":
                        data = b"wrong calibration output"
                    (destination / name).write_bytes(data)
        return None

    output = tmp_path / "output"
    output.mkdir()
    supplied = None if use_download else inputs
    if use_download:
        recipe["source"]["url"] = "https://img.atcoder.jp/ahc058/UpvAVdx6.zip"
        (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    with patch("tcsexam.ahc058_atcoder.acquire_official_builder", return_value="fixed-builder") as builder, \
            patch("tcsexam.ahc058_atcoder.run_official_container", side_effect=execute), \
            patch("tcsexam.ahc058_atcoder.download_official",
                  side_effect=lambda source, *args, **kwargs: inputs[source["id"]]) as download:
        prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            output, tmp_path / "downloads", supplied)
    return output, rows, official, generated, calls, builder, download


def test_prepare_recreates_105_outputs_and_calibrates_official_generator(tmp_path):
    output, rows, official, generated, calls, _, _ = _run_fixture_preparation(tmp_path)
    files = [path for path in output.rglob("*") if path.is_file()]
    assert len(files) == 105
    assert {path.stat().st_mode & 0o777 for path in files} == {0o644}
    assert {path.relative_to(output).as_posix() for path in files} == {row["path"] for row in rows}
    for number in range(100):
        assert (output / f"app/instances/{number:04d}.txt").read_bytes() == official[f"{number:04d}.txt"]
    for index, name in enumerate(("h00", "h04", "h19", "h24", "h27")):
        assert (output / f"app/instances/{name}.txt").read_bytes() == generated[index]
    assert not list(output.rglob("*seeds*"))
    assert not list(output.rglob("Cargo*"))
    command = " ".join(calls[0]["command"])
    assert "cargo run --release --locked --bin gen -- CALIBRATION100.seeds.txt --dir generated-calibration100" in command
    assert "cargo run --release --locked --bin gen -- PUBLIC5.seeds.txt --dir generated-public5" in command


def test_prepare_downloads_official_zip_with_one_fixed_rust_builder(tmp_path):
    _, _, _, _, _, builder, download = _run_fixture_preparation(tmp_path, use_download=True)
    builder.assert_called_once()
    download.assert_called_once()
    assert download.call_args.args[0]["id"] == "ahc058-atcoder-official-tools-upvavdx6-zip"
    assert download.call_args.args[3] == "fixed-builder"


def test_prepare_rejects_wrong_source_and_output_hashes(tmp_path):
    recipe, rows, inputs, _, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    archive.write_bytes(archive.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="hash or size differs"):
        prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            tmp_path / "bad-source", tmp_path / "downloads", inputs,
                            builder_image="fixed-builder")
    with pytest.raises(ValueError, match="generated public output hash or size differs"):
        _run_fixture_preparation(tmp_path / "wrong-generated", wrong_generated=True)
    with pytest.raises(ValueError, match="official generator calibration differs"):
        _run_fixture_preparation(tmp_path / "wrong-calibration", wrong_calibration=True)


def test_prepare_rejects_changed_official_plaintext(tmp_path):
    recipe, rows, inputs, _, _ = _write_preparation_fixture(tmp_path, wrong_official=True)
    with pytest.raises(ValueError, match="official plaintext size differs"):
        prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            tmp_path / "output", tmp_path / "downloads", inputs,
                            builder_image="fixed-builder")


def _accept_changed_archive(tmp_path, recipe, inputs):
    archive = inputs[recipe["source"]["id"]]
    recipe["source"].update(bytes=archive.stat().st_size, sha256=digest(archive))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))


def _prepare_archive_change(tmp_path, recipe, rows, inputs):
    _accept_changed_archive(tmp_path, recipe, inputs)
    with patch("tcsexam.ahc058_atcoder.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.ahc058_atcoder.run_official_container",
                  side_effect=AssertionError("generator must not run for an invalid archive")):
        prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            tmp_path / "changed-output", tmp_path / "downloads", inputs)


def test_prepare_rejects_undeclared_and_duplicate_members(tmp_path):
    recipe, rows, inputs, _, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("tools/in/0100.txt", b"undeclared")
    with pytest.raises(ValueError, match="undeclared.*0100.txt"):
        _prepare_archive_change(tmp_path, recipe, rows, inputs)
    recipe, rows, inputs, _, _ = _write_preparation_fixture(tmp_path / "duplicate")
    archive = inputs[recipe["source"]["id"]]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("tools/in/0000.txt", b"duplicate")
    with pytest.raises(ValueError, match="Duplicate AHC058 archive member: tools/in/0000.txt"):
        _prepare_archive_change(tmp_path / "duplicate", recipe, rows, inputs)


def test_prepare_rejects_traversal_links_and_special_files(tmp_path):
    for kind in ("traversal", "symlink", "fifo"):
        fixture = tmp_path / kind
        recipe, rows, inputs, _, _ = _write_preparation_fixture(fixture)
        archive = inputs[recipe["source"]["id"]]
        replacement = fixture / (kind + ".zip")
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
            for member in source.infolist():
                if member.filename == "tools/in/0000.txt":
                    if kind == "traversal":
                        output.writestr("tools/in/../../0000.txt", source.read(member))
                    else:
                        special = zipfile.ZipInfo(member.filename)
                        file_kind = stat.S_IFLNK if kind == "symlink" else stat.S_IFIFO
                        special.external_attr = (file_kind | 0o777) << 16
                        output.writestr(special, "target" if kind == "symlink" else "")
                else:
                    output.writestr(member, source.read(member))
        inputs[recipe["source"]["id"]] = replacement
        message = "Unsafe archive path" if kind == "traversal" else "special AHC058 member"
        with pytest.raises(ValueError, match=message):
            _prepare_archive_change(fixture, recipe, rows, inputs)


def test_prepare_rejects_undeclared_directory_and_missing_member(tmp_path):
    recipe, rows, inputs, _, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("unexpected/", b"")
    with pytest.raises(ValueError, match="Undeclared or special AHC058 archive directory"):
        _prepare_archive_change(tmp_path, recipe, rows, inputs)
    fixture = tmp_path / "missing"
    recipe, rows, inputs, _, _ = _write_preparation_fixture(fixture)
    archive = inputs[recipe["source"]["id"]]
    replacement = fixture / "missing.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            if member.filename != "tools/src/lib.rs":
                output.writestr(member, source.read(member))
    inputs[recipe["source"]["id"]] = replacement
    with pytest.raises(ValueError, match="missing declared members.*tools/src/lib.rs"):
        _prepare_archive_change(fixture, recipe, rows, inputs)


def test_prepare_rejects_changed_generator_source_and_extra_seed_mapping(tmp_path):
    recipe, rows, inputs, _, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    replacement = tmp_path / "changed-generator.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            data = b"changed generator" if member.filename == "tools/src/bin/gen.rs" else source.read(member)
            output.writestr(member, data)
    inputs[recipe["source"]["id"]] = replacement
    with pytest.raises(ValueError, match="checked upstream file"):
        _prepare_archive_change(tmp_path, recipe, rows, inputs)
    fixture = tmp_path / "extra-seed"
    recipe, rows, inputs, _, _ = _write_preparation_fixture(fixture)
    recipe["selection"]["generated_public"].append({"path": "app/instances/other.txt", "seed": 1})
    (fixture / "recipe.json").write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match="public seed mapping"):
        prepare_public_data(fixture, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            fixture / "output", fixture / "downloads", inputs)


def test_stage_data_context_contains_notice_source_and_only_105_payload_files(tmp_path):
    rootfs, rows, _, _, _, _, _ = _run_fixture_preparation(tmp_path)
    root = tmp_path / "stage-root"
    record = copy.deepcopy(RECORDS[DATA_ID])
    manifest = root / record["files_manifest"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": rows}))
    record["manifest_sha256"] = digest(manifest)
    record["content_digest"] = content_digest(rows, record["target_root"])
    recipe = root / record["recipe"]
    recipe.write_text(json.dumps(load(RECORDS[DATA_ID]["recipe"])))
    for source in (NOTICE, EVIDENCE):
        destination = root / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    dockerfile = root / "assets/data/Dockerfile"
    dockerfile.parent.mkdir(parents=True, exist_ok=True)
    dockerfile.write_text("FROM scratch\nCOPY rootfs/ /payload/rootfs/\n")
    (root / "assets/images.json").write_text(json.dumps({"images": [record]}))
    context = stage_data_context(root, DATA_ID, rootfs, root / "context")
    assert len(list((context / "rootfs").rglob("*.txt"))) == 105
    assert {path.name for path in (context / "licenses").iterdir()} == {
        "AHC058-ATCODER-NOTICE.txt", "ahc058-atcoder-source.json"
    }
    metadata = json.loads((context / "manifest/content.json").read_text())
    assert metadata["distribution"] == "local_prepare"
    assert metadata["public_upload_allowed"] is False


def test_inventory_refresh_changes_only_ahc058_public_data_scope(tmp_path):
    manifest_rows = load(RECORDS[DATA_ID]["files_manifest"])["files"]
    for row in manifest_rows:
        assert classification(row["source_path"]) == (
            "public_development", "local_prepare", EVIDENCE_NAME
        )
    public = manifest_rows[0]["source_path"]
    generated = manifest_rows[-1]["source_path"]
    verifier = f"tasks/solver/online/{TASK}/environment/public_runner.py"
    hidden = f"tasks/solver/online/{TASK}/tests/instances/0000.txt"
    answer = f"tasks/solver/online/{TASK}/solution/precomputed/0000.out"
    unrelated = "tasks/theorem/example/environment/app/Main.lean"
    for path in (verifier, hidden, unrelated):
        assert classification(path)[1] == "unresolved"
    assert classification(answer)[1] == "private_only"
    assets = tmp_path / "assets"
    assets.mkdir()
    rows = [{"path": path, "bytes": 1, "retained_field": "unchanged"}
            for path in (public, generated, verifier, hidden, answer, unrelated)]
    (assets / "files.json").write_text(json.dumps({"files": rows}))
    images = json.dumps({"schema_version": 3, "images": [
        {"id": "unrelated", "build": {"retained": True}},
    ]}, indent=2) + "\n"
    (assets / "images.json").write_text(images)
    refresh(tmp_path)
    assert (assets / "images.json").read_text() == images
    updated = {row["path"]: row for row in json.loads((assets / "files.json").read_text())["files"]}
    for path in (public, generated):
        assert updated[path]["distribution"] == "local_prepare"
        assert updated[path]["distribution_evidence"] == EVIDENCE_NAME
    for path in (verifier, hidden, unrelated):
        assert updated[path]["distribution"] == "unresolved"
    assert updated[answer]["distribution"] == "private_only"
    assert all(row["retained_field"] == "unchanged" for row in updated.values())
