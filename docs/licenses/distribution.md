# Resource access and distribution conditions

[English](distribution.md) | [简体中文](distribution.zh-CN.md)

This guide lists access routes and sharing conditions for TCSExam resources.
It is for users preparing data locally or distributing source, data or images.

## Apply conditions to the selected material

Use [`tcsexam build`](../resources.md) to acquire fixed official inputs, verify
and transform them, and assemble local images. Resources marked `local_prepare`
can be prepared locally under their source terms. `private_only` excludes a
material from public source export and public image distribution.

Before redistributing a product, follow its resource-specific conditions below
and retain the required source, attribution and notices. Each row applies to the
named material and version; an image combines the conditions of all its inputs
and inherited layers. Locally generated products retain applicable restrictions
on their source materials. Use the linked records for exact product IDs and
file scopes.

## Data and task materials

Read each row by resource. Source links and records identify the covered inputs;
sharing conditions apply to the resulting material as well as its containing images.

| Resource | Access and source | Terms and handling |
|---|---|---|
| Original code, checkers, scripts and build configuration | Repository source | Apache-2.0 where project contributors hold the applicable rights. Retain author notices, `LICENSE` and `NOTICE`, and identify modifications. |
| Original task statements, explanatory documentation and website content | Repository source and website repository | CC BY 4.0 where project contributors hold the applicable rights. Retain attribution and identify modifications. |
| QBF evaluation data: thirteen public instances and 57 hidden transformed instances | [ParaProofa v1 supplement](https://doi.org/10.5281/zenodo.18832723), by Mark Peyrer, Maximilian Heisinger and Martina Seidl; [fixed source record](third-party/qbf-data-distribution-source.json) | CC BY 4.0, with attribution to supplement authors and original instance families. The three BMC instances `ex018`, `ex019` and `ex020` additionally retain University of Toronto 2007 non-commercial teaching and research terms, including no-fee, notice and publicity conditions. The fixed-product scope is listed below. Software in the supplement retains its own licenses. |
| BPPLIB instances, packings and registry-table extraction | Fixed official files from [BPPLIB](https://github.com/mdelorme2/BPPLIB); [preparation record](third-party/bpplib-reconstruction.json) | CC BY-NC-ND 4.0. Preserve attribution, non-commercial and no-derivatives conditions. Generated files and all containing images remain local-only products; keep them out of public registries and downloads. |
| PACE 2019 Vertex Cover public development data | [Source record](third-party/vc-pace2019-source.json) for the public-v2 archive; [Zenodo dataset](https://zenodo.org/records/3368306) | CC BY 4.0 by M. Ayaz Dzulfikar, Johannes K. Fichte and Markus Hecher. Scope: `solver-vc-pace2019-development-data`, containing 100 odd-numbered public instances recompressed with XZ 5.2.5. Retain the CC BY text, `PACE2019-VC-NOTICE.txt`, source and PACE report links, graph-family attribution and recompression notes. |
| PACE 2021 Cluster Editing public development data | [Pinned source and XZ reconstruction](third-party/ce-pace2021-source.json) | CC0-1.0 covers the 100 odd-numbered public instances in `solver-ce-pace2021-development-data`. Include the CC0 text and source record. |
| PACE 2022 Directed Feedback Vertex Set public development data | [Pinned source and reconstruction](third-party/dfvs-pace2022-source.json) | Local preparation only: the official archive has no data license. Retain its notices and keep the official archive, generated instances and containing images out of public distribution. The PACE report has its own CC BY 4.0 license. |
| PACE 2024 OSCM public development data | [Two pinned official archives](third-party/oscm-pace2024-source.json) | The combined 173-file product is local-only. MIT covers the 60 medium and thirteen tiny test-set instances; the 100 Exact Track instances have no data license. Retain the source notice and test-set MIT text. Keep both official archives and the combined generated product and containing images out of public distribution. Upstream `.sol` files are excluded from preparation. |
| AHC058 public development data | [Official AtCoder archive and locked generator](third-party/ahc058-atcoder-source.json) | Local preparation only: no open redistribution license is established for the statement, inputs, generator, scorer or visualizer. Retain the source notice. Keep the official archive, generated instances and containing images out of public distribution. |
| Course-timetabling instances | [cb-ctt](https://github.com/iolab-uniud/cb-ctt) for twenty corresponding instances and transformations; [source comparison](third-party/ctt-source-comparison.json) | CC BY 4.0 from the original authors. Identify format/name changes, including `comp15` corresponding to official `comp03`. `comp11` and OptHub solutions require their own source terms; obtain them from the [official sources](https://www.eeecs.qub.ac.uk/itc2007/). Their redistribution terms are unconfirmed. |
| IWLS 2022 public truth tables | [Pinned source and transformations](third-party/logic-syn-iwls2023-source.json) | Retain IWLS 2022's MIT license for the 100 public truth tables and identify transformations. The ABC archive has separate software terms below. |
| MQLib instances | [Family-specific sources and license record](third-party/mqlib-family-license-review.json) | OR-Library instances `g001642`, `g002564` and `g002776` have a documented MIT basis; retain J. E. Beasley's attribution and full license. Acquire other families from their sources under their individual terms. |
| ROADEF/EURO 2012 instances and reference assignments | [Pinned Google OR-Tools source](https://github.com/google/or-tools/tree/06376d5ff5bbaead64e9b2df61ccbe74e99e5f8c/data/roadef_challenge_2011/solution_checker); [source-chain record](third-party/roadef-hidden-source-chain.json) | Included instances and checker source are Apache-2.0. Retain Google attribution, license and modification notes. Reference assignments are project-generated numerical outputs recorded separately. Obtain the challenge PDF from the [official page](https://www.roadef.org/challenge/2012/en/sujet.php); its redistribution terms are unconfirmed. |
| MaxSAT hidden data | [Pinned official Zenodo archive and reconstruction recipe](../../assets/data/solver/solver-maxsat-mse-judging-data-recipe.json) | The MaxSAT Evaluation 2026 supplement is CC BY 4.0. Retain supplement and instance-family attribution from the [third-party notices](THIRD_PARTY_NOTICES.md#additional-full-materials). Included solver programs retain their own licenses. |
| Reference-answer payloads | [Reference-answer handling](../oracle-answers.md) | Keep concrete acceptance answers outside model-solving environments. They are private by default and unnecessary for ordinary builds and runs. Apply the explicit release interface and resource-specific conditions to an answer product authorized for distribution. |
| Papers, rules PDFs, model outputs and other external materials | Original sources and any material-specific license | Follow the terms for the material being shared. A software or dataset license applies only to its covered content. |

The fixed QBF product scope is `qbf-public`, `qbf-judging`,
`qbf-qbfeval-online-development`, `qbf-qbfeval-offline-development`,
`qbf-qbfeval-online-backend`, `qbf-qbfeval-offline-verifier` and
`backend-public-online-qbf-qbfeval`. The associated fixed transformed data,
standard answers and `ex*` mapping have the data permission recorded in the
[source record](third-party/qbf-data-distribution-source.json). Keep applicable
software, system and per-instance notices with any distributed product, and
follow the answer-handling guide for answer payloads.

## Tools and runtime components

Read each row for the component's license and any source or replacement requirements.

| Resource | Access and source | Terms and handling |
|---|---|---|
| PACE 2021 Cluster Editing and PACE 2022 Directed Feedback Vertex Set verifiers | Pinned official [2021 ZIP](https://pacechallenge.org/2021/verifier.zip) and [2022 tar.gz](https://pacechallenge.org/2022/verifier.tar.gz), compiled by the local recipes | Redistribution terms are unconfirmed. Download and compile locally, retain upstream notices and keep the source snapshots and resulting images private. |
| VC public self-test judge | [Component requirements](third-party/vc-public-judge-image.json) for `backend-public-online-vc-pace2019` | Retain project and data licenses, vc_validate corresponding source and build instructions, and applicable system-package source materials. |
| OSCM NumPy development tool | [Pinned NumPy 2.2.6 wheel](third-party/oscm-pace2024-development-tools-source.json) | Local preparation only. The recipe verifies the wheel and its RECORD entries and retains four upstream notices. Bundled-dependency source obligations remain unconfirmed; keep the wheel, tools image and containing images private. |
| CPSolver, dom4j and log4j | [Source, build and replacement guide](cpsolver-source.md) | Java sources: LGPL-3.0-or-later; original Ant files: LGPL-2.1-or-later; dom4j: five-clause BSD-style terms; log4j: Apache Software License 1.1. Include required corresponding source, build materials and complete notices with distributed binaries. |
| Qute, drat-trim and qrp2rup | Pinned sources in the [third-party notices](THIRD_PARTY_NOTICES.md) | Qute's later MIT notice has unconfirmed applicability to its older snapshot; retain the original revision and version comparison. drat-trim is MIT. qrp2rup is CC BY 4.0 under the author's supplement: attribute it, mark changes and provide its source with binaries. Preserve MiniSat and docopt.cpp MIT/Boost notices separately. |
| MQLib software | [MQLib repository](https://github.com/MQLib/MQLib) | MIT. Retain copyright and license, with notices of modifications. Instance data has the family-specific terms above. |
| ABC source | [Pinned source record](third-party/logic-syn-iwls2023-source.json) | Retain the UC Regents BSD-style notice. |
| Lean, mathlib, elan and system packages | [System sources](third-party/system-license-materials.json), [additional package descriptors](third-party/lean-public-rebuild-system-materials.json) and [mathlib inventory](third-party/lean-public-rebuild-mathlib-materials.json) | Retain each component's notices and provide complete corresponding source where its license requires it. Match source, compiled cache and version. |
| Agent tools | Pinned Harbor runtime installer; [agent-tool record](third-party/claude-code-distribution.json) | Agent packages retain their own licenses. The recorded Claude Code package has an All rights reserved notice and no general redistribution grant; install it at runtime and exclude it from distributed environment images. |
| Graphviz in ProofWidgets and other browser components | [Embedded component record](third-party/proofwidgets-embedded-components.json) and [Graphviz source materials](../../assets/environments/lean-base/graphviz-epl/SOURCE-OFFER.md) | Graphviz is EPL-2.0 and the wrapper is Apache-2.0. Prepare fixed source archives with `tcsexam source-inputs`. Retain EPL text, corresponding Graphviz source, wrapper changes and build rules, and applicable Lake/browser/npm notices installed under `/usr/share/doc/tcsexam/`. |

Use the [third-party notices](THIRD_PARTY_NOTICES.md) for attribution text and
[component records](full-review.md) for pinned file inventories. The
[file manifest](../../assets/files.json) and [image manifest](../../assets/images.json)
record input paths, product identities and available acquisition addresses.
