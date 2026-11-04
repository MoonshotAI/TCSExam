import copy
import hashlib
import io
import json
from pathlib import Path
from subprocess import CompletedProcess
import tarfile
from unittest.mock import patch

import pytest

from tcsexam.build import build_definition
from tcsexam.ce_pace2021 import prepare_public_data
from tcsexam.inventory import classification, refresh
from tcsexam.resources import content_digest, digest, stage_data_context


ROOT = Path(__file__).resolve().parents[3]
TASK = "ce-pace2021"
DATA_ID = "solver-ce-pace2021-development-data"
EVIDENCE = "docs/licenses/third-party/ce-pace2021-source.json"
IMAGES = json.loads((ROOT / "assets/images.json").read_text())["images"]
RECORDS = {row["id"]: row for row in IMAGES if row.get("id")}


def load(path):
    return json.loads((ROOT / path).read_text())


def test_public_manifest_fixed_source_xz_and_distribution_scope():
    record = RECORDS[DATA_ID]
    recipe = load(record["recipe"])
    rows = load(record["files_manifest"])["files"]
    expected = [f"app/instances/heur{number:03d}.gr.xz" for number in range(1, 200, 2)]
    assert [row["path"] for row in rows] == expected
    assert len(rows) == record["files"] == 100
    assert sum(row["bytes"] for row in rows) == record["bytes"] == 33577952
    assert {row["mode"] for row in rows} == {"0644"}
    assert digest(ROOT / record["files_manifest"]) == record["manifest_sha256"]
    assert content_digest(rows, "/") == record["content_digest"]
    assert recipe["source"] == record["source_input"] == {
        "id": "pace-2021-heur-tar-gz",
        "url": "https://fpt.akt.tu-berlin.de/pace2021/heur.tar.gz",
        "bytes": 114857966,
        "sha256": "7fa6fbbdc0427fd99ea64d0ba2c95e160220889e988de99f57e9333241c42bff",
    }
    assert recipe["selection"]["instance_count"] == 100
    assert recipe["compression"]["arguments"] == [
        "--format=xz", "--stdout", "--threads=2", "--check=crc64"
    ]
    assert recipe["compression"]["preset"] == 9
    assert recipe["compression"]["preset_overrides"] == {"heur199.gr": 6}
    assert recipe["compression"]["tool"]["version"] == "5.8.4"
    assert recipe["compression"]["tool"]["source"]["sha256"] == (
        "0014c7886930454fe8bd4228665b51af55eeae560ea135c9c4cd33f55b2591d9"
    )
    assert "source_paths" not in recipe
    assert "source_input_file" not in record
    assert record["distribution"] == "redistributable"
    assert record["public_upload_allowed"] is True
    assert record["distribution_evidence"] == EVIDENCE
    assert record["product_prepared"] is False
    assert record["image_digest"] is None
    assert record["public_image"] is None
    assert record["public_pull_verified"] is False
    assert record["status"] == "local_preparation_required"
    assert record["previous_image_digest"] == (
        "sha256:4049fa3ea8a6a4d23e815387db081c9161902fd23a644111aa485643b87cf9da"
    )
    assert RECORDS[f"dev-online-{TASK}"]["distribution"] == "unresolved"
    assert RECORDS[f"dev-online-{TASK}"]["public_upload_allowed"] is False
    definition = build_definition(ROOT, record)
    assert definition["official_builder"] == recipe["build"]["builder_image"]
    assert recipe["generator_paths"] == ["src/tcsexam/ce_pace2021.py"]
    online = build_definition(ROOT, RECORDS[f"dev-online-{TASK}"])
    assert online["dependencies"] == sorted([DATA_ID, f"{DATA_ID[:-4]}tools"])


def test_public_evidence_cc0_families_and_pending_publication():
    evidence = load(EVIDENCE)
    upstream = evidence["public_development_data"]
    assert upstream["output_files"] == 100
    assert upstream["manifest_sha256"] == RECORDS[DATA_ID]["manifest_sha256"]
    assert upstream["content_digest"] == RECORDS[DATA_ID]["content_digest"]
    assert upstream["second_source"]["plain_files_byte_identical_to_official_archive"] == 100
    assert sum(row["public_instances"] for row in upstream["source_data_families"]["families"]) == 100
    license_record = upstream["license"]
    assert license_record["spdx"] == "CC0-1.0"
    assert digest(ROOT / license_record["local_copy"]) == license_record["sha256"]
    assert (ROOT / license_record["local_copy"]).stat().st_size == license_record["bytes"] == 7048
    resource = RECORDS[DATA_ID]
    recipe = load(resource["recipe"])
    rows = load(resource["files_manifest"])["files"]
    assert resource["data_split"] == "public"
    assert all(row["path"].startswith("app/instances/") for row in rows)
    assert recipe["selection"]["first_instance"] == 1
    assert recipe["selection"]["last_instance"] == 199
    assert recipe["selection"]["instance_step"] == 2
    assert {row["path"] for row in recipe["license_files"]} == {license_record["local_copy"]}
    for row in recipe["license_files"]:
        assert digest(ROOT / row["path"]) == row["sha256"]
        assert (ROOT / row["path"]).stat().st_size == row["bytes"]
    assert resource["distribution"] == "redistributable"
    assert resource["public_image"] is None
    from tcsexam.checks import internal_reference_categories
    assert internal_reference_categories(json.dumps(evidence)) == []
    decisions = load("docs/licenses/third-party/distribution-decisions.json")
    assert decisions["integration_complete"] is False
    assert decisions["enforced_by_exporter"] is False
    decision = next(row for row in decisions["resources"]
                    if row["id"] == "ce-pace2021-public-development-data")
    assert decision["licenses"] == ["CC0-1.0"]
    assert decision["accepted_fixed_products"] == [DATA_ID]
    assert "Hidden judging instances" in decision["decision_scope"]
    assert "solution/precomputed answers" in decision["decision_scope"]
    assert "complete development image" in decision["decision_scope"]


def _write_preparation_fixture(tmp_path):
    recipe = copy.deepcopy(load(RECORDS[DATA_ID]["recipe"]))
    archive = tmp_path / "heur.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        directory = tarfile.TarInfo("heur/")
        directory.type = tarfile.DIRTYPE
        output.addfile(directory)
        for position, number in enumerate(range(1, 200, 2)):
            data = f"p cep 1 0\nc fixture {number:03d}\n".encode()
            member = tarfile.TarInfo(f"heur/heur{number:03d}.gr")
            member.size = len(data)
            member.mode = 0o644 if position < 17 else 0o664
            output.addfile(member, io.BytesIO(data))
    recipe["source"].update(url=None, bytes=archive.stat().st_size, sha256=digest(archive))
    tool_archive = tmp_path / "xz.tar.gz"
    tool_archive.write_bytes(b"fixed XZ source fixture")
    tool = recipe["compression"]["tool"]["source"]
    tool.update(url=None, bytes=tool_archive.stat().st_size, sha256=digest(tool_archive))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    rows = []
    for number in range(1, 200, 2):
        compressed = f"frozen xz heur{number:03d}\n".encode()
        rows.append({
            "path": f"app/instances/heur{number:03d}.gr.xz",
            "bytes": len(compressed),
            "sha256": hashlib.sha256(compressed).hexdigest(),
            "mode": "0644",
        })
    inputs = {recipe["source"]["id"]: archive, tool["id"]: tool_archive}
    return recipe, rows, inputs


def _run_fixture_preparation(tmp_path, wrong_output=False):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    container = "a" * 64
    commands = []

    def execute(command, **kwargs):
        commands.append(command)
        action = command[1]
        if action == "create":
            return CompletedProcess(command, 0, stdout=container + "\n", stderr="")
        if action == "wait":
            return CompletedProcess(command, 0, stdout="0\n", stderr="")
        if action == "cp" and command[2] == container + ":/tcsexam-output/output/.":
            destination = Path(command[3]) / "app/instances"
            destination.mkdir(parents=True, exist_ok=True)
            for row in rows:
                data = (b"wrong compressed bytes" if wrong_output
                        and row["path"].endswith("heur001.gr.xz")
                        else f"frozen xz {Path(row['path']).name.removesuffix('.gr.xz')}\n".encode())
                path = destination / Path(row["path"]).name
                path.write_bytes(data)
                path.chmod(0o644)
        return CompletedProcess(command, 0, stdout="", stderr="")

    with patch("tcsexam.ce_pace2021.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.resources.subprocess.run", side_effect=execute):
        prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            output, tmp_path / "downloads", inputs)
    return output, commands


def test_prepare_recreates_100_outputs_with_docker_cp_and_fixed_xz(tmp_path):
    output, commands = _run_fixture_preparation(tmp_path)
    files = sorted(path for path in output.rglob("*") if path.is_file())
    assert len(files) == 100
    assert [path.name for path in files] == [f"heur{number:03d}.gr.xz"
                                              for number in range(1, 200, 2)]
    assert {path.stat().st_mode & 0o777 for path in files} == {0o644}
    create = next(command for command in commands if command[1] == "create")
    assert create[:2] == ["docker", "create"]
    assert "--pull=never" in create
    script = create[-1]
    assert "xz (XZ Utils) 5.8.4" in script
    assert "--format=xz --stdout --threads=2 --check=crc64" in script
    assert 'if [ "$name" = heur199.gr ]; then preset=6; fi' in script
    assert '"-$preset"' in script
    assert "--decompress --stdout" in script
    assert any(command[:2] == ["docker", "cp"] for command in commands)
    assert not any("--mount" in command or "type=bind" in command for command in commands)
    assert commands[-1] == ["docker", "rm", "-f", "a" * 64]


def test_prepare_rejects_wrong_output_hash(tmp_path):
    with pytest.raises(ValueError, match="compressed output hash or size differs"):
        _run_fixture_preparation(tmp_path, wrong_output=True)


def test_prepare_rejects_wrong_source_hash_before_container(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    archive.write_bytes(archive.read_bytes() + b"corrupt")
    with patch("tcsexam.ce_pace2021.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.resources.subprocess.run") as execute:
        with pytest.raises(ValueError, match="hash or size differs"):
            prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                                tmp_path / "output", tmp_path / "downloads", inputs)
    execute.assert_not_called()


def test_prepare_rejects_wrong_instance_set(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    original = inputs[recipe["source"]["id"]]
    replacement = tmp_path / "wrong-instances.tar.gz"
    with tarfile.open(original, "r:gz") as source, tarfile.open(replacement, "w:gz") as output:
        for member in source:
            if member.name == "heur/heur001.gr":
                member.name = "heur/heur002.gr"
            output.addfile(member, source.extractfile(member) if member.isfile() else None)
    recipe["source"].update(bytes=replacement.stat().st_size, sha256=digest(replacement))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    inputs[recipe["source"]["id"]] = replacement
    with patch("tcsexam.ce_pace2021.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.resources.subprocess.run") as execute:
        with pytest.raises(ValueError, match="undeclared.*heur002"):
            prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                                tmp_path / "output", tmp_path / "downloads", inputs)
    execute.assert_not_called()


def test_stage_data_context_includes_checked_cc0_and_evidence(tmp_path):
    record = copy.deepcopy(RECORDS[DATA_ID])
    payload = b"fixture compressed data"
    rows = [{"path": "app/instances/heur001.gr.xz", "bytes": len(payload),
             "sha256": hashlib.sha256(payload).hexdigest(), "mode": "0644"}]
    manifest = tmp_path / record["files_manifest"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": rows}))
    record["manifest_sha256"] = digest(manifest)
    recipe = tmp_path / record["recipe"]
    recipe.write_text(json.dumps({"license_files": load(record["recipe"])["license_files"]}))
    evidence = tmp_path / EVIDENCE
    evidence.parent.mkdir(parents=True)
    evidence.write_text((ROOT / EVIDENCE).read_text())
    license_path = tmp_path / "docs/licenses/third-party/PACE-CC0-1.0.txt"
    license_path.write_bytes((ROOT / "docs/licenses/third-party/PACE-CC0-1.0.txt").read_bytes())
    dockerfile = tmp_path / "assets/data/Dockerfile"
    dockerfile.write_text("FROM scratch\nCOPY rootfs/ /payload/rootfs/\n")
    (tmp_path / "assets/images.json").write_text(json.dumps({"images": [record]}))
    rootfs_file = tmp_path / "rootfs/app/instances/heur001.gr.xz"
    rootfs_file.parent.mkdir(parents=True)
    rootfs_file.write_bytes(payload)
    rootfs_file.chmod(0o644)
    context = stage_data_context(tmp_path, DATA_ID, tmp_path / "rootfs", tmp_path / "context")
    bundled = context / "licenses/PACE-CC0-1.0.txt"
    assert bundled.read_bytes() == license_path.read_bytes()
    assert digest(bundled) == "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499"
    assert (context / "licenses/ce-pace2021-source.json").is_file()
    assert (context / "rootfs/app/instances/heur001.gr.xz").read_bytes() == payload


def test_inventory_refresh_preserves_images_lean_recipes_and_other_rows(tmp_path):
    public = f"tasks/solver/online/{TASK}/environment/app/instances/heur001.gr.xz"
    even = f"tasks/solver/online/{TASK}/environment/app/instances/heur002.gr.xz"
    hidden = f"tasks/solver/online/{TASK}/tests/instances/heur003.gr.xz"
    answer = f"tasks/solver/online/{TASK}/solution/precomputed/heur003.out"
    unrelated = "tasks/theorem/example/environment/app/Main.lean"
    for path, expected in ((public, "redistributable"), (even, "unresolved"),
                           (hidden, "unresolved"), (answer, "private_only")):
        assert classification(path)[1] == expected
    assert classification(public) == ("public_development", "redistributable", EVIDENCE)
    assets = tmp_path / "assets"
    assets.mkdir()
    rows = [{"path": path, "bytes": 1, "retained_field": "unchanged"}
            for path in (public, even, hidden, answer, unrelated)]
    (assets / "files.json").write_text(json.dumps({"files": rows}))
    images = json.dumps({"schema_version": 4, "images": [
        {"id": "lean-base", "build": {"kind": "custom", "retained": True}},
        {"id": "unrelated", "build": {"retained": True}},
    ]}, indent=2) + "\n"
    (assets / "images.json").write_text(images)
    refresh(tmp_path)
    assert (assets / "images.json").read_text() == images
    updated = {row["path"]: row for row in json.loads((assets / "files.json").read_text())["files"]}
    assert updated[public]["distribution"] == "redistributable"
    assert updated[public]["distribution_evidence"] == EVIDENCE
    assert updated[even]["distribution"] == "unresolved"
    assert updated[hidden]["distribution"] == "unresolved"
    assert updated[answer]["distribution"] == "private_only"
    assert all(row["retained_field"] == "unchanged" for row in updated.values())
