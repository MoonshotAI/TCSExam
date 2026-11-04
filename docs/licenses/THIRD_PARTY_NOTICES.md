# Third-party notices

[English](THIRD_PARTY_NOTICES.md) | [简体中文](THIRD_PARTY_NOTICES.zh-CN.md)

This page lists component sources, licenses and attribution requirements.
It is for users reusing task materials or preparing a distribution.

Third-party terms apply to the corresponding files in task folders and
containers. Original license texts are under `docs/licenses/third-party/`.
Use [distribution conditions](distribution.md) for resource-specific sharing
scope and [component records](full-review.md) for pinned source and file lists.

## Solver code, data, and reference materials

Read each row for the named component and its required attribution. Paths under
`environment/app/` are relative to the task identified in that row.

| Resource and location | Source, author, and terms | Attribution and distribution conditions |
|---|---|---|
| BPPLIB instances: `tasks/solver/online/bpp-bpplib/environment/app/instances/`, `library/`, and `tests/official-instances/` | M. Delorme, M. Iori, S. Martello, and the authors of each family; [BPPLIB license](https://github.com/mdelorme2/BPPLIB/blob/main/LICENSE), CC BY-NC-ND 4.0 | Retain original attribution and license. The non-commercial and no-derivatives conditions remain in force. |
| BPPLIB packings, registry-table extraction, and transformed data, including hidden judging data | Derived from the BPPLIB data and solution logs under the same CC BY-NC-ND 4.0 terms | Obtain the originals and prepare any required files locally. Keep derived files local under the [distribution conditions](distribution.md). The [source and preparation record](third-party/bpplib-reconstruction.json) and [table-source record](third-party/bpplib-table-source.json) identify the materials. |
| Course-timetabling instances and transformations: `tasks/solver/online/curriculum-itc2007/` | Sara Ceschia, Francesca Da Ros, Luca Di Gaspero, Andrea Schaerf; [cb-ctt license](https://github.com/iolab-uniud/cb-ctt/blob/main/LICENSE.txt), CC BY 4.0 | Attribute the authors and retain conversion notes. `comp15` corresponds to official `comp03`; the license basis does not extend to `comp11`. See the [source comparison](third-party/ctt-source-comparison.json). |
| CPSolver wrapper source: `environment/app/cpsolver-src/` | Tomáš Müller et al.; [original repository](https://github.com/tomas-muller/cpsolver-itc2007); source headers specify LGPL-3.0-or-later | Retain source headers, original notices, and modification notes. Provide the corresponding source and build materials with a distributed binary. |
| CPSolver core JAR: `environment/app/lib/cpsolver-all-1.2.jar` | CPSolver 1.2_bld46; [upstream task-package source](https://github.com/tomas-muller/cpsolver-itc2007/blob/a253a5a45a5b148d5a8981c3fd0af5ecf9ae4b06/lib/cpsolver-all-1.2.jar); LGPL-3.0 text in the JAR | The [source, build, and replacement guide](cpsolver-source.md) identifies the corresponding release source and required package contents. Retain the LGPL and related dependency notices. |
| dom4j 1.6.1: `environment/app/lib/dom4j-1.6.1.jar` | MetaStuff Ltd.; five-clause BSD-style terms in the JAR's `META-INF/LICENSE.txt` | Preserve the full notice, including attribution, no-endorsement, and name restrictions. Keep all five clauses intact. |
| log4j 1.2.8: `environment/app/lib/log4j-1.2.8.jar` | Apache Software Foundation; Apache Software License 1.1 in the [official source archive](https://archive.apache.org/dist/logging/log4j/1.2.8/jakarta-log4j-1.2.8.tar.gz) | Retain the complete license, its required acknowledgment, and its name restrictions. See `third-party/Log4j-1.2.8-Apache-1.1.txt`. |
| Official ITC 2007 `validator.cc` and OptHub best-known solutions | Andrea Schaerf, Luca Di Gaspero, and solution contributors; [ITC 2007](https://www.eeecs.qub.ac.uk/itc2007/) and [OptHub](https://opthub.uniud.it/) | Redistribution terms for these files remain unconfirmed. Obtain them from their original sources and follow their individual terms. |
| MQLib software: `tasks/solver/online/maxcut-mqlib/environment/app/mqlib/` | Iain Dunning, Swati Gupta, and John Silberholz; [MQLib license](https://github.com/MQLib/MQLib/blob/master/LICENSE), MIT | Retain copyright, the MIT license, and notices for modified code. Instance data has the family-specific terms below; consult each source for accompanying papers and supplements. |
| MQLib instances and transformed copies | The [MQLib download script](https://github.com/MQLib/MQLib/blob/master/scripts/downloadAllGraphs.py) points to sources hosted separately | Instance terms vary by family. Obtain each item from its source and follow the conditions for that family. |
| OR-Library instances `g001642`, `g002564`, and `g002776`, used by MQLib | J. E. Beasley; [OR-Library legal page](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/legal.html), MIT | Retain Beasley's copyright, the full MIT text, and attribution for the MQLib transformation. This basis covers only these three instances. See the [MQLib family record](third-party/mqlib-family-license-review.json). |
| ROADEF/EURO 2012 instances, rearranged copies, and Google checker | Pinned [Google OR-Tools source](https://github.com/google/or-tools/tree/06376d5ff5bbaead64e9b2df61ccbe74e99e5f8c/data/roadef_challenge_2011/solution_checker), Apache-2.0 | Retain Google attribution, the license, and notes on changes to the source files and data. The [source-chain record](third-party/roadef-hidden-source-chain.json) identifies the corresponding materials. |
| ROADEF challenge PDF and project-generated reference assignments | [Official challenge page](https://www.roadef.org/challenge/2012/en/sujet.php); the reference assignments were generated by this project | Redistribution terms for the PDF are not established; obtain it from the official source. The reference assignments are project-generated numerical outputs, documented in the [source record](third-party/roadef-hidden-source-chain.json). The source record identifies them separately from the PDF and checker code. |
| ROADEF checker source: `environment/app/checker-src/` | Copyright 2011 Google Inc. All Rights Reserved.; pinned official source above, Apache-2.0 | Retain Google's copyright and license, and identify the blank-line changes. See the [source comparison](third-party/roadef-checker-source.json). |
| Qute source: `tasks/solver/online/qbf-qbfeval/environment/app/qute/` | Friedrich Slivovsky and Tomáš Peitl; [pinned source](https://github.com/fslivovsky/qute/tree/67c5e54e96eb2ba7aedc18186d5ae62230c4caf8); MIT terms in the [authors' software supplement](https://doi.org/10.5281/zenodo.14536421) | Retain the source revision, copyright, full license, and the fact that the license was added after the older source snapshot. Applicability of the later MIT notice to the older snapshot remains unconfirmed. See the [version comparison](third-party/qute-version-comparison.json). |
| MiniSat and docopt.cpp bundled with Qute | Original component authors; bundled MiniSat, `LICENSE-MIT`, and `LICENSE-Boost-1.0` files | Retain each component's original notice separately, including both docopt.cpp license texts. |
| qrp2rup | Tomáš Peitl; 2026 [CC BY 4.0 software supplement](https://doi.org/10.5281/zenodo.20203771), attributed to Tomáš Peitl and Leroy Chew | Attribute the source, mark modifications, and provide the corresponding source and notices with binaries. See the [source record](third-party/qrp2rup-current-license-source.json) and [materials list](third-party/qrp2rup-distribution-files.json). |
| drat-trim | Marijn Heule and Nathan Wetzler; [pinned source header](https://github.com/marijnheule/drat-trim/blob/2e3b2dc0ecf938addbd779d42877b6ed69d9a985/drat-trim.c), MIT | Retain the copyright, license, and disclaimer from the source header when distributing the binary. |
| QBFEVAL data, public and hidden instances, and transformed copies | [Official QBFEVAL 2020 rules](https://www.qbflib.org/qbfeval20.php); [ParaProofa v1 supplement](https://doi.org/10.5281/zenodo.18832723), CC BY 4.0 | Attribute Mark Peyrer, Maximilian Heisinger, Martina Seidl, and the original instance families. The three BMC instances retain University of Toronto 2007 non-commercial teaching and research terms. See the [per-instance source record](third-party/qbf-data-distribution-source.json) and [included-material list](third-party/qbf-data-distribution-files.json). |

The exact acknowledgment required by the log4j 1.2.8 terms is: “This product includes software developed by the Apache Software Foundation (http://www.apache.org/).” The complete original terms are in `third-party/Log4j-1.2.8-Apache-1.1.txt`.

## Lean, construction, and system components

Read each row for the pinned component or mathematical-data source.

| Resource | Source and terms | Attribution and distribution conditions |
|---|---|---|
| Lean 4.33.0-rc1 and elan 4.2.3 | [Lean license](https://github.com/leanprover/lean4/blob/v4.33.0-rc1/LICENSE) and [elan license](https://github.com/leanprover/elan/blob/master/LICENSE), Apache-2.0 | Retain both notices and applicable notices for components included in the image. |
| mathlib commit `5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3` | [Pinned mathlib license](https://github.com/leanprover-community/mathlib4/blob/5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3/LICENSE), Apache-2.0 | Retain file-level copyright headers. Use matching source, compiled cache, version, and notices. |
| Batteries, Aesop, Qq, ProofWidgets, ImportGraph, LeanSearchClient, and Plausible | Licenses at their pinned commits; Apache-2.0 notices are in `third-party/` | Retain component notices. ProofWidgets' generated browser code has dependencies with their own licenses; see the [frontend license record](third-party/proofwidgets-npm-license-materials.json). |
| Lean4 CLI commit `da07ca808b6718cb2aed14dba154e5a08b8f8ecf` | mhuisi; [pinned license](https://github.com/leanprover/lean4-cli/blob/da07ca808b6718cb2aed14dba154e5a08b8f8ecf/LICENSE), MIT | Retain its MIT notice; it is separate from Lean's Apache-2.0 license. |
| Frege definition layer based on FormalizedFormalLogic/Foundation | [Upstream license](https://github.com/FormalizedFormalLogic/Foundation/blob/master/LICENSE), Apache-2.0 | Attribute FormalizedFormalLogic/Foundation contributors and retain the license and adaptation notes in the [source record](third-party/frege-reference-source.json). |
| Binary-code reference with 136 codewords: `tasks/construction/binary-code-a24-10/solution/` | Laaksonen and Östergård; derived from parameters and orbit representatives in [their paper](https://arxiv.org/abs/1604.06022) | Attribute the authors and identify the source. The task payload consists of the converted codewords. See the [reference record](third-party/a24-reference-source.json). |
| Extremal-graph reference: 124 vertices, 629 edges, and Lean encoding | Jan Goedgebeur, Jorik Jooken, Gwenaël Joret, and Tibo Van den Eede; [fixed upstream source](https://github.com/AGT-Kulak/searchMaxSizeMinGirth/tree/f6c80b4aa75236b0d4e6ff4f11f197621080f180), GPL-3.0 | GPL-3.0 applies to the upstream code and graph data. Retain the original graph, Lean source, attribution, GPL text, and conversion notes. A combined work containing GPL material must meet GPL terms. See the [source record](third-party/extremal-graph-source.json) and [component file list](third-party/extremal-graph-distribution-files.json). |
| Locally generated examples, including the Petersen graph, cross polytopes, and root systems | Task-specific generation code and descriptions | Keep mathematical-object data distinct from copied code and third-party programs; apply each source's terms to the actual material. |

Container images include Debian, Ubuntu, GNU tools, Java, Python, and other system components. Each component retains its own license. Retain the component notices and provide corresponding source when required. Exact versions and source locations are in the [system license materials](third-party/system-license-materials.json).

Graphviz 15.0.0 embedded in ProofWidgets is EPL-2.0; the outer `@hpcc-js/wasm` package is Apache-2.0. Distribution must include the EPL text and a usable way to obtain Graphviz source and the modifications. Expat 2.8.1, Emscripten 6.0.0, and Penrose Rust components keep their original licenses; see the [embedded component record](third-party/proofwidgets-embedded-components.json).

## Additional Full materials

These notices also apply to Full and same-source offline packages:

- **JSPLIB data:** ScheduleOpt/benchmarks and applicable adaptations are CC BY-SA 4.0. Attribute the original instance authors and ScheduleOpt contributors; see the [source record](third-party/full-review.json).
- **MCQD maximum-clique code:** `mcqd_anytime.h` carries Janez Konc's GPL-3.0-or-later notice. Preserve its header and identify the node-limit, time-limit, output-removal, and optimality-query modifications.
- **Circuit definitions:** Copyright 2026 Samuel Schlesinger, Apache-2.0; used in `np-vs-acc` and `nexp-vs-tc0`, with changes described in the source header.
- **Tensor-rank definition:** Copyright 2026 Jeroen Zuiddam, Apache-2.0; the formalization source credits Christandl, Hoeberechts, Nieuwboer, Vrana, and Zuiddam. See the per-task source record.
- **Sorting-network comparators:** Green 1969; identical comparator data from fixed SorterHunter files, Copyright 2017 Bert Dobbelaere, MIT. Retain attribution and the license when distributing the converted Lean tuples.
- **PACE 2019 instances:** M. Ayaz Dzulfikar, Johannes K. Fichte, and Markus Hecher; official [Zenodo record 3368306](https://zenodo.org/records/3368306), CC BY 4.0. Retain other original sources and conversion notes.
- **MaxSAT Evaluation 2026 supplement:** Dieter Vandesande, Christoph Jabs, Jeremias Berg, Johannes Fichte, George Katsirelos, Ruben Martins, André Schidler, and Dominik Schreiber; [Zenodo record 21358014](https://zenodo.org/records/21358014), CC BY 4.0. Retain instance-family attribution; included solver software keeps its own license.
- **PACE 2024 checker:** Copyright 2023 Philipp Kindermann, Fabian Klute, and Soeren Nickel, MIT. Retain the notice from the included wheel.

The [per-task license record](third-party/full-review.json) identifies additional MIT, BSD-style, CC0, Apache and GPL components. Follow the [distribution conditions](distribution.md) for materials with unconfirmed terms.
