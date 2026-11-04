This reference describes the TCSExam source package and its build entry points.
It is for users preparing environments from source or creating a source distribution.

# Source packages

[English](source-delivery.md) | [简体中文](source-delivery.zh-CN.md)

The repository contains 100 tasks in 130 task folders: 70 shared Lean
folders and 30 Solver tasks with separate Online and Offline folders. Lite
selects 20 tasks from across Full's task categories, using these same folders.

Read the table by directory. Runtime outputs are kept separately from source.

| Path | Contents |
|---|---|
| `tasks/` | Instructions, task configuration, environment recipes and verifiers |
| `suites/` | Full/Lite selections and task/protocol paths |
| `src/tcsexam/` | CLI, score calculation, judging backend and fixed scoring references |
| `assets/` | Resource inventories, pinned input recipes, environment builds and notices |
| `docs/` | Usage, technical references, sources and licenses |

Each task uses Harbor's folder format with `instruction.md`, `task.toml`,
`environment/` and `tests/`. Runtime images, bulk prepared datasets, model
outputs and reference-answer archives are separate products.

## Build from source

Follow [getting started](getting-started.md) to install the CLI and check the
host. The build entry points are:

```bash
tcsexam source-inputs
tcsexam build --suite lite
```

`source-inputs` prepares fixed public Lean source archives. `build` prepares the
selected dependencies and images on the Docker host. Use
[resource preparation](resources.md) for fixed inputs, acquisition failures,
image manifests and selecting a smaller build. Ordinary evaluation uses the
task inputs and verifiers; reference-answer archives are optional inputs for
the [reference-answer tooling](oracle-answers.md).

To prepare all task variants, build Full once with Online Solver and then the
Offline Solver track:

```bash
tcsexam build --suite full --solver-protocol online
tcsexam build --suite full --track solver --solver-protocol offline
```

Configure the model and check the chosen runtime selection through
[running evaluations](running.md). Online Solver additionally needs its
[backend service](backend/docker.md).

## Export and redistribution

[CONTRIBUTING.md](../.github/CONTRIBUTING.md) contains source-export commands and development
checks. Export keeps source
separate from caches, credentials and evaluation outputs. Keep runtime images
and job directories separately when preserving an experiment.

Preserve the applicable [licenses and notices](licenses/README.md).
[Distribution conditions](licenses/distribution.md) describe which third-party
materials and images can be shared.
