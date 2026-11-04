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
from tcsexam.checks import internal_reference_categories
from tcsexam.inventory import classification, refresh
from tcsexam.resources import content_digest, digest, stage_data_context
from tcsexam.vc_pace2019 import prepare_public_data


ROOT = Path(__file__).resolve().parents[3]
TASK = "vc-pace2019"
DATA_ID = "solver-vc-pace2019-development-data"
EVIDENCE = ROOT / "docs/licenses/third-party/vc-pace2019-source.json"
EVIDENCE_NAME = "docs/licenses/third-party/vc-pace2019-source.json"
NOTICE = ROOT / "docs/licenses/third-party/PACE2019-VC-NOTICE.txt"
IMAGES = json.loads((ROOT / "assets/images.json").read_text())["images"]
RECORDS = {row["id"]: row for row in IMAGES if row.get("id")}


def load(path):
    path = Path(path)
    return json.loads((ROOT / path).read_text() if not path.is_absolute() else path.read_text())


def test_public_recipe_manifest_and_distribution_scope():
    record = RECORDS[DATA_ID]
    recipe = load(record["recipe"])
    rows = load(record["files_manifest"])["files"]
    assert [row["path"] for row in rows] == [
        f"app/instances/vc-exact_{number:03d}.xz" for number in range(1, 200, 2)
    ]
    assert len(rows) == record["files"] == 100
    assert sum(row["bytes"] for row in rows) == record["bytes"] == 3899952
    assert {row["mode"] for row in rows} == {"0644"}
    assert digest(ROOT / record["files_manifest"]) == record["manifest_sha256"] == (
        "69d2e5e44465137d02a1f09cf49584bcd54744197eb77cf9a1a3b1bf41a9ad9d"
    )
    assert content_digest(rows, "/") == record["content_digest"] == (
        "sha256:9726aa143e63cd36b73d76029ebaa670b865a06110e64bcd883783b4fa2be82f"
    )
    assert recipe["source"] == record["source_input"] == {
        "id": "pace-2019-vc-exact-public-v2-tar-bz2",
        "url": "https://pacechallenge.org/files/pace2019-vc-exact-public-v2.tar.bz2",
        "bytes": 10695845,
        "sha256": "c78177cb5b2f7468bc652bd6e082f002495b26ba220bdc8eee9993ac6ff834c6",
    }
    assert recipe["archive_format"] == "tar.bz2"
    assert recipe["selection"] == {
        "source_root": "public",
        "output_directory": "app/instances",
        "first_instance": 1,
        "last_instance": 199,
        "instance_step": 2,
        "instance_count": 100,
    }
    assert recipe["compression"]["arguments"] == [
        "--format=xz", "--stdout", "--check=crc64"
    ]
    assert recipe["compression"]["preset"] == 9
    assert recipe["compression"]["preset_overrides"] == {}
    assert "threads" not in recipe["compression"]
    assert recipe["compression"]["tool"]["version"] == "5.2.5"
    assert recipe["compression"]["tool"]["source"] == {
        "id": "xz-utils-5.2.5-tar-gz",
        "url": "https://tukaani.org/xz/xz-5.2.5.tar.gz",
        "bytes": 1791345,
        "sha256": "f6f4910fd033078738bd82bfba4f49219d03b17eb0794eb91efbae419f4aba10",
    }
    assert "source_paths" not in recipe
    assert "source_input_file" not in record
    assert recipe["license_files"] == [
        {
            "path": "docs/licenses/third-party/PACE2019-VC-NOTICE.txt",
            "bytes": 2730,
            "sha256": "c02b5c550d669decf2712bc390a358f00aa1ca182b7eb67f1d830176c30a7f62",
        },
        {
            "path": "docs/licenses/CC-BY-4.0.txt",
            "bytes": 18657,
            "sha256": "9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411",
        },
    ]
    assert record["distribution"] == "redistributable"
    assert record["public_upload_allowed"] is True
    assert record["distribution_evidence"] == EVIDENCE_NAME
    assert record["product_prepared"] is False
    assert record["image_digest"] is None
    assert record["public_image"] is None
    assert record["public_pull_verified"] is False
    assert record["content_verified"] is True
    assert record["permissions_verified"] is True
    assert record["tool_version_verified"] is True
    assert record["public_source_rebuild_verified"] is True
    assert record["status"] == "local_preparation_required"
    assert record["previous_image_digest"] == (
        "sha256:597717afc13cb1c73ef8caaf9127b42a06ec9a716c64b176cfd921c1100bce28"
    )
    assert RECORDS[f"dev-online-{TASK}"]["distribution"] == "unresolved"
    assert RECORDS[f"dev-online-{TASK}"]["public_upload_allowed"] is False
    definition = build_definition(ROOT, record)
    assert definition["official_builder"] == recipe["build"]["builder_image"]
    assert recipe["generator_paths"] == ["src/tcsexam/vc_pace2019.py"]
    online = build_definition(ROOT, RECORDS[f"dev-online-{TASK}"])
    assert online["dependencies"] == [DATA_ID]
    offline = build_definition(ROOT, RECORDS[f"dev-offline-{TASK}"])
    assert offline["dependencies"] == [f"dev-online-{TASK}"]
    assert RECORDS[f"dev-offline-{TASK}"]["distribution"] == "unresolved"
    assert RECORDS[f"dev-offline-{TASK}"]["public_upload_allowed"] is False
    backend = build_definition(ROOT, RECORDS[f"backend-online-{TASK}"])
    assert backend["dependencies"] == sorted([f"dev-online-{TASK}",
                                               f"solver-{TASK}-judging-data"])
    public = build_definition(ROOT, RECORDS[f"backend-public-online-{TASK}"])
    assert public["dependencies"] == sorted([f"dev-online-{TASK}", DATA_ID])
    verifier = build_definition(ROOT, RECORDS[f"verifier-offline-{TASK}"])
    assert verifier["dependencies"] == [f"backend-online-{TASK}"]
    for identity in (f"{TASK}-backend-base", f"backend-online-{TASK}",
                     f"verifier-offline-{TASK}"):
        assert RECORDS[identity]["distribution"] == "unresolved"
        assert RECORDS[identity]["public_upload_allowed"] is False
        assert RECORDS[identity]["public_image"] is None


def test_official_sources_license_and_frozen_manifest_are_consistent():
    evidence = load(EVIDENCE)
    public = evidence["public_development_data"]
    manifest_path = ROOT / public["manifest"]
    rows = load(manifest_path)["files"]
    assert len(rows) == public["output_files"] == 100
    assert sum(row["bytes"] for row in rows) == public["output_bytes"] == 3899952
    assert digest(manifest_path) == public["manifest_sha256"]
    assert content_digest(rows, "/") == public["content_digest"]
    assert public["upstream"]["archive_bytes"] == 10695845
    assert public["upstream"]["archive_sha256"] == (
        "c78177cb5b2f7468bc652bd6e082f002495b26ba220bdc8eee9993ac6ff834c6"
    )
    assert public["upstream"]["per_file_sha1_matches"] == 100
    assert public["second_source"]["public_odd_plain_files_byte_identical_to_public_v2"] == 100
    assert public["second_source"]["even_numbered_instances_in_scope"] is False
    assert public["transform"]["xz_arguments"] == [
        "--format=xz", "--stdout", "--check=crc64", "-9"
    ]
    assert public["transform"]["multithreading_argument_used"] is False
    assert public["transform"]["plaintext_changed"] is False
    assert public["original_graph_provenance"]["independent_per_family_license_review_completed"] is False


def test_cc_by_notice_has_required_attribution_sources_and_modification_statement():
    evidence = load(EVIDENCE)
    public = evidence["public_development_data"]
    license_record = public["license"]
    license_path = ROOT / license_record["local_copy"]
    assert license_record["spdx"] == "CC-BY-4.0"
    assert digest(license_path) == license_record["sha256"]
    assert license_path.stat().st_size == license_record["bytes"] == 18657
    assert digest(NOTICE) == license_record["notice_sha256"]
    assert NOTICE.stat().st_size == license_record["notice_bytes"]
    notice = NOTICE.read_text()
    for expected in (
            *public["second_source"]["authors"],
            public["second_source"]["title"],
            "https://doi.org/10.5281/zenodo.3368306",
            public["upstream"]["archive_url"],
            public["upstream"]["official_per_file_sha1_listing"],
            "https://creativecommons.org/licenses/by/4.0/legalcode#s5",
            "--format=xz --stdout --check=crc64 -9",
            "The graph plaintext was not changed.",
            public["original_graph_provenance"]["report"],
            *public["original_graph_provenance"]["families"]):
        assert expected in notice
    resource = RECORDS[DATA_ID]
    recipe = load(resource["recipe"])
    rows = load(resource["files_manifest"])["files"]
    assert resource["data_split"] == "public"
    assert all(row["path"].startswith("app/instances/") for row in rows)
    assert recipe["selection"]["first_instance"] == 1
    assert recipe["selection"]["last_instance"] == 199
    assert recipe["selection"]["instance_step"] == 2
    assert {row["path"] for row in recipe["license_files"]} == {
        license_record["local_copy"], NOTICE.relative_to(ROOT).as_posix()
    }
    for row in recipe["license_files"]:
        assert digest(ROOT / row["path"]) == row["sha256"]
        assert (ROOT / row["path"]).stat().st_size == row["bytes"]
    assert resource["distribution"] == "redistributable"
    assert resource["public_image"] is None
    assert internal_reference_categories(EVIDENCE.read_text()) == []
    decisions = load("docs/licenses/third-party/distribution-decisions.json")
    assert decisions["integration_complete"] is False
    assert decisions["enforced_by_exporter"] is False
    decision = next(row for row in decisions["resources"]
                    if row["id"] == "vc-pace2019-public-development-data")
    assert decision["licenses"] == ["CC-BY-4.0"]
    assert decision["accepted_fixed_products"] == [DATA_ID]
    assert decision["original_graph_family_license_review_completed"] is False
    assert "Even-numbered instances" in decision["decision_scope"]
    assert "hidden judging data" in decision["decision_scope"]
    assert "solution/precomputed answers" in decision["decision_scope"]
    assert internal_reference_categories(notice) == []


def _write_preparation_fixture(tmp_path, wrong_plaintext=False):
    recipe = copy.deepcopy(load(RECORDS[DATA_ID]["recipe"]))
    archive = tmp_path / "public.tar.bz2"
    plain = {
        f"vc-exact_{number:03d}.gr": f"p edge 1 0\nc VC fixture {number:03d}\n".encode()
        for number in range(1, 200, 2)
    }
    with tarfile.open(archive, "w:bz2") as output:
        directory = tarfile.TarInfo("public")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        output.addfile(directory)
        for number in range(1, 200, 2):
            stem = f"vc-exact_{number:03d}.gr"
            data = plain[stem]
            member = tarfile.TarInfo(f"public/{stem}")
            member.size = len(data)
            member.mode = 0o644
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
        stem = f"vc-exact_{number:03d}"
        source = (b"wrong official plaintext\n" if wrong_plaintext and number == 1
                  else plain[stem + ".gr"])
        data = lzma.compress(source, format=lzma.FORMAT_XZ,
                             check=lzma.CHECK_CRC64, preset=9)
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
                        and row["path"].endswith("vc-exact_001.xz")
                        else compressed[row["path"]])
                path = destination / Path(row["path"]).name
                path.write_bytes(data)
                path.chmod(0o644)
        return CompletedProcess(command, 0, stdout="", stderr="")

    with patch("tcsexam.vc_pace2019.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.resources.subprocess.run", side_effect=execute):
        prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                            output, tmp_path / "downloads", inputs)
    return output, commands


def test_prepare_recreates_100_outputs_with_docker_cp_and_fixed_xz(tmp_path):
    output, commands = _run_fixture_preparation(tmp_path)
    files = sorted(path for path in output.rglob("*") if path.is_file())
    assert len(files) == 100
    assert [path.name for path in files] == [f"vc-exact_{number:03d}.xz"
                                              for number in range(1, 200, 2)]
    assert {path.stat().st_mode & 0o777 for path in files} == {0o644}
    create = next(command for command in commands if command[1] == "create")
    assert create[:2] == ["docker", "create"]
    assert "--pull=never" in create
    script = create[-1]
    assert "xz (XZ Utils) 5.2.5" in script
    assert "liblzma 5.2.5" in script
    assert "--format=xz --stdout --check=crc64 -9" in script
    assert "--threads" not in script
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
    with patch("tcsexam.vc_pace2019.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.resources.subprocess.run") as execute:
        with pytest.raises(ValueError, match="hash or size differs"):
            prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                                tmp_path / "output", tmp_path / "downloads", inputs)
    execute.assert_not_called()


def test_prepare_rejects_wrong_instance_set(tmp_path):
    recipe, rows, inputs, _ = _write_preparation_fixture(tmp_path)
    original = inputs[recipe["source"]["id"]]
    replacement = tmp_path / "wrong-instances.tar.bz2"
    with tarfile.open(original, "r:bz2") as source, tarfile.open(replacement, "w:bz2") as output:
        for member in source:
            if member.name == "public/vc-exact_001.gr":
                member.name = "public/vc-exact_002.gr"
            output.addfile(member, source.extractfile(member) if member.isfile() else None)
    recipe["source"].update(bytes=replacement.stat().st_size, sha256=digest(replacement))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    inputs[recipe["source"]["id"]] = replacement
    with patch("tcsexam.vc_pace2019.acquire_official_builder", return_value="fixed-builder"), \
            patch("tcsexam.resources.subprocess.run") as execute:
        with pytest.raises(ValueError, match="undeclared.*vc-exact_002"):
            prepare_public_data(tmp_path, {"id": DATA_ID, "recipe": "recipe.json"}, rows,
                                tmp_path / "output", tmp_path / "downloads", inputs)
    execute.assert_not_called()


def _stage_fixture(tmp_path):
    record = copy.deepcopy(RECORDS[DATA_ID])
    payload = lzma.compress(b"fixture plain\n", format=lzma.FORMAT_XZ,
                            check=lzma.CHECK_CRC64, preset=9)
    rows = [{"path": "app/instances/vc-exact_001.xz", "bytes": len(payload),
             "sha256": hashlib.sha256(payload).hexdigest(), "mode": "0644"}]
    manifest = tmp_path / record["files_manifest"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": rows}))
    record["manifest_sha256"] = digest(manifest)
    recipe = tmp_path / record["recipe"]
    recipe.parent.mkdir(parents=True, exist_ok=True)
    recipe.write_text(json.dumps(load(record["recipe"])))
    evidence = tmp_path / EVIDENCE_NAME
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(EVIDENCE.read_text())
    for declaration in load(record["recipe"])["license_files"]:
        source = ROOT / declaration["path"]
        destination = tmp_path / declaration["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    dockerfile = tmp_path / "assets/data/Dockerfile"
    dockerfile.parent.mkdir(parents=True, exist_ok=True)
    dockerfile.write_text("FROM scratch\nCOPY rootfs/ /payload/rootfs/\n")
    (tmp_path / "assets/images.json").write_text(json.dumps({"images": [record]}))
    rootfs_file = tmp_path / "rootfs/app/instances/vc-exact_001.xz"
    rootfs_file.parent.mkdir(parents=True)
    rootfs_file.write_bytes(payload)
    rootfs_file.chmod(0o644)
    return record, payload


def test_stage_data_context_includes_cc_by_notice_and_source_record(tmp_path):
    _, payload = _stage_fixture(tmp_path)
    context = stage_data_context(tmp_path, DATA_ID, tmp_path / "rootfs", tmp_path / "context")
    names = sorted(path.name for path in (context / "licenses").iterdir())
    assert names == ["CC-BY-4.0.txt", "PACE2019-VC-NOTICE.txt", "vc-pace2019-source.json"]
    for name in names:
        source = EVIDENCE if name == EVIDENCE.name else NOTICE if name == NOTICE.name else (
            ROOT / "docs/licenses/CC-BY-4.0.txt")
        assert (context / "licenses" / name).read_bytes() == source.read_bytes()
    assert (context / "rootfs/app/instances/vc-exact_001.xz").read_bytes() == payload
    metadata = json.loads((context / "manifest/content.json").read_text())
    assert metadata["distribution"] == "redistributable"
    assert metadata["public_upload_allowed"] is True


def test_stage_data_context_rejects_changed_license_bytes(tmp_path):
    _stage_fixture(tmp_path)
    notice = tmp_path / "docs/licenses/third-party/PACE2019-VC-NOTICE.txt"
    notice.write_bytes(notice.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="license hash or size differs"):
        stage_data_context(tmp_path, DATA_ID, tmp_path / "rootfs", tmp_path / "context")


def test_inventory_refresh_changes_only_public_odd_vc_classification(tmp_path):
    public = f"tasks/solver/online/{TASK}/environment/app/instances/vc-exact_001.xz"
    even = f"tasks/solver/online/{TASK}/environment/app/instances/vc-exact_002.xz"
    hidden = f"tasks/solver/online/{TASK}/tests/instances/vc-exact_001.xz"
    answer = f"tasks/solver/online/{TASK}/solution/precomputed/vc-exact_001.out"
    verifier = f"tasks/solver/online/{TASK}/environment/app/vc_validate.cpp"
    unrelated = "tasks/theorem/example/environment/app/Main.lean"
    for path, expected in ((public, "redistributable"), (even, "unresolved"),
                           (hidden, "unresolved"), (answer, "private_only"),
                           (verifier, "unresolved")):
        assert classification(path)[1] == expected
    assert classification(public) == ("public_development", "redistributable", EVIDENCE_NAME)
    assets = tmp_path / "assets"
    assets.mkdir()
    rows = [{"path": path, "bytes": 1, "retained_field": "unchanged"}
            for path in (public, even, hidden, answer, verifier, unrelated)]
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
    assert updated[public]["distribution_evidence"] == EVIDENCE_NAME
    for path in (even, hidden, verifier):
        assert updated[path]["distribution"] == "unresolved"
    assert updated[answer]["distribution"] == "private_only"
    assert all(row["retained_field"] == "unchanged" for row in updated.values())
