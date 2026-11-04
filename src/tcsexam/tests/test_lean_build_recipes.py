import json
from pathlib import Path
import re

import pytest

from tcsexam.build import build_definition
from tcsexam.inventory import docker_inputs, refresh as refresh_inventory
from tcsexam.lean_recipes import (
    BASE_DIGESTS,
    COMMON_BASE,
    DERIVED_BASE,
    PUBLIC_BASE,
    bind_recipe_source,
    main,
    runtime_identity,
    with_build_recipes,
)


ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads((ROOT / "assets/images.json").read_text())
RECORDS = {row["id"]: row for row in DATA["images"] if row.get("id")}
DERIVED_TASKS = {
    "tasks/construction/binary-code-a24-10",
    "tasks/construction/ex-c3c4-maxedges",
    "tasks/construction/kissing-d13",
    "tasks/construction/ramsey-r46",
    "tasks/construction/tsp-gap",
    "tasks/open/evasiveness-graph-properties",
    "tasks/open/frege-not-pbounded",
    "tasks/open/log-rank-conjecture",
    "tasks/open/online-matching-random-order",
    "tasks/open/prg-constant-width-robp",
    "tasks/theorem/corners-quasipoly",
    "tasks/theorem/folded-rs-gsb",
    "tasks/theorem/negations-small-depth",
    "tasks/theorem/quantum-crypto-algorithmica",
}


def lean_runtimes(role=None):
    rows = []
    for row in DATA["images"]:
        if row.get("type") != "runtime":
            continue
        if role and row.get("runtime_role") != role:
            continue
        if any(consumer.startswith(("tasks/theorem/", "tasks/construction/", "tasks/open/"))
               for consumer in row.get("consumers", [])):
            rows.append(row)
    return sorted(rows, key=lambda row: row["id"])


DEVELOPMENT = lean_runtimes("development")
VERIFIER = lean_runtimes("verifier")
RUNTIMES = lean_runtimes()
PIN = re.compile(r"[^\s<>]+@sha256:[0-9a-f]{64}")


def test_all_140_runtime_products_are_present():
    assert len(DEVELOPMENT) == 70
    assert len(VERIFIER) == 70
    assert len(RUNTIMES) == 140
    assert {row["runtime_role"] for row in RUNTIMES} == {"development", "verifier"}


@pytest.mark.parametrize("row", DEVELOPMENT, ids=lambda row: row["id"])
def test_development_uses_public_base_and_retains_historical_assignment(row):
    task = row["consumers"][0]
    historical = DERIVED_BASE if task in DERIVED_TASKS else COMMON_BASE
    config = row["build"]
    definition = build_definition(ROOT, row)
    assert config == {
        "dockerfile": f"{task}/environment/Dockerfile",
        "context": f"{task}/environment",
        "image_args": {"TCSEXAM_LEAN_BASE": PUBLIC_BASE},
        "network": "host",
    }
    assert row["dependencies"] == [PUBLIC_BASE]
    assert row["historical_base"] == historical
    assert definition["dependencies"] == [PUBLIC_BASE]
    assert definition["image_args"] == {"TCSEXAM_LEAN_BASE": PUBLIC_BASE}
    assert definition["pull_args"] == {}
    assert definition["network"] == "host"
    assert RECORDS[historical]["type"] == "toolchain"
    assert RECORDS[historical]["image_digest"] == BASE_DIGESTS[historical]
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", RECORDS[historical]["image_digest"])


def test_public_base_assignment_and_derived_product_history():
    assert {row["build"]["image_args"]["TCSEXAM_LEAN_BASE"] for row in DEVELOPMENT} == {PUBLIC_BASE}
    counts = {COMMON_BASE: 0, DERIVED_BASE: 0}
    for row in DEVELOPMENT:
        counts[row["historical_base"]] += 1
    assert counts == {COMMON_BASE: 56, DERIVED_BASE: 14}
    derived = RECORDS[DERIVED_BASE]
    discrete = RECORDS[runtime_identity("tasks/theorem/discrete-bidding-games", "development")]
    assert derived["image_digest"] == discrete["image_digest"]
    assert derived["image_digest"] != RECORDS[COMMON_BASE]["image_digest"]
    assert discrete["historical_base"] == COMMON_BASE
    public = RECORDS[PUBLIC_BASE]
    assert public["build"] == {
        "dockerfile": "assets/environments/lean-base/Dockerfile",
        "context": "assets/environments/lean-base",
        "network": "host",
    }
    assert public["dependencies"] == []
    assert public["public_image"] is None
    assert public["public_pull_verified"] is False
    assert public["public_upload_allowed"] is False
    assert public["equivalent_to_observed_products"] is False
    assert build_definition(ROOT, public)["kind"] == "docker"


@pytest.mark.parametrize("row", VERIFIER, ids=lambda row: row["id"])
def test_verifier_uses_same_task_development(row):
    task = row["consumers"][0]
    development = runtime_identity(task, "development")
    assert development in RECORDS
    assert row["build"] == {
        "dockerfile": f"{task}/tests/Dockerfile",
        "context": f"{task}/tests",
        "image_args": {"TCSEXAM_DEVELOPMENT_IMAGE": development},
    }
    assert row["dependencies"] == [development]
    definition = build_definition(ROOT, row)
    assert definition["dependencies"] == [development]
    assert definition["image_args"] == {"TCSEXAM_DEVELOPMENT_IMAGE": development}
    assert definition["pull_args"] == {}
    assert "network" not in definition


@pytest.mark.parametrize("row", RUNTIMES, ids=lambda row: row["id"])
def test_build_context_and_every_local_input_exist(row):
    config = row["build"]
    definition = build_definition(ROOT, row)
    assert definition["kind"] == "docker"
    assert (ROOT / definition["dockerfile"]).is_file()
    assert (ROOT / definition["context"]).is_dir()
    for source in config.get("source_paths", [config["context"]]):
        assert (ROOT / source).exists()
    assert definition["source_digest"].startswith("sha256:")


def test_dockerfile_copy_inputs_are_present():
    runtime_dockerfiles = {row["build"]["dockerfile"] for row in RUNTIMES}
    inputs = [row for row in docker_inputs(ROOT) if row["dockerfile"] in runtime_dockerfiles]
    assert {row["dockerfile"] for row in inputs} == runtime_dockerfiles
    for row in inputs:
        if row["operation"] == "FROM":
            assert row["dynamic"] is True
            assert row["expression"] in ("${TCSEXAM_LEAN_BASE}", "${TCSEXAM_DEVELOPMENT_IMAGE}")
            continue
        if row["operation"] not in ("COPY", "ADD") or row.get("stage_input"):
            continue
        for item in row["inputs"]:
            if not item["remote"] and not item["dynamic"]:
                assert item["present_paths"], (row["dockerfile"], item)


def test_dependency_graph_is_acyclic_and_directed_toward_development():
    graph = {row["id"]: row["dependencies"] for row in RUNTIMES}
    graph.update({identity: [] for identity in BASE_DIGESTS})
    graph[PUBLIC_BASE] = []
    visiting, visited = set(), set()

    def visit(identity):
        assert identity not in visiting, f"dependency cycle at {identity}"
        if identity in visited:
            return
        visiting.add(identity)
        for dependency in graph[identity]:
            assert dependency in graph
            visit(dependency)
        visiting.remove(identity)
        visited.add(identity)

    for identity in graph:
        visit(identity)
    for row in VERIFIER:
        assert row["id"] not in RECORDS[row["dependencies"][0]]["dependencies"]


def test_generator_is_idempotent_and_preserves_all_solver_records():
    assert with_build_recipes(ROOT, DATA) == DATA
    assert main(["--root", str(ROOT), "--check"]) == 0


def test_missing_verifiers_start_without_historical_acceptance_claims():
    import copy
    previous = copy.deepcopy(DATA)
    removed = {row['id'] for row in VERIFIER
               if row.get('generated_by') == 'lean-independent-verifier'}
    assert len(removed) == 55
    previous['images'] = [row for row in previous['images'] if row.get('id') not in removed]
    regenerated = with_build_recipes(ROOT, previous)
    added = [row for row in regenerated['images'] if row.get('id') in removed]
    assert len(added) == 55
    for row in added:
        assert row['product_prepared'] is False
        assert row['runtime_verified'] is False
        assert row['image_digest'] is None
        assert row.get('harbor_verified') is not True
        assert row['dependencies'] == [runtime_identity(row['consumers'][0], 'development')]
    assert with_build_recipes(ROOT, regenerated) == regenerated


def test_source_binding_invalidates_changed_recipes_and_preserves_later_acceptance(tmp_path):
    import copy
    tests = tmp_path / 'tests'
    tests.mkdir()
    (tests / 'Dockerfile').write_text('FROM example\n')
    (tmp_path / 'src/tcsexam').mkdir(parents=True)
    (tmp_path / 'src/tcsexam/build.py').write_text('builder input\n')
    row = {'id': 'fixture', 'type': 'runtime', 'image_digest': 'old-image',
           'product_prepared': True, 'harbor_verified': True, 'content_verified': True,
           'build': {'dockerfile': 'tests/Dockerfile', 'context': 'tests'}}
    bind_recipe_source(tmp_path, row)
    first = row['source_recipe_source_digest']
    assert row['product_prepared'] is False
    assert row['harbor_verified'] is False
    assert row['previous_recipe_acceptance']['scope'] == 'legacy'
    assert row['previous_recipe_acceptance']['harbor_verified'] is True
    assert row['previous_recipe_acceptance']['image_digest'] == 'old-image'
    row.update(product_prepared=True, harbor_verified=True, content_verified=True)
    accepted = copy.deepcopy(row)
    bind_recipe_source(tmp_path, row)
    assert row == accepted
    (tests / 'Dockerfile').write_text('FROM changed-example\n')
    bind_recipe_source(tmp_path, row)
    assert row['source_recipe_source_digest'] != first
    assert row['product_prepared'] is False
    assert row['harbor_verified'] is False
    assert row['previous_recipe_acceptance']['source_recipe_source_digest'] == first
    invalidated = copy.deepcopy(row)
    bind_recipe_source(tmp_path, row)
    assert row == invalidated


def test_legacy_base_binding_preserves_recorded_observations(tmp_path):
    (tmp_path / 'Dockerfile').write_text('FROM example\n')
    (tmp_path / 'src/tcsexam').mkdir(parents=True)
    (tmp_path / 'src/tcsexam/build.py').write_text('builder input\n')
    row = {'id': 'base', 'type': 'toolchain', 'product_prepared': True,
           'runtime_verified': True, 'build': {'dockerfile': 'Dockerfile',
                                            'context': '.', 'source_paths': ['Dockerfile']}}
    bind_recipe_source(tmp_path, row, legacy_base=True)
    assert row['product_prepared'] is True
    assert row['runtime_verified'] is True
    assert row['source_recipe_acceptance_scope'] == 'legacy'
    assert row['source_recipe_source_digest'].startswith('sha256:')


def test_inventory_refresh_preserves_existing_build_records(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (tmp_path / "tasks").mkdir()
    (assets / "files.json").write_text('{"files": []}\n')
    (assets / "images.json").write_text(json.dumps(DATA))
    before = {row["id"]: (row.get("dependencies"), row.get("build"))
              for row in DATA["images"] if row.get("id")}
    refresh_inventory(tmp_path)
    after = json.loads((assets / "images.json").read_text())
    assert {row["id"]: (row.get("dependencies"), row.get("build"))
            for row in after["images"] if row.get("id")} == before


def test_public_build_declarations_bind_the_actual_pinned_recipe_and_sources():
    declaration = json.loads((ROOT / "assets/environments/lean-base/rebuild-status.json").read_text())
    assert declaration["public_base_record"] == PUBLIC_BASE
    public = RECORDS[PUBLIC_BASE]
    assert declaration["dockerfile"] == public["build"]["dockerfile"]
    assert declaration["dependency_manifest"] == "assets/environments/lean-base/mathlib-lake-manifest.json"
    manifest = json.loads((ROOT / declaration["dependency_manifest"]).read_text())
    assert manifest["packages"] and all(re.fullmatch(r"[0-9a-f]{40}", p["rev"]) for p in manifest["packages"])
    dockerfile = (ROOT / declaration["dockerfile"]).read_text()
    bases = [line.split()[1] for line in dockerfile.splitlines() if line.startswith("FROM ")]
    assert bases and all(PIN.fullmatch(reference) for reference in bases)
    assert declaration["source_preparation"] == "tcsexam source-inputs"
    assert declaration["local_build"] == "tcsexam build --suite lite --track theorem"
    for directory in declaration["source_materials"]:
        source = ROOT / directory
        assert source.is_dir()
        assert f"COPY {source.name}/ /usr/share/doc/tcsexam/{source.name}/" in dockerfile
        assert f"cd /usr/share/doc/tcsexam/{source.name}" in dockerfile
        assert (source / "SHA256SUMS").is_file()
    assert "sha256sum -c SHA256SUMS" in dockerfile


def test_development_recipes_use_public_base_without_bundled_extra_agent():
    for row in DEVELOPMENT:
        dockerfile = (ROOT / row["build"]["dockerfile"]).read_text()
        assert "@anthropic-ai/claude-code" not in dockerfile
        assert "claude --version" not in dockerfile
    # Environment images must retain the explicit fixed public base dependency.
    for row in DEVELOPMENT:
        assert PUBLIC_BASE in row["dependencies"]


def test_public_lean_materials_do_not_embed_internal_references():
    from tcsexam.checks import internal_reference_categories

    for path in (ROOT / "assets/environments/lean-base").iterdir():
        if path.suffix not in (".json", ".md", "") or not path.is_file():
            continue
        text = path.read_text()
        assert internal_reference_categories(text) == [], path.relative_to(ROOT)
