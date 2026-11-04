# Lean task environment

This guide explains how to build and use the shared Lean environment.

The environment targets Linux `amd64`. Install Harbor `0.22.0` for task execution. Lean uses `leanprover/lean4:v4.33.0-rc1`; mathlib is pinned to commit `5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3` and installed at `/opt/lean-lib/mathlib4`. Elan selects the Lean toolchain and Lake manages its dependencies. The fixed transitive dependencies are listed in `mathlib-lake-manifest.json`.

From the repository root, prepare the fixed public source archives and build the selected tasks:

```bash
tcsexam source-inputs
tcsexam build --suite lite --track theorem
tcsexam doctor --suite lite --track theorem
```

`source-inputs` verifies the Graphviz and wrapper archives declared in `graphviz-epl/source-manifest.json` before placing them in the build context. If an upstream download is unavailable, supply an identical local archive through the explicit import documented in the [resource guide](../../../docs/resources.md#prepare-fixed-lean-source-archives). Source preparation does not compile Lean or build Docker images.

Use the complete directory as the base-image build context. The Dockerfile pins its Ubuntu image, Elan archive and mathlib commit. Build-time dependency retrieval requires network access; failed retrieval stops the build. Host networking during the build does not change the selected task's runtime network policy. Local products and historical image records keep separate identities.

Reserve at least 40 GB of disk for image layers, compiled libraries, task builds and logs. Lean tasks use 4 CPU cores and 16 GB of memory; consult the selected `task.toml` for storage and compilation limits. The development budget is twelve hours (43,200 seconds). Environment build, agent installation and final judging have separate budgets. External runtime timeout multipliers remain `1`.

The base image makes compiled mathlib files readable by non-root users. Each development image copies only its task's `environment/app/` and performs the task's declared installation. Complete installation before invoking Lean in a new project, so Lake can resolve the pinned dependency configuration. Runtime connectivity follows each task's configuration.

## Running and judging

Retain Harbor's native task entry points. See the [Harbor task documentation](https://docs.harborframework.com/tasks/overview) and the repository [running guide](../../../docs/running.md). Generate a configuration without invoking a model or compiling Lean:

```bash
tcsexam prepare --suite lite --track theorem \
  --base-url https://YOUR_PROVIDER.example/v1 --output build/theorem.json
python -m tcsexam.harbor_launch run --config build/theorem.json --print-config
```

The independent verifier uses the development image from the same task and the original `tests/` files. The development build context excludes `tests/`, `solution/` and historical complete proofs. Keep these materials outside the model-solving environment.

Retain the task's reference statements, editable ranges, axiom checks and scoring files. Theorem tasks use their declared standard axioms; construction tasks use the computational axioms listed in `judge.json`. Open-conjecture tasks judge their two main statements independently. Compilation and judging limits apply to every submission.

Run `tcsexam validate` for static repository checks. It does not compile Lean. After changing the task inventory, regenerate declarations with `PYTHONPATH=src python -m tcsexam.lean_recipes`, or append `--check` to detect stale fields.

## Source and license materials

The Dockerfile installs `NOTICE.md` at `/usr/share/doc/tcsexam/README.md` and retains the following separate material sets:

- `lean-components/`: fixed Lake component commits and original licenses.
- `graphviz-epl/`: Graphviz EPL-2.0 text, source offer, fixed source archives, wrapper modifications and build rules.
- `browser-components/`: Expat, Emscripten and Penrose notices with their stated dependency scope.
- `proofwidgets-npm/`: fixed npm dependency source records and original or clearly identified supplementary licenses.

Keep the material paths and their checksum checks in rebuilt images. Each dependency retains its own terms; a project license does not replace a third-party license. Dependency inventories may include build-only components and do not imply that every listed component is linked into the browser payload. See the [distribution guide](../../../docs/licenses/distribution.md).

Task provenance is recorded in `assets/sources.json`, shared dependency pins in `pins.json`, and resource preparation requirements in the [resource guide](../../../docs/resources.md). `tcsexam doctor` reports local image availability separately from runtime acceptance.
