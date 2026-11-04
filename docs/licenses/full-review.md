# Component source and license records

[English](full-review.md) | [简体中文](full-review.zh-CN.md)

This page locates pinned source, file and license records for TCSExam components.
It is for users checking attribution or preparing a distribution.

Start with [Licensing](README.md) for project licenses and
[distribution conditions](distribution.md) for resource-specific requirements.
The [third-party notices](THIRD_PARTY_NOTICES.md) identify component authors and
terms; original license texts are preserved in [third-party/](third-party/).

## Find a component record

Read each row for the record covering that material. Records identify pinned
versions and paths; use the entry matching the resource you are distributing.

| Material | Records |
|---|---|
| Task code, data and reference materials | [Per-task source and license inventory](third-party/full-review.json) and [resource distribution records](third-party/distribution-decisions.json) |
| Runtime images | [Image component inventory](third-party/image-license-inventory.json), [system package materials](third-party/system-license-materials.json) and the [image manifest](../../assets/images.json) |
| Lean packages and caches | [Mathlib materials](third-party/lean-public-rebuild-mathlib-materials.json) and [additional system materials](third-party/lean-public-rebuild-system-materials.json) |
| ProofWidgets browser code | [Frontend dependency materials](third-party/proofwidgets-npm-license-materials.json), [embedded components](third-party/proofwidgets-embedded-components.json) and [Graphviz source materials](../../assets/environments/lean-base/graphviz-epl/SOURCE-OFFER.md) |
| CPSolver and its dependencies | [Source, build and replacement guide](cpsolver-source.md) |
| Resource acquisition and local preparation | [Resource guide](../resources.md), [file manifest](../../assets/files.json) and [data recipes](../../assets/data/) |

The per-task inventory records material at its pinned source revision.
Same-source task variants retain those material-specific terms. For image
sharing, collect the applicable notices and corresponding source for all
included components, using their exact pinned versions.
