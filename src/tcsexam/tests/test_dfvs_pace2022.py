import copy
import hashlib
import io
import json
import lzma
from pathlib import Path
from subprocess import CompletedProcess
import tarfile
from unittest.mock import patch

import pytest

from tcsexam.build import build_definition
from tcsexam.dfvs_pace2022 import prepare_public_data
from tcsexam.inventory import classification, refresh
from tcsexam.resources import content_digest, digest, stage_data_context


ROOT = Path(__file__).resolve().parents[3]
TASK = "dfvs-pace2022"
DATA_ID = "solver-dfvs-pace2022-development-data"
EVIDENCE = "docs/licenses/third-party/dfvs-pace2022-source.json"
IMAGES = json.loads((ROOT / "assets/images.json").read_text())["images"]
RECORDS = {row["id"]: row for row in IMAGES if row.get("id")}


def load(path):
    return json.loads((ROOT / path).read_text())


def test_public_manifest_fixed_source_xz_and_local_only_scope():
    record = RECORDS[DATA_ID]
    recipe = load(record["recipe"])
    rows = load(record["files_manifest"])["files"]
    expected = [f"app/instances/e_{number:03d}.xz" for number in range(1, 200, 2)]
    assert [row["path"] for row in rows] == expected
    assert len(rows) == record["files"] == 100
    assert sum(row["bytes"] for row in rows) == record["bytes"] == 10362488
    assert {row["mode"] for row in rows} == {"0644"}
    assert digest(ROOT / record["files_manifest"]) == record["manifest_sha256"] == (
        "71de6fc2fc3b614ab31ec692908c728c47fe59dafcb6ab6140471d86a2548336"
    )
    assert content_digest(rows, "/") == record["content_digest"]
    assert recipe["source"] == record["source_input"] == {
        "id": "pace-2022-exact-public-tar-gz",
        "url": "https://heibox.uni-heidelberg.de/f/be4337d9e4234bca8606/?dl=1",
        "bytes": 14237896,
        "sha256": "56158c1e637c5f5a332e46e0e51afb99c062c5261e76acc61d195b03cc67bc18",
    }
    assert recipe["selection"] == {
        "source_root": "exact_public",
        "output_directory": "app/instances",
        "first_instance": 1,
        "last_instance": 199,
        "instance_step": 2,
        "instance_count": 100,
    }
    assert recipe["compression"]["arguments"] == [
        "--format=xz", "--stdout", "--threads=2", "--check=crc64"
    ]
    assert recipe["compression"]["preset"] == 6
    assert recipe["compression"]["preset_overrides"] == {}
    assert recipe["compression"]["tool"]["version"] == "5.2.5"
    assert recipe["compression"]["tool"]["source"] == {
        "id": "xz-utils-5.2.5-tar-gz",
        "url": "https://tukaani.org/xz/xz-5.2.5.tar.gz",
        "bytes": 1791345,
        "sha256": "f6f4910fd033078738bd82bfba4f49219d03b17eb0794eb91efbae419f4aba10",
    }
    assert "source_paths" not in recipe
    assert "source_input_file" not in record
    assert "license_files" not in recipe
    assert record["distribution"] == "local_prepare"
    assert record["public_upload_allowed"] is False
    assert record["distribution_evidence"] == EVIDENCE
    assert record["product_prepared"] is False
    assert record["image_digest"] is None
    assert record["public_image"] is None
    assert record["public_pull_verified"] is False
    assert record["status"] == "local_preparation_required"
    assert record["previous_image_digest"] == (
        "sha256:6ee4e1972c6737485f5b8776099007fbd805dcaff9c856fa78958cb613a594a1"
    )
    assert RECORDS[f"dev-online-{TASK}"]["distribution"] == "unresolved"
    assert RECORDS[f"dev-online-{TASK}"]["public_upload_allowed"] is False
    assert RECORDS[f"dev-online-{TASK}"]["status"] == "local_preparation_required"
    assert RECORDS[f"dev-online-{TASK}"]["runtime_verified"] is False
    definition = build_definition(ROOT, record)
    assert definition["official_builder"] == recipe["build"]["builder_image"]
    assert recipe["generator_paths"] == ["src/tcsexam/dfvs_pace2022.py"]
    online = build_definition(ROOT, RECORDS[f"dev-online-{TASK}"])
    assert online["dependencies"] == sorted([DATA_ID, f"{DATA_ID[:-4]}tools"])


def test_source_record_does_not_invent_a_data_license():
    evidence = load(EVIDENCE)
    upstream = evidence["public_development_data"]
    assert upstream["output_files"] == 100
    assert upstream["output_bytes"] == 10362488
    assert upstream["upstream"]["plaintext_bytes"] == 66294762
    assert upstream["upstream"]["source_modes_observed"] == {"0664": 100}
    assert upstream["manifest_sha256"] == RECORDS[DATA_ID]["manifest_sha256"]
    assert upstream["content_digest"] == RECORDS[DATA_ID]["content_digest"]
    license_record = upstream["license_review"]
    assert license_record["upstream_data_license"] == "not provided"
    assert license_record["local_prepare_only"] is True
    assert license_record["public_upload_allowed"] is False
    assert license_record["statement"] == "上游未附数据许可，本地准备不授予公开再分发权。"
    assert "CC-BY 4.0" in license_record["report_license_note"]
    assert "No CC0" in license_record["report_license_note"]
    assert upstream["transform"]["xz_version"] == "5.2.5"
    assert upstream["transform"]["xz_source_sha256"] == (
        "f6f4910fd033078738bd82bfba4f49219d03b17eb0794eb91efbae419f4aba10"
    )
    resource = RECORDS[DATA_ID]
    recipe = load(resource["recipe"])
    rows = load(resource["files_manifest"])["files"]
    assert resource["data_split"] == "public"
    assert resource["distribution"] == "local_prepare"
    assert resource["public_upload_allowed"] is False
    assert resource["public_image"] is None
    assert all(row["path"].startswith("app/instances/") for row in rows)
    assert recipe["selection"]["first_instance"] == 1
    assert recipe["selection"]["last_instance"] == 199
    assert recipe["selection"]["instance_step"] == 2
    assert not recipe.get("license_files")
    from tcsexam.checks import internal_reference_categories
    assert internal_reference_categories(json.dumps(evidence)) == []
    decisions = load("docs/licenses/third-party/distribution-decisions.json")
    assert decisions["integration_complete"] is False
    assert decisions["enforced_by_exporter"] is False
    decision = next(row for row in decisions["resources"]
                    if row["id"] == "dfvs-pace2022-public-development-local-preparation")
    assert decision["recommended_action"] == "automatic_official_download_and_local_preparation_only"
    assert decision["licenses"] == []
    assert decision["local_preparation_products"] == [DATA_ID]
    assert decision["public_upload_allowed"] is False
    assert "accepted_fixed_products" not in decision
    assert "Hidden judging instances" in decision["decision_scope"]
    assert "solution/precomputed answers" in decision["decision_scope"]


def _write_preparation_fixture(tmp_path, wrong_plaintext=False):
    recipe = copy.deepcopy(load(RECORDS[DATA_ID]["recipe"]))
    archive = tmp_path / "exact_public.tar.gz"
    plain = {
        f"e_{number:03d}": f"% DFVS fixture {number:03d}\n1 0 0\n\n".encode()
        for number in range(1, 200, 2)
    }
    with tarfile.open(archive, "w:gz") as output:
        directory = tarfile.TarInfo("exact_public")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o775
        output.addfile(directory)
        for number in range(1, 200, 2):
            stem = f"e_{number:03d}"
            data = plain[stem]
            member = tarfile.TarInfo(f"exact_public/{stem}")
            member.size = len(data)
            member.mode = 0o664
            output.addfile(member, io.BytesIO(data))
    recipe["source"].update(url=None, bytes=archive.stat().st_size, sha256=digest(archive))
    tool_archive = tmp_path / "xz.tar.gz"
    tool_archive.write_bytes(b"fixed XZ source fixture")
    tool = recipe["compression"]["tool"]["source"]
    tool.update(url=None, bytes=tool_archive.stat().st_size, sha256=digest(tool_archive))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    rows = []
    compressed = {}
    for number in range(1, 200, 2):
        stem = f"e_{number:03d}"
        source = b"wrong official plaintext\n" if wrong_plaintext and number == 1 else plain[stem]
        data = lzma.compress(source, format=lzma.FORMAT_XZ,
                             check=lzma.CHECK_CRC64, preset=6)
        compressed[f"app/instances/{stem}.xz"] = data
        rows.append({
            "path": f"app/instances/{stem}.xz",
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "mode": "0644",
        })
    inputs = {recipe["source"]["id"]: archive, tool["id"]: tool_archive}
    return recipe, rows, inputs, compressed


def _run_fixture_preparation(tmp_path, wrong_output=False, wrong_plaintext=False):
    recipe, rows, inputs, compressed = _write_preparation_fixture(tmp_path, wrong_plaintext)
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
                        and row["path"].endswith("e_001.xz") else compressed[row["path"]])
                path = destination / Path(row["path"]).name
                path.write_bytes(data)
                path.chmod(0o644)
        return CompletedProcess(command, 0, stdout="", stderr="")

    with patch("tcsexam.dfvs_pace2022.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.resources.subprocess.run", side_effect=execute):
        prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            output, tmp_path / "downloads", inputs)
    return output, commands


def test_prepare_recreates_100_outputs_with_docker_cp_and_fixed_xz(tmp_path):
    output, commands = _run_fixture_preparation(tmp_path)
    files = sorted(path for path in output.rglob("*") if path.is_file())
    assert len(files) == 100
    assert [path.name for path in files] == [f"e_{number:03d}.xz"
                                              for number in range(1, 200, 2)]
    assert {path.stat().st_mode & 0o777 for path in files} == {0o644}
    create = next(command for command in commands if command[1] == "create")
    assert create[:2] == ["docker", "create"]
    assert "--pull=never" in create
    script = create[-1]
    assert "xz (XZ Utils) 5.2.5" in script
    assert "liblzma 5.2.5" in script
    assert "--format=xz --stdout --threads=2 --check=crc64 -6" in script
    assert "--decompress --stdout" in script
    assert 'test "$#" -eq 100' in script
    assert any(command[:2] == ["docker", "cp"] for command in commands)
    assert not any("--mount" in command or "type=bind" in command for command in commands)
    assert commands[-1] == ["docker", "rm", "-f", "a" * 64]


def test_prepare_rejects_wrong_output_hash(tmp_path):
    with pytest.raises(ValueError, match="compressed output hash or size differs"):
        _run_fixture_preparation(tmp_path, wrong_output=True)


def test_prepare_rejects_output_not_matching_official_plaintext(tmp_path):
    with pytest.raises(ValueError, match="decompressed output differs from official plaintext"):
        _run_fixture_preparation(tmp_path, wrong_plaintext=True)


def test_prepare_rejects_wrong_source_hash_before_container(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    archive.write_bytes(archive.read_bytes() + b"corrupt")
    with patch("tcsexam.dfvs_pace2022.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.resources.subprocess.run") as execute:
        with pytest.raises(ValueError, match="hash or size differs"):
            prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                                tmp_path / "output", tmp_path / "downloads", inputs)
    execute.assert_not_called()


def test_prepare_rejects_wrong_instance_set(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    original = inputs[recipe["source"]["id"]]
    replacement = tmp_path / "wrong-instances.tar.gz"
    with tarfile.open(original, "r:gz") as source, tarfile.open(replacement, "w:gz") as output:
        for member in source:
            if member.name == "exact_public/e_001":
                member.name = "exact_public/e_002"
            output.addfile(member, source.extractfile(member) if member.isfile() else None)
    recipe["source"].update(bytes=replacement.stat().st_size, sha256=digest(replacement))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    inputs[recipe["source"]["id"]] = replacement
    with patch("tcsexam.dfvs_pace2022.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.resources.subprocess.run") as execute:
        with pytest.raises(ValueError, match="undeclared.*e_002"):
            prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                                tmp_path / "output", tmp_path / "downloads", inputs)
    execute.assert_not_called()


def test_stage_data_context_includes_source_notice_without_invented_license(tmp_path):
    record = copy.deepcopy(RECORDS[DATA_ID])
    payload = lzma.compress(b"fixture plain\n", format=lzma.FORMAT_XZ,
                            check=lzma.CHECK_CRC64, preset=6)
    rows = [{"path": "app/instances/e_001.xz", "bytes": len(payload),
             "sha256": hashlib.sha256(payload).hexdigest(), "mode": "0644"}]
    manifest = tmp_path / record["files_manifest"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": rows}))
    record["manifest_sha256"] = digest(manifest)
    recipe = tmp_path / record["recipe"]
    recipe.write_text(json.dumps({"description": "no data license"}))
    evidence = tmp_path / EVIDENCE
    evidence.parent.mkdir(parents=True)
    evidence.write_text((ROOT / EVIDENCE).read_text())
    dockerfile = tmp_path / "assets/data/Dockerfile"
    dockerfile.write_text("FROM scratch\nCOPY rootfs/ /payload/rootfs/\n")
    (tmp_path / "assets/images.json").write_text(json.dumps({"images": [record]}))
    rootfs_file = tmp_path / "rootfs/app/instances/e_001.xz"
    rootfs_file.parent.mkdir(parents=True)
    rootfs_file.write_bytes(payload)
    rootfs_file.chmod(0o644)
    context = stage_data_context(tmp_path, DATA_ID, tmp_path / "rootfs", tmp_path / "context")
    notice = context / "licenses/dfvs-pace2022-source.json"
    assert json.loads(notice.read_text())["public_development_data"]["license_review"][
        "public_upload_allowed"] is False
    assert [path.name for path in (context / "licenses").iterdir()] == [notice.name]
    assert not (context / "licenses/PACE-CC0-1.0.txt").exists()
    assert (context / "rootfs/app/instances/e_001.xz").read_bytes() == payload


def test_inventory_refresh_changes_only_public_odd_dfvs_classification(tmp_path):
    public = f"tasks/solver/online/{TASK}/environment/app/instances/e_001.xz"
    even = f"tasks/solver/online/{TASK}/environment/app/instances/e_002.xz"
    hidden = f"tasks/solver/online/{TASK}/tests/instances/e_001.xz"
    answer = f"tasks/solver/online/{TASK}/solution/precomputed/e_001.out"
    unrelated = "tasks/theorem/example/environment/app/Main.lean"
    for path, expected in ((public, "local_prepare"), (even, "unresolved"),
                           (hidden, "unresolved"), (answer, "private_only")):
        assert classification(path)[1] == expected
    assert classification(public) == ("public_development", "local_prepare", EVIDENCE)
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
    assert updated[public]["distribution"] == "local_prepare"
    assert updated[public]["distribution_evidence"] == EVIDENCE
    assert updated[even]["distribution"] == "unresolved"
    assert updated[hidden]["distribution"] == "unresolved"
    assert updated[answer]["distribution"] == "private_only"
    assert all(row["retained_field"] == "unchanged" for row in updated.values())
