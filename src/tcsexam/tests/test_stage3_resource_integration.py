"""Exercise source-recipe routing without running compilers or data conversion."""
import hashlib
import json
import lzma
from pathlib import Path
from unittest.mock import patch

import pytest

from tcsexam.build import build_definition
from tcsexam.maxsat_data import PLAINTEXT_CONTRACT
from tcsexam.resources import content_digest, digest, prepare_resource
from tcsexam.solver_data_recipes import product_patch


ROOT = Path(__file__).resolve().parents[3]
ADAPTERS = [
    ("official_ce_xz", "tcsexam.ce_pace2021.prepare_public_data"),
    ("official_vc_xz", "tcsexam.vc_pace2019.prepare_public_data"),
    ("official_gp_generator", "tcsexam.gp_data.prepare_data"),
    ("official_maxsat_generator", "tcsexam.maxsat_data.prepare_data"),
]
PRODUCTS = [
    ("ce-pace2021", "judging", "official_ce_xz", 100),
    ("vc-pace2019", "judging", "official_vc_xz", 100),
    ("gp-dimacs10", "development", "official_gp_generator", 27),
    ("gp-dimacs10", "judging", "official_gp_generator", 13),
    ("maxsat-mse", "development", "official_maxsat_generator", 15),
]


@pytest.mark.parametrize("task,split,recipe_format,count", PRODUCTS)
def test_verified_recipe_is_reachable_with_unchanged_payload(task, split, recipe_format, count):
    name = f"solver-{task}-{split}-data"
    record = next(row for row in product_patch(ROOT) if row["id"] == name)
    recipe = json.loads((ROOT / record["recipe"]).read_text())
    manifest = json.loads((ROOT / record["files_manifest"]).read_text())["files"]
    assert record["recipe_format"] == recipe_format
    assert record["files"] == len(manifest) == count
    assert record["content_digest"] == content_digest(manifest, "/")
    assert record["source_inputs"] == recipe["sources"]
    assert "source_input_file" not in record
    assert record["data_split"] == ("hidden" if split == "judging" else "public")
    assert record["distribution"] == "local_prepare"
    assert record["public_upload_allowed"] is False
    definition = build_definition(ROOT, record)
    assert definition["official_builder"] == recipe["build"]["builder_image"]
    assert definition["pull_args"] == {
        "TCSEXAM_OFFICIAL_BUILDER": recipe["build"]["builder_image"]
    }


@pytest.mark.parametrize("recipe_format,adapter_path", ADAPTERS)
@pytest.mark.parametrize("corrupt", [False, True])
def test_dispatch_preserves_arguments_and_rejects_changed_bytes(tmp_path, recipe_format, adapter_path, corrupt):
    data = b"fixed fixture bytes"
    maxsat = recipe_format == 'official_maxsat_generator'
    plain = b'p wcnf 1 1 2\n1 -1 0\n'
    if maxsat:
        data = lzma.compress(plain)
    rows = [{"path": "tests/instances/one.wcnf.xz" if maxsat else "tests/instances/one.dat", "bytes": len(data),
             "sha256": hashlib.sha256(data).hexdigest(), "mode": "0644"}]
    assets = tmp_path / "assets"
    assets.mkdir()
    manifest = assets / "files.json"
    manifest.write_text(json.dumps({"files": rows}))
    recipe = {}
    if maxsat:
        worker = assets / 'worker.py'
        worker.write_text('# fixture conversion worker\n')
        recipe = {'format': recipe_format, 'content_version': 'fixed-v1',
                  'plaintext_contract': PLAINTEXT_CONTRACT,
                  'archive_source_id': 'official-archive', 'xz_source_id': 'xz-source',
                  'sources': [{'id': identity, 'filename': name, 'url': 'https://example.com/' + name,
                               'bytes': 1, 'sha256': hashlib.sha256(b'x').hexdigest()}
                              for identity, name in [('official-archive', 'instances.zip'),
                                                     ('xz-source', 'xz-source.tar.gz')]],
                  'implementation_files': {'assets/worker.py': {'destination': 'worker.py',
                                                               'sha256': digest(worker)}},
                  'build': {'builder_image': 'ubuntu:22.04@sha256:' + '1' * 64, 'cwd': '.',
                            'timeout_sec': 60},
                  'outputs': [{'path': rows[0]['path'], 'operation': 'maxsat_relabel',
                               'canonical_format': 'original-v1',
                               'source_id': 'official-archive', 'source_member': 'weighted/one.wcnf.xz',
                               'source_member_bytes': len(data), 'source_expanded_limit_bytes': 1024,
                               'source_sha256_plain': hashlib.sha256(
                                   b'c converted from MSE new format (h-lines, no p-line)\n' + plain).hexdigest(),
                               'output_sha256_plain': hashlib.sha256(plain).hexdigest(),
                               'output_plaintext_bytes': len(plain), 'original_seed_name': 'one.wcnf',
                               'seed_hex': hashlib.sha256(b'tcshard-transform-20260831:one.wcnf').digest()[:8].hex(),
                               'nvars': 1, 'nclauses': 1, 'top': 2}]}
    (assets / "recipe.json").write_text(json.dumps(recipe))
    resource = {"id": "fixture", "type": "data", "target_root": "/",
                "recipe": "assets/recipe.json", "recipe_format": recipe_format,
                "files_manifest": "assets/files.json", "manifest_sha256": digest(manifest),
                "content_version": "fixed-v1"}
    (assets / "images.json").write_text(json.dumps({"images": [resource]}))
    cache = tmp_path / "cache"
    inputs = {"original-archive": tmp_path / "supplied.tar.gz"}
    args = {"docker_context": "fixture-only"}

    def adapter(root, actual_resource, actual_rows, output, downloads, **kwargs):
        assert root == tmp_path and actual_resource == resource and actual_rows == rows
        assert downloads == cache / "downloads"
        assert kwargs == {"inputs": inputs, "args": args, "builder_image": "local-fixed-image"}
        target = output / rows[0]["path"]
        target.parent.mkdir(parents=True)
        target.write_bytes(b"X" * len(data) if corrupt else data)
        target.chmod(0o644)

    with patch(adapter_path, side_effect=adapter) as call:
        if corrupt:
            with pytest.raises(ValueError, match="Content differs"):
                prepare_resource(tmp_path, "fixture", cache, inputs, args, "local-fixed-image")
            assert not (cache / "fixture/fixed-v1").exists()
        else:
            rootfs = prepare_resource(tmp_path, "fixture", cache, inputs, args, "local-fixed-image")
            assert (rootfs / rows[0]["path"]).read_bytes() == data
            assert (rootfs.parent / ".complete.json").is_file()
            if maxsat:
                marker = json.loads((rootfs.parent / '.complete.json').read_text())
                assert marker['maxsat_plaintext_contract'] == PLAINTEXT_CONTRACT
                assert marker['maxsat_recipe_sha256'] == digest(assets / 'recipe.json')
            assert prepare_resource(tmp_path, "fixture", cache, inputs, args, "local-fixed-image") == rootfs
        call.assert_called_once()
    assert not list((cache / "fixture").glob(".preparing-*"))


@pytest.mark.parametrize("recipe_format,_adapter", ADAPTERS)
def test_generator_change_invalidates_build_identity(tmp_path, recipe_format, _adapter):
    # The output identity stays fixed; changed generation code must invalidate
    # the build cache so an old conversion cannot silently satisfy a new recipe.
    (tmp_path / "src/tcsexam").mkdir(parents=True)
    (tmp_path / "assets/data").mkdir(parents=True)
    (tmp_path / "assets/data/Dockerfile").write_text('FROM scratch\nCOPY rootfs/ /\n')
    (tmp_path / "src/tcsexam/resources.py").write_text("# fixture dispatcher\n")
    (tmp_path / "src/tcsexam/build.py").write_text("# fixture build\n")
    (tmp_path / "generator.py").write_text("# original generator\n")
    (tmp_path / "files.json").write_text('{"files": []}')
    (tmp_path / "recipe.json").write_text(json.dumps({
        "generator_paths": ["generator.py"],
        "build": {"builder_image": "ubuntu:22.04@sha256:" + "1" * 64},
    }))
    record = {"id": "fixture", "type": "data", "recipe": "recipe.json", "files_manifest": "files.json",
              "content_version": "v1", "distribution": "local_prepare", "public_upload_allowed": False,
              "recipe_format": recipe_format, "target_root": "/",
              "manifest_sha256": digest(tmp_path / "files.json")}
    before = build_definition(tmp_path, record)
    (tmp_path / "generator.py").write_text("# corrected generator\n")
    after = build_definition(tmp_path, record)
    assert before["source_digest"] != after["source_digest"]
    assert before["manifest_sha256"] == after["manifest_sha256"]


def test_source_preparation_preserves_distribution_and_version_history():
    original = {row["id"]: row for row in json.loads((ROOT / "assets/images.json").read_text())["images"]
                if row.get("id")}
    records = {row["id"]: row for row in product_patch(ROOT)}
    for name in ["solver-ce-pace2021-development-data", "solver-vc-pace2019-development-data"]:
        assert records[name] == original[name]
    # Both MaxClique splits now have verified official-source reconstruction.
    # This permits local preparation while retaining the publication restrictions.
    for name in ["solver-maxclique-dimacs-development-data", "solver-maxclique-dimacs-judging-data"]:
        assert records[name] == original[name]
        assert records[name]["recipe_format"] == "official_files"
        assert records[name]["distribution"] == "local_prepare"
        assert not records[name].get("public_pull_verified")
        assert not records[name].get("public_upload_allowed")
    name = "solver-radiation-mznchallenge-judging-data"
    assert records[name] == original[name]
    # Fixed official files plus bundled project originals now reconstruct all
    # 47 hidden inputs without changing the separate image-publication decision.
    assert records[name]["recipe_format"] == "official_files"
    assert records[name]["files"] == 47
    assert records[name]["distribution"] == "local_prepare"
    assert not records[name].get("public_pull_verified")
    assert not records[name].get("public_upload_allowed")
    # The official route reconstructs all 211 solver inputs. Canonical98 and
    # the original compressed211 archive retain separate frozen identities.
    name = "solver-maxsat-mse-judging-data"
    recipe = json.loads((ROOT / records[name]['recipe']).read_text())
    assert records[name]["recipe_format"] == recipe['format'] == "official_maxsat_generator"
    assert records[name]["content_version"] == recipe['content_version'] == "original-judging211-xz525-p6-t1-v1"
    assert recipe['plaintext_contract'] == PLAINTEXT_CONTRACT
    assert records[name]['source_inputs'] == recipe['sources']
    assert 'source_input_file' not in records[name]
    assert records[name]["files"] == 211
    assert records[name]["data_history"][0]["files"] == 98
    assert records[name]['data_history'][0]['manifest_sha256'] == '6b05630fc35b918aaf60c2c2c60661b0eb1777aecd81fcac34bf5abaa6ad5f89'
    legacy = recipe['legacy_fixed_archive']
    assert legacy['content_version'] == 'original-judging211-260912-v1'
    assert digest(ROOT / legacy['files_manifest']) == legacy['manifest_sha256'] == 'ac00850349c32f7d853802c0a6e0b331615523b8b458eab9948f7ce419d719e1'
    assert records[name]["distribution"] == "local_prepare"
    assert records[name]["status"] == "local_preparation_required"
    assert not records[name].get("public_pull_verified")
    assert not records[name].get("public_upload_allowed")
