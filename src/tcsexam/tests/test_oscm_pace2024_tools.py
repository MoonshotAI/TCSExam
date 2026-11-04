import base64
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
from tcsexam.oscm_pace2024_tools import prepare_tools
from tcsexam.resources import content_digest, digest, stage_data_context


ROOT = Path(__file__).resolve().parents[3]
TOOLS_ID = "solver-oscm-pace2024-development-tools"
DATA_ID = "solver-oscm-pace2024-development-data"
EVIDENCE = "docs/licenses/third-party/oscm-pace2024-development-tools-source.json"
WHEEL_NAME = "numpy-2.2.6-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
WHEEL_URL = ("https://files.pythonhosted.org/packages/8c/3d/1e1db36cfd41f895d266b103df00ca5b3cbe965184df824dec5c08c6b803/"
             + WHEEL_NAME)
RECORDS = {
    row["id"]: row
    for row in json.loads((ROOT / "assets/images.json").read_text())["images"]
    if row.get("id")
}


def load(path):
    return json.loads((ROOT / path).read_text())


def test_official_wheel_recipe_manifest_and_build_scope():
    record = RECORDS[TOOLS_ID]
    recipe = load(record["recipe"])
    rows = load(record["files_manifest"])["files"]
    assert len(rows) == record["files"] == 1
    assert sum(row["bytes"] for row in rows) == record["bytes"] == 16527618
    assert rows[0]["path"] == "opt/ocm/pkg/" + WHEEL_NAME
    assert rows[0]["sha256"] == "fd83c01228a688733f1ded5201c678f0c53ecc1006ffbc404db9f7a899ac6249"
    assert rows[0]["mode"] == "0644"
    assert digest(ROOT / record["files_manifest"]) == record["manifest_sha256"] == (
        "00a55847d74703c5b082f2c242883be752d8bffdf734e7234547c4342ae8da03"
    )
    assert content_digest(rows, "/") == record["content_digest"]
    assert record["recipe_format"] == "official_wheel"
    assert recipe["archive_format"] == "wheel"
    assert recipe["source"] == record["source_input"] == {
        "id": "numpy-2.2.6-cp312-manylinux2014-x86-64-wheel",
        "url": WHEEL_URL,
        "bytes": 16527618,
        "sha256": "fd83c01228a688733f1ded5201c678f0c53ecc1006ffbc404db9f7a899ac6249",
    }
    assert "source_input_file" not in record
    assert "source_paths" not in recipe
    assert recipe["wheel"]["record_member"] == "numpy-2.2.6.dist-info/RECORD"
    assert recipe["wheel"]["record_bytes"] == 81729
    assert recipe["wheel"]["record_sha256"] == (
        "5eecf4a4205999a329c70c5003c419d03212a394f01cd75ef719539f0675357a"
    )
    assert recipe["wheel"]["file_members"] == 876
    assert len(recipe["wheel"]["notice_members"]) == len(recipe["license_files"]) == 4
    assert recipe["generator_paths"] == ["src/tcsexam/oscm_pace2024_tools.py"]
    assert record["distribution"] == "local_prepare"
    assert record["public_upload_allowed"] is False
    assert record["distribution_evidence"] == EVIDENCE
    assert record["build_argument"] == "TCSEXAM_TOOLS_IMAGE"
    assert record["product_prepared"] is False
    assert record["image_digest"] is None
    assert record["public_image"] is None
    assert record["public_pull_verified"] is False
    assert record["status"] == "local_preparation_required"
    assert record["previous_image_digest"] == (
        "sha256:37f6dd018b3aa2c8a258a1e7a2671bfdf3aa1c02af8296db9487fce918a2face"
    )
    definition = build_definition(ROOT, record)
    assert definition["official_builder"] == recipe["build"]["builder_image"]
    assert definition["pull_args"] == {
        "TCSEXAM_OFFICIAL_BUILDER": recipe["build"]["builder_image"]
    }
    online = build_definition(ROOT, RECORDS["dev-online-oscm-pace2024"])
    assert online["dependencies"] == sorted([TOOLS_ID, DATA_ID])
    assert RECORDS[DATA_ID]["distribution"] == "local_prepare"
    assert RECORDS[DATA_ID]["recipe_format"] == "official_zip"
    for identity in ("dev-online-oscm-pace2024", "dev-offline-oscm-pace2024",
                     "backend-online-oscm-pace2024", "backend-public-online-oscm-pace2024"):
        assert RECORDS[identity]["distribution"] == "unresolved"
        assert RECORDS[identity]["public_upload_allowed"] is False


def test_tools_source_record_preserves_notice_scope_without_publication():
    evidence = load(EVIDENCE)
    assert evidence["product"]["distribution"] == "local_prepare"
    assert evidence["product"]["public_upload_allowed"] is False
    assert evidence["product"]["derived_image_public_upload_allowed"] is False
    assert evidence["upstream"]["wheel_url"] == WHEEL_URL
    assert evidence["upstream"]["wheel_sha256"] == RECORDS[TOOLS_ID]["source_input"]["sha256"]
    review = evidence["notice_review"]
    assert review["wheel_notice_members_reviewed"] is True
    assert review["complete_bundled_dependency_license_review"] is False
    assert review["corresponding_source_obligations_reviewed"] is False
    assert len(review["files"]) == 4
    for row in review["files"]:
        path = ROOT / row["local_copy"]
        assert path.stat().st_size == row["bytes"]
        assert digest(path) == row["sha256"]
        matching = [item for item in load(RECORDS[TOOLS_ID]["recipe"])["wheel"]["notice_members"]
                    if item["member"] == row["member"]]
        assert len(matching) == 1
        assert matching[0]["path"] == row["local_copy"]
    names = {row["name"] for row in review["bundled_components_named_by_upstream_notice"]}
    assert {"OpenBLAS", "LAPACK", "GCC runtime library", "libquadmath", "libdivide"} <= names
    main_notice = (ROOT / "docs/licenses/third-party/NumPy-2.2.6-LICENSE.txt").read_text()
    for expected in ("Copyright (c) 2005-2024, NumPy Developers.", "Name: OpenBLAS",
                     "Name: LAPACK", "Name: GCC runtime library", "Name: libquadmath",
                     "GCC RUNTIME LIBRARY EXCEPTION"):
        assert expected in main_notice
    assert evidence["verification"]["manual_cached_tool_product_used_as_production_recipe"] is False
    assert evidence["verification"]["public_upload_performed"] is False
    from tcsexam.checks import internal_reference_categories
    assert internal_reference_categories(json.dumps(evidence)) == []
    decisions = load("docs/licenses/third-party/distribution-decisions.json")
    assert decisions["integration_complete"] is False
    assert decisions["enforced_by_exporter"] is False
    decision = next(row for row in decisions["resources"]
                    if row["id"] == "oscm-pace2024-development-tools-local-preparation")
    assert decision["local_preparation_products"] == [TOOLS_ID]
    assert decision["public_upload_allowed"] is False
    assert decision["complete_bundled_dependency_license_review"] is False
    assert decision["corresponding_source_obligations_reviewed"] is False
    assert "accepted_fixed_products" not in decision
    assert "other verifier wheels" in decision["decision_scope"]


def _record_row(name, data):
    encoded = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"{name},sha256={encoded},{len(data)}"


def _write_preparation_fixture(tmp_path):
    recipe = copy.deepcopy(load(RECORDS[TOOLS_ID]["recipe"]))
    for declaration in recipe["license_files"]:
        destination = tmp_path / declaration["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / declaration["path"]).read_bytes())
    contents = {
        "numpy/__init__.py": b"# synthetic NumPy fixture\n",
        "numpy-2.2.6.dist-info/METADATA": b"Name: numpy\nVersion: 2.2.6\n",
    }
    for declaration in recipe["wheel"]["notice_members"]:
        contents[declaration["member"]] = (tmp_path / declaration["path"]).read_bytes()
    record_name = recipe["wheel"]["record_member"]
    record = "\n".join([_record_row(name, data) for name, data in contents.items()]
                       + [f"{record_name},,"]) + "\n"
    contents[record_name] = record.encode()
    wheel = tmp_path / WHEEL_NAME
    with zipfile.ZipFile(wheel, "w") as output:
        output.writestr("numpy/", b"")
        output.writestr("numpy-2.2.6.dist-info/", b"")
        for name, data in contents.items():
            output.writestr(name, data)
    recipe["wheel"].update(record_bytes=len(contents[record_name]),
                           record_sha256=hashlib.sha256(contents[record_name]).hexdigest(),
                           file_members=len(contents))
    recipe["source"].update(url=None, bytes=wheel.stat().st_size, sha256=digest(wheel))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    original = load(RECORDS[TOOLS_ID]["files_manifest"])["files"][0]
    row = {"path": original["path"], "bytes": recipe["source"]["bytes"],
           "sha256": recipe["source"]["sha256"], "mode": "0644"}
    return recipe, [row], {recipe["source"]["id"]: wheel}


def _accept_changed_archive(tmp_path, recipe, rows, inputs):
    archive = inputs[recipe["source"]["id"]]
    recipe["source"].update(bytes=archive.stat().st_size, sha256=digest(archive))
    rows[0].update(bytes=archive.stat().st_size, sha256=digest(archive))
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))


def _prepare(tmp_path, recipe, rows, inputs):
    prepare_tools(tmp_path, {"id": TOOLS_ID, "recipe": "recipe.json"}, rows,
                  tmp_path / "output", tmp_path / "downloads", inputs)


def test_prepare_recreates_exact_wheel_and_checks_all_record_members(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    _prepare(tmp_path, recipe, rows, inputs)
    output = tmp_path / "output" / rows[0]["path"]
    assert output.read_bytes() == inputs[recipe["source"]["id"]].read_bytes()
    assert output.stat().st_mode & 0o777 == 0o644
    assert digest(output) == rows[0]["sha256"]


def test_prepare_automatically_downloads_official_wheel_with_fixed_builder(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    recipe["source"]["url"] = WHEEL_URL
    (tmp_path / "recipe.json").write_text(json.dumps(recipe))
    with patch("tcsexam.oscm_pace2024_tools.acquire_official_builder", return_value="fixed-builder") as builder, \
            patch("tcsexam.oscm_pace2024_tools.download_official",
                  return_value=inputs[recipe["source"]["id"]]) as download:
        prepare_tools(tmp_path, {"id": TOOLS_ID, "recipe": "recipe.json"}, rows,
                      tmp_path / "output", tmp_path / "downloads")
    builder.assert_called_once()
    assert download.call_args.args[0]["url"] == WHEEL_URL


def test_prepare_rejects_wrong_source_hash(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    archive.write_bytes(archive.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="hash or size differs"):
        _prepare(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_undeclared_member(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("numpy/undeclared.py", b"bad")
    _accept_changed_archive(tmp_path, recipe, rows, inputs)
    with pytest.raises(ValueError, match="Undeclared.*undeclared.py"):
        _prepare(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_duplicate_member(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("numpy/__init__.py", b"# duplicate")
    _accept_changed_archive(tmp_path, recipe, rows, inputs)
    with pytest.raises(ValueError, match="Duplicate NumPy wheel member"):
        _prepare(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_path_traversal(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    replacement = tmp_path / "traversal.whl"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            name = "../numpy/__init__.py" if member.filename == "numpy/__init__.py" else member.filename
            output.writestr(name, source.read(member))
    inputs[recipe["source"]["id"]] = replacement
    _accept_changed_archive(tmp_path, recipe, rows, inputs)
    with pytest.raises(ValueError, match="Unsafe archive path"):
        _prepare(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_link_member(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    replacement = tmp_path / "link.whl"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            if member.filename == "numpy/__init__.py":
                link = zipfile.ZipInfo(member.filename)
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                output.writestr(link, "target.py")
            else:
                output.writestr(member, source.read(member))
    inputs[recipe["source"]["id"]] = replacement
    _accept_changed_archive(tmp_path, recipe, rows, inputs)
    with pytest.raises(ValueError, match="special NumPy wheel member"):
        _prepare(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_undeclared_directory(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("undeclared/", b"")
    _accept_changed_archive(tmp_path, recipe, rows, inputs)
    with pytest.raises(ValueError, match="Undeclared NumPy wheel directory"):
        _prepare(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_record_content_mismatch(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    replacement = tmp_path / "record-mismatch.whl"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            data = b"changed without RECORD update" if member.filename == "numpy/__init__.py" else source.read(member)
            output.writestr(member, data)
    inputs[recipe["source"]["id"]] = replacement
    _accept_changed_archive(tmp_path, recipe, rows, inputs)
    with pytest.raises(ValueError, match="RECORD member.*differs"):
        _prepare(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_missing_record_member(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    archive = inputs[recipe["source"]["id"]]
    replacement = tmp_path / "missing.whl"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as output:
        for member in source.infolist():
            if member.filename != "numpy/__init__.py":
                output.writestr(member, source.read(member))
    inputs[recipe["source"]["id"]] = replacement
    _accept_changed_archive(tmp_path, recipe, rows, inputs)
    with pytest.raises(ValueError, match="missing RECORD members"):
        _prepare(tmp_path, recipe, rows, inputs)


def test_prepare_rejects_changed_staged_notice(tmp_path):
    recipe, rows, inputs = _write_preparation_fixture(tmp_path)
    notice = tmp_path / recipe["wheel"]["notice_members"][0]["path"]
    notice.write_bytes(notice.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Staged NumPy notice differs"):
        _prepare(tmp_path, recipe, rows, inputs)


def test_stage_data_context_contains_source_and_all_four_notices(tmp_path):
    record = copy.deepcopy(RECORDS[TOOLS_ID])
    payload = b"synthetic wheel bytes"
    rows = [{"path": "opt/ocm/pkg/" + WHEEL_NAME, "bytes": len(payload),
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
    for declaration in load(record["recipe"])["license_files"]:
        destination = tmp_path / declaration["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / declaration["path"]).read_bytes())
    dockerfile = tmp_path / "assets/data/Dockerfile"
    dockerfile.parent.mkdir(parents=True, exist_ok=True)
    dockerfile.write_text("FROM scratch\nCOPY rootfs/ /payload/rootfs/\n")
    (tmp_path / "assets/images.json").write_text(json.dumps({"images": [record]}))
    rootfs_file = tmp_path / "rootfs" / rows[0]["path"]
    rootfs_file.parent.mkdir(parents=True)
    rootfs_file.write_bytes(payload)
    rootfs_file.chmod(0o644)
    context = stage_data_context(tmp_path, TOOLS_ID, tmp_path / "rootfs", tmp_path / "context")
    names = sorted(path.name for path in (context / "licenses").iterdir())
    assert names == ["NumPy-2.2.6-LICENSE.txt", "NumPy-2.2.6-MA-LICENSE.txt",
                     "NumPy-2.2.6-RANDOM-C-LICENSE.txt", "NumPy-2.2.6-RANDOM-LICENSE.md",
                     "oscm-pace2024-development-tools-source.json"]
    metadata = json.loads((context / "manifest/content.json").read_text())
    assert metadata["distribution"] == "local_prepare"
    assert metadata["public_upload_allowed"] is False


def test_inventory_refresh_changes_only_numpy_tool_row(tmp_path):
    wheel = f"tasks/solver/online/oscm-pace2024/environment/app/verifier/{WHEEL_NAME}"
    other_wheel = "tasks/solver/online/oscm-pace2024/environment/app/verifier/click-8.4.2-py3-none-any.whl"
    public = "tasks/solver/online/oscm-pace2024/environment/app/instances/1.gr"
    assert classification(wheel) == ("public_development", "local_prepare", EVIDENCE)
    assert classification(other_wheel)[1] == "unresolved"
    assert classification(public) == (
        "public_development", "local_prepare", "docs/licenses/third-party/oscm-pace2024-source.json"
    )
    assets = tmp_path / "assets"
    assets.mkdir()
    rows = [{"path": path, "bytes": 1, "retained_field": "unchanged"}
            for path in (wheel, other_wheel, public)]
    (assets / "files.json").write_text(json.dumps({"files": rows}))
    images = json.dumps({"schema_version": 4, "images": [
        {"id": "lean-base", "build": {"kind": "custom", "retained": True}}
    ]}, indent=2) + "\n"
    (assets / "images.json").write_text(images)
    refresh(tmp_path)
    assert (assets / "images.json").read_text() == images
    updated = {row["path"]: row for row in json.loads((assets / "files.json").read_text())["files"]}
    assert updated[wheel]["distribution"] == "local_prepare"
    assert updated[wheel]["distribution_evidence"] == EVIDENCE
    assert updated[other_wheel]["distribution"] == "unresolved"
    assert updated[public]["distribution_evidence"] == "docs/licenses/third-party/oscm-pace2024-source.json"
    assert all(row["retained_field"] == "unchanged" for row in updated.values())
