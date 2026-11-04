"""Verify hidden DFVS preparation is reachable through the public build entry."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tcsexam.build import build_definition
from tcsexam.resources import digest, prepare_resource
from tcsexam.solver_data_recipes import product_patch


ROOT = Path(__file__).resolve().parents[3]
HIDDEN_ID = "solver-dfvs-pace2022-judging-data"


def test_hidden_product_keeps_exact_inputs_and_pinned_builder():
    record = next(row for row in product_patch(ROOT) if row["id"] == HIDDEN_ID)
    recipe = json.loads((ROOT / record["recipe"]).read_text())
    rows = json.loads((ROOT / record["files_manifest"]).read_text())["files"]
    assert record["recipe_format"] == "official_dfvs_xz"
    assert record["data_split"] == "hidden"
    assert record["target_root"] == "/"
    assert record["files"] == len(rows) == 200
    assert [row["path"] for row in rows] == [
        f"tests/instances/e_{number:03d}.xz" for number in range(1, 201)
    ]
    assert record["source_inputs"] == recipe["sources"]
    assert {row["id"] for row in record["source_inputs"]} == {
        "pace2022-exact-all"
    }
    assert recipe["graph_transform"]["id"] == "vertex-relabeling-v1"
    assert recipe["compression"] == {"format": "xz", "tool": "python-lzma",
        "liblzma_version": "5.2.5", "preset": 6, "check": "crc64", "threads": 1}
    assert "source_input_file" not in record
    assert record["distribution"] == "local_prepare"
    assert record["public_upload_allowed"] is False
    definition = build_definition(ROOT, record)
    assert definition["official_builder"] == recipe["build"]["builder_image"]
    assert definition["pull_args"] == {
        "TCSEXAM_OFFICIAL_BUILDER": recipe["build"]["builder_image"]
    }


@pytest.mark.parametrize("corrupt", [False, True])
def test_dispatch_keeps_validation_and_atomic_cache(tmp_path, corrupt):
    # Small routing fixture: no real archive, compiler, or Docker process runs.
    data = b"fixture payload"
    rows = [{"path": "tests/instances/e_001.xz", "bytes": len(data),
             "sha256": hashlib.sha256(data).hexdigest(), "mode": "0644"}]
    assets = tmp_path / "assets"
    assets.mkdir()
    manifest = assets / "files.json"
    manifest.write_text(json.dumps({"files": rows}))
    (assets / "recipe.json").write_text("{}")
    resource = {"id": HIDDEN_ID, "type": "data", "target_root": "/",
                "recipe": "assets/recipe.json", "recipe_format": "official_dfvs_xz",
                "files_manifest": "assets/files.json", "manifest_sha256": digest(manifest),
                "content_version": "test-fixed"}
    (assets / "images.json").write_text(json.dumps({"images": [resource]}))
    cache = tmp_path / "cache"
    inputs = {"pace2022-exact-all": tmp_path / "caller-supplied.tar.gz"}
    args = {"docker_host": "test-only"}

    def prepare(root, actual_resource, actual_rows, output, downloads, **kwargs):
        assert root == tmp_path
        assert actual_resource == resource
        assert actual_rows == rows
        assert downloads == cache / "downloads"
        assert kwargs == {"inputs": inputs, "args": args, "builder_image": "local-fixed-builder"}
        target = output / rows[0]["path"]
        target.parent.mkdir(parents=True)
        target.write_bytes(b"X" * len(data) if corrupt else data)
        target.chmod(0o644)

    with patch("tcsexam.dfvs_pace2022.prepare_public_data", side_effect=prepare) as adapter:
        if corrupt:
            with pytest.raises(ValueError, match="Content differs"):
                prepare_resource(tmp_path, HIDDEN_ID, cache, inputs, args, "local-fixed-builder")
            assert not (cache / HIDDEN_ID / "test-fixed").exists()
        else:
            rootfs = prepare_resource(tmp_path, HIDDEN_ID, cache, inputs, args, "local-fixed-builder")
            assert (rootfs / rows[0]["path"]).read_bytes() == data
            assert (rootfs.parent / ".complete.json").is_file()
            assert prepare_resource(tmp_path, HIDDEN_ID, cache, inputs, args, "local-fixed-builder") == rootfs
        adapter.assert_called_once()
    assert not list((cache / HIDDEN_ID).glob(".preparing-*"))
