import json
from pathlib import Path

import pytest

from tcsexam.build import build_definition
from tcsexam.solver_recipes import solver_runtime_manifest


ROOT = Path(__file__).resolve().parents[3]
TASKS = ("ce-pace2021", "dfvs-pace2022")


@pytest.fixture(scope="module")
def records():
    data = solver_runtime_manifest(ROOT, json.loads((ROOT / "assets/images.json").read_text()))
    return {row["id"]: row for row in data["images"] if row.get("id")}


def docker_definition(records, identity):
    row = records[identity]
    config = row["build"]
    definition = build_definition(ROOT, row)
    assert definition["kind"] == "docker"
    assert (ROOT / config["dockerfile"]).is_file()
    assert (ROOT / config["context"]).exists()
    for source in config.get("source_paths", [config["context"]]):
        assert (ROOT / source).exists()
    return definition


@pytest.mark.parametrize("task", TASKS)
def test_development_data_declares_public_data_build_argument(records, task):
    row = records[f"solver-{task}-development-data"]
    definition = build_definition(ROOT, row)
    assert definition["kind"] == "resource"
    assert row["build_argument"] == "TCSEXAM_PUBLIC_DATA_IMAGE"
    assert (ROOT / row["recipe"]).is_file()
    assert (ROOT / row["files_manifest"]).is_file()


@pytest.mark.parametrize("task", TASKS)
def test_official_tools_build_in_pinned_jammy_without_changing_binary_pins(records, task):
    row = records[f"solver-{task}-development-tools"]
    recipe = json.loads((ROOT / row["recipe"]).read_text())
    builder = "ubuntu:22.04@sha256:0a9887931b0e38af2e3487ed39e29436b0535c4f3f52e57745baaf79d1898956"
    definition = build_definition(ROOT, row)
    assert definition["kind"] == "resource"
    assert definition["official_builder"] == builder
    assert definition["pull_args"] == {"TCSEXAM_OFFICIAL_BUILDER": builder}
    assert recipe["build"]["builder_image"] == builder
    assert recipe["build"]["command"] == ["make", "all"]

    entries = json.loads((ROOT / row["files_manifest"]).read_text())["files"]
    binaries = [entry for entry in entries if "source_member" not in entry]
    expected = {
        "ce-pace2021": "2f2863e6f136fa565c8698aedb2c368ca644e3aa6e2f3a8ce8949b0a001f12f6",
        "dfvs-pace2022": "21f73c58783c1d2eb17cf2fdbb437b2d17b2b86e350529ef2465d83ad75a4bf9",
    }[task]
    assert len(binaries) == 2
    assert {entry["sha256"] for entry in binaries} == {expected}
    assert {entry["mode"] for entry in binaries} == {"0755"}
