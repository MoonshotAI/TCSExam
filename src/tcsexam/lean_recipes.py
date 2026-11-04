"""Generate local build recipes for the three Lean task tracks."""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import tempfile

from .layout import load, repository


TRACKS = ("theorem", "construction", "open")
COMMON_BASE = "lean-base-1401a103"
DERIVED_BASE = "lean-base-3b26a8d0"
PUBLIC_BASE = "lean-base-public-5b3f719"
BASE_DIGESTS = {
    COMMON_BASE: "sha256:1401a1032f6aa67aea121b342af959450f53a94735ebc854c523438ac9796279",
    DERIVED_BASE: "sha256:3b26a8d02194e29f983f7735eb17932fc883d89a1b7f53a0fffe6623080d7975",
}


def public_base_record():
    return {
        "id": PUBLIC_BASE,
        "generated_by": "lean-public-upstream-rebuild",
        "type": "toolchain",
        "product_prepared": False,
        "image_digest": None,
        "public_image": None,
        "public_pull_verified": False,
        "public_upload_allowed": False,
        "platform": "linux/amd64",
        "product_record_id": PUBLIC_BASE,
        "status": "local_recipe_available",
        "content_description": "Content-different public-upstream Lean/mathlib base; functional acceptance does not establish equivalence to observed historical products.",
        "distribution": "unresolved",
        "distribution_evidence": "assets/environments/lean-base/rebuild-status.json",
        "equivalent_to_observed_products": False,
        "historical_observed_products": [COMMON_BASE, DERIVED_BASE],
        "runtime_verified": False,
        "dependencies": [],
        "build": {
            "dockerfile": "assets/environments/lean-base/Dockerfile",
            "context": "assets/environments/lean-base",
            "network": "host",
        },
    }


def runtime_identity(task, role):
    return f"runtime-{task.replace('/', '-')}-{role}"


def bind_recipe_source(root, row, *, legacy_base=False):
    """Keep acceptance attached to the source recipe that produced it.

    Imported image observations predate this binding. Preserve their scope as
    historical evidence rather than copying them onto a changed local recipe.
    Re-running the generator on an unchanged recipe preserves later acceptance.
    """
    from .build import build_definition

    digest = build_definition(root, row)["source_digest"]
    previous = row.get("source_recipe_source_digest")
    if previous == digest:
        return
    acceptance = {key: value for key, value in row.items()
                  if key == "product_prepared" or (key.endswith("_verified") and isinstance(value, bool))}
    if legacy_base and previous is None:
        row["source_recipe_acceptance_scope"] = "legacy"
        row["source_recipe_acceptance_note"] = (
            "Recorded base validation predates source-digest binding. Binding the current recipe "
            "preserves that historical evidence and does not establish a new acceptance run."
        )
    else:
        if any(acceptance.values()):
            row["previous_recipe_acceptance"] = {
                "source_recipe_source_digest": previous,
                "scope": "legacy" if previous is None else "previous_recipe",
                "image_digest": row.get("image_digest"),
                "status": row.get("status"),
                **acceptance,
            }
        for key in acceptance:
            row[key] = False
        for key in ("product_prepared", "runtime_verified", "harbor_verified", "content_verified", "startup_verified"):
            row[key] = False
        row["status"] = "local_recipe_available"
    row["source_recipe_source_digest"] = digest


def base_assignments(images):
    assignments = {}
    for row in images:
        if row.get("type") != "historical_reference":
            continue
        source = row.get("source_image", "")
        if source.endswith("@" + BASE_DIGESTS[DERIVED_BASE]):
            base = DERIVED_BASE
        elif (source.endswith("@" + BASE_DIGESTS[COMMON_BASE])
              or source == "<PUBLIC_REGISTRY>/lean-runtime:historical"):
            base = COMMON_BASE
        else:
            base = None
        for location in row.get("locations", []):
            suffix = "/environment/Dockerfile"
            if not location.endswith(suffix):
                continue
            task = location[:-len(suffix)]
            if task.split("/")[1] not in TRACKS:
                continue
            if base is None:
                raise ValueError(f"Unrecognized Lean base history for {task}: {source}")
            previous = assignments.setdefault(task, base)
            if previous != base:
                raise ValueError(f"Conflicting Lean base history for {task}")
    return assignments


def with_build_recipes(root, data):
    root = Path(root).resolve()
    result = copy.deepcopy(data)
    images = result["images"]
    by_id = {row.get("id"): row for row in images if row.get("id")}
    for identity, digest in BASE_DIGESTS.items():
        row = by_id.get(identity)
        if row is None or row.get("type") != "toolchain" or row.get("image_digest") != digest:
            raise ValueError(f"Lean base record is missing or has the wrong digest: {identity}")

    public = by_id.get(PUBLIC_BASE)
    if public is None:
        public = public_base_record()
        images.append(public)
        by_id[PUBLIC_BASE] = public
    expected_public = public_base_record()
    for key, value in expected_public.items():
        if key in {"product_prepared", "image_digest", "status", "runtime_verified", "dependencies", "build"}:
            continue
        if public.get(key) != value:
            raise ValueError(f"Public Lean base record differs for {key}: {PUBLIC_BASE}")
    public["dependencies"] = expected_public["dependencies"]
    public["build"] = expected_public["build"]
    bind_recipe_source(root, public, legacy_base=True)

    assignments = base_assignments(images)
    runtimes = {}
    for row in images:
        consumers = row.get("consumers", [])
        if row.get("type") != "runtime" or len(consumers) != 1:
            continue
        task = consumers[0]
        parts = task.split("/")
        if len(parts) != 3 or parts[0] != "tasks" or parts[1] not in TRACKS:
            continue
        role = row.get("runtime_role")
        if role not in ("development", "verifier"):
            continue
        expected = runtime_identity(task, role)
        if row.get("id") != expected:
            raise ValueError(f"Unexpected Lean runtime identity: {row.get('id')} != {expected}")
        if (task, role) in runtimes:
            raise ValueError(f"Duplicate Lean runtime product: {task}/{role}")
        runtimes[(task, role)] = row

    development_tasks = {task for task, role in runtimes if role == "development"}
    if development_tasks != set(assignments):
        missing = sorted(development_tasks - set(assignments))
        stale = sorted(set(assignments) - development_tasks)
        raise ValueError(f"Lean base assignments do not match development products; missing={missing}, stale={stale}")

    # Every Lean task owns a clean verifier product, including Full-only tasks.
    # Preserve historical records and their evidence; new layers start unverified.
    for task in sorted(development_tasks):
        if (task, "verifier") in runtimes:
            continue
        identity = runtime_identity(task, "verifier")
        row = {
            "id": identity,
            "generated_by": "lean-independent-verifier",
            "type": "runtime",
            "consumers": [task],
            "runtime_role": "verifier",
            "product_prepared": False,
            "image_digest": None,
            "public_image": None,
            "public_pull_verified": False,
            "platform": "linux/amd64",
            "product_record_id": identity,
            "status": "local_recipe_available",
            "content_description": "Independent Lean verifier with fixed scoring, project configuration and dependency inputs; accepts declared final source files only.",
            "distribution": "unresolved",
            "public_upload_allowed": False,
            "runtime_verified": False,
            "distribution_evidence": "docs/licenses/distribution.md",
        }
        images.append(row)
        runtimes[(task, "verifier")] = row

    for (task, role), row in sorted(runtimes.items()):
        if role == "development":
            dependency = PUBLIC_BASE
            argument = "TCSEXAM_LEAN_BASE"
            directory = "environment"
            row["historical_base"] = assignments[task]
        else:
            dependency = runtime_identity(task, "development")
            argument = "TCSEXAM_DEVELOPMENT_IMAGE"
            directory = "tests"
            if (task, "development") not in runtimes:
                raise ValueError(f"Lean verifier has no development product: {task}")
        dockerfile = f"{task}/{directory}/Dockerfile"
        if not (root / dockerfile).is_file():
            raise ValueError(f"Lean runtime Dockerfile is missing: {dockerfile}")
        row["dependencies"] = [dependency]
        row["build"] = {
            "dockerfile": dockerfile,
            "context": f"{task}/{directory}",
            "image_args": {argument: dependency},
        }
        if role == "development":
            row["build"]["network"] = "host"
        bind_recipe_source(root, row)
    return result


def refresh(root, check=False):
    root = Path(root).resolve()
    certificate_root = root / "assets/environments/lean-verifier/certificates/ramsey-r55"
    for source_name, target_name in (("legacy-generator.txt", "r55-legacy-generator.txt"),
                                     ("TCSExamR55Certificate.lean", "TCSExamR55Certificate.lean")):
        source = (certificate_root / source_name).read_bytes()
        target = root / "tasks/construction/ramsey-r55/tests" / target_name
        if not target.exists() or target.read_bytes() != source:
            if check:
                raise ValueError("Lean certificate support is stale; run python -m tcsexam.lean_recipes")
            target.write_bytes(source)
    for filename in ("lean_security.py", "TCSExamVerifierAudit.lean"):
        security = (root / "assets/environments/lean-verifier" / filename).read_bytes()
        for track in TRACKS:
            for scorer in sorted((root / "tasks" / track).glob("*/tests/score.py")):
                target = scorer.with_name(filename)
                if not target.exists() or target.read_bytes() != security:
                    if check:
                        raise ValueError("Lean verifier checks are stale; run python -m tcsexam.lean_recipes")
                    target.write_bytes(security)
    path = root / "assets/images.json"
    before = load(path)
    after = with_build_recipes(root, before)
    changed = before != after
    if check and changed:
        raise ValueError("Lean image build recipes are stale; run python -m tcsexam.lean_recipes")
    if changed and not check:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                             prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(after, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    runtimes = [row for row in after["images"]
                if row.get("type") == "runtime" and row.get("runtime_role") in ("development", "verifier")
                and any(consumer.split("/")[1:2] and consumer.split("/")[1] in TRACKS
                        for consumer in row.get("consumers", []))]
    return {
        "changed": changed,
        "check": check,
        "development": sum(row["runtime_role"] == "development" for row in runtimes),
        "verifier": sum(row["runtime_role"] == "verifier" for row in runtimes),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = refresh(repository(args.root), check=args.check)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
