# Resource inventories

[English](README.md) | [简体中文](README.zh-CN.md)

These manifests describe task environments, data preparation and source provenance.
They are for contributors maintaining the build recipes; paths are repository-relative.

| File or directory | Contents |
|---|---|
| `images.json` | Runtime, tool and data products, image identities, dependencies and acquisition recipes |
| `files.json` | Omitted source inputs, paths, sizes, hashes, modes and distribution conditions |
| `sources.json` | Source commits, original hashes and current packaging hashes |
| `data/` | Data preparation recipes, per-file manifests and the common data-image Dockerfile |
| `build-inputs.json` | Dockerfile FROM/COPY/ADD dependencies and omitted inputs |
| `resource-groups.json` | Omitted files grouped by purpose and distribution conditions |
| `environments/lean-base/` | Shared Lean build materials and dependency pins |
| `environments/cpsolver/` | CPSolver source and build materials; see [instructions](../docs/licenses/cpsolver-source.md) |

Use `tcsexam build` to prepare a selection from these recipes. It downloads fixed
inputs, builds dependencies and assembles the complete images used by Harbor.
Data images supply files at build time. The resulting image identities are stored
in the local cache for `doctor` and `run`. An external `artifacts.json` provides
optional immutable image assignments. See [resource preparation](../docs/resources.md)
for the commands and input requirements.

Keep public practice data, hidden judging data and reference answers in their
respective products. Development and public self-test images must exclude hidden
inputs from every layer. A complete image inherits its inputs'
[distribution conditions](../docs/licenses/distribution.md).

Store generated images, datasets, jobs and private configuration outside the
source package. [Contributing](../.github/CONTRIBUTING.md) describes source checks and export.
