<a id="third-party-notices"></a>

# 第三方声明

[English](THIRD_PARTY_NOTICES.md) | [简体中文](THIRD_PARTY_NOTICES.zh-CN.md)

中文译文供参考，许可条款以原文为准。

本页列出组件来源、许可和署名要求。
供复用任务材料或准备分发的用户阅读。

第三方条款适用于任务文件夹和容器中的对应文件。原始许可文本位于 `docs/licenses/third-party/`。各资源可共享的范围见[分发条件](distribution.zh-CN.md)，固定来源和文件列表见[组件记录](full-review.zh-CN.md)。

<a id="solver-code-data-and-reference-materials"></a>

## Solver 代码、数据与参考材料

读法说明：每行列出指定组件及其署名要求。`environment/app/` 下的路径均相对于该行所指任务。

| 资源与位置 | 来源、作者与条款 | 署名与分发条件 |
|---|---|---|
| BPPLIB 实例：`tasks/solver/online/bpp-bpplib/environment/app/instances/`、`library/` 和 `tests/official-instances/` | M. Delorme、M. Iori、S. Martello 及各实例族作者；[BPPLIB 许可](https://github.com/mdelorme2/BPPLIB/blob/main/LICENSE)，CC BY-NC-ND 4.0 | 保留原始署名和许可。非商业及禁止演绎条件继续有效。 |
| BPPLIB 装箱方案、注册表提取数据及变换数据，包括隐藏判分数据 | 基于 BPPLIB 数据和求解日志，适用相同的 CC BY-NC-ND 4.0 条款 | 获取原件，并在本地准备所需文件。按[分发条件](distribution.zh-CN.md)将生成文件保留在本地。[来源与准备记录](third-party/bpplib-reconstruction.json)及[表格来源记录](third-party/bpplib-table-source.json)标明对应材料。 |
| 课程排课实例及变换：`tasks/solver/online/curriculum-itc2007/` | Sara Ceschia、Francesca Da Ros、Luca Di Gaspero、Andrea Schaerf；[cb-ctt 许可](https://github.com/iolab-uniud/cb-ctt/blob/main/LICENSE.txt)，CC BY 4.0 | 署名作者并保留转换说明。`comp15` 对应官方 `comp03`；许可依据不延伸至 `comp11`。参见[来源比较](third-party/ctt-source-comparison.json)。 |
| CPSolver 封装层源码：`environment/app/cpsolver-src/` | Tomáš Müller 等；[原始仓库](https://github.com/tomas-muller/cpsolver-itc2007)；源码头注明 LGPL-3.0-or-later | 保留源码头、原始声明和修改说明。分发二进制文件时一并提供对应源码及构建材料。 |
| CPSolver 核心 JAR：`environment/app/lib/cpsolver-all-1.2.jar` | CPSolver 1.2_bld46；[上游任务包来源](https://github.com/tomas-muller/cpsolver-itc2007/blob/a253a5a45a5b148d5a8981c3fd0af5ecf9ae4b06/lib/cpsolver-all-1.2.jar)；JAR 内含 LGPL-3.0 文本 | [源码、构建与替换指南](cpsolver-source.zh-CN.md)标明对应发布源码及包内所需内容。保留 LGPL 和相关依赖声明。 |
| dom4j 1.6.1：`environment/app/lib/dom4j-1.6.1.jar` | MetaStuff Ltd.；JAR 的 `META-INF/LICENSE.txt` 内含五条款 BSD 风格条款 | 保留完整声明，包括署名、禁止背书和名称限制。五个条款均须完整保留。 |
| log4j 1.2.8：`environment/app/lib/log4j-1.2.8.jar` | Apache Software Foundation；[官方源码归档](https://archive.apache.org/dist/logging/log4j/1.2.8/jakarta-log4j-1.2.8.tar.gz)中的 Apache Software License 1.1 | 保留完整许可、其要求的致谢和名称限制。参见 `third-party/Log4j-1.2.8-Apache-1.1.txt`。 |
| 官方 ITC 2007 `validator.cc` 和 OptHub 已知最好解 | Andrea Schaerf、Luca Di Gaspero 及解的贡献者；[ITC 2007](https://www.eeecs.qub.ac.uk/itc2007/) 和 [OptHub](https://opthub.uniud.it/) | 这些文件的再分发条款尚未确认。从原始来源获取，并遵循各自条款。 |
| MQLib 软件：`tasks/solver/online/maxcut-mqlib/environment/app/mqlib/` | Iain Dunning、Swati Gupta 和 John Silberholz；[MQLib 许可](https://github.com/MQLib/MQLib/blob/master/LICENSE)，MIT | 保留版权、MIT 许可和修改代码的声明。实例数据采用下列各实例族条款；随附论文和补充材料请查阅各自来源。 |
| MQLib 实例及变换副本 | [MQLib 下载脚本](https://github.com/MQLib/MQLib/blob/master/scripts/downloadAllGraphs.py)指向单独托管的来源 | 实例条款因实例族而异。逐项从其来源获取，并遵循该实例族条件。 |
| MQLib 使用的 OR-Library 实例 `g001642`、`g002564` 和 `g002776` | J. E. Beasley；[OR-Library 法律页面](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/legal.html)，MIT | 保留 Beasley 版权、完整 MIT 文本和 MQLib 变换署名。该依据仅覆盖这三个实例。参见 [MQLib 实例族记录](third-party/mqlib-family-license-review.json)。 |
| ROADEF/EURO 2012 实例、重排副本和 Google 判分器 | 固定 [Google OR-Tools 源码](https://github.com/google/or-tools/tree/06376d5ff5bbaead64e9b2df61ccbe74e99e5f8c/data/roadef_challenge_2011/solution_checker)，Apache-2.0 | 保留 Google 署名、许可，以及源码文件和数据的修改说明。[来源链记录](third-party/roadef-hidden-source-chain.json)标明对应材料。 |
| ROADEF 竞赛 PDF 和项目生成的参考分配方案 | [官方竞赛页面](https://www.roadef.org/challenge/2012/en/sujet.php)；参考分配方案由本项目生成 | PDF 的再分发条款尚未确定，请从官方来源获取。参考分配方案为项目生成的数值输出，记录在[来源记录](third-party/roadef-hidden-source-chain.json)中。来源记录将其与 PDF 和判分器代码分别标明。 |
| ROADEF 判分器源码：`environment/app/checker-src/` | Copyright 2011 Google Inc. All Rights Reserved.；上述固定官方源码，Apache-2.0 | 保留 Google 版权和许可，并标明空行修改。参见[来源比较](third-party/roadef-checker-source.json)。 |
| Qute 源码：`tasks/solver/online/qbf-qbfeval/environment/app/qute/` | Friedrich Slivovsky 和 Tomáš Peitl；[固定源码](https://github.com/fslivovsky/qute/tree/67c5e54e96eb2ba7aedc18186d5ae62230c4caf8)；[作者软件补充材料](https://doi.org/10.5281/zenodo.14536421)中的 MIT 条款 | 保留源码版本、版权、完整许可，以及许可添加于较旧源码快照之后这一说明。后来的 MIT 声明是否适用于较旧快照尚未确认。参见[版本比较](third-party/qute-version-comparison.json)。 |
| Qute 随附的 MiniSat 和 docopt.cpp | 原组件作者；随附 MiniSat、`LICENSE-MIT` 和 `LICENSE-Boost-1.0` 文件 | 分别保留各组件原始声明，包括 docopt.cpp 的两份许可文本。 |
| qrp2rup | Tomáš Peitl；2026 年 [CC BY 4.0 软件补充材料](https://doi.org/10.5281/zenodo.20203771)，署名 Tomáš Peitl 和 Leroy Chew | 署名来源、标明修改，并随二进制文件提供对应源码和声明。参见[来源记录](third-party/qrp2rup-current-license-source.json)和[材料列表](third-party/qrp2rup-distribution-files.json)。 |
| drat-trim | Marijn Heule 和 Nathan Wetzler；[固定源码头](https://github.com/marijnheule/drat-trim/blob/2e3b2dc0ecf938addbd779d42877b6ed69d9a985/drat-trim.c)，MIT | 分发二进制文件时，保留源码头中的版权、许可和免责声明。 |
| QBFEVAL 数据、公开和隐藏实例及变换副本 | [QBFEVAL 2020 官方规则](https://www.qbflib.org/qbfeval20.php)；[ParaProofa v1 补充材料](https://doi.org/10.5281/zenodo.18832723)，CC BY 4.0 | 署名 Mark Peyrer、Maximilian Heisinger、Martina Seidl 及原始实例族。三个 BMC 实例保留 University of Toronto 2007 非商业教学研究条款。参见[逐实例来源记录](third-party/qbf-data-distribution-source.json)和[所含材料列表](third-party/qbf-data-distribution-files.json)。 |

log4j 1.2.8 条款要求的确切致谢原文为：“This product includes software developed by the Apache Software Foundation (http://www.apache.org/).” 完整原始条款位于 `third-party/Log4j-1.2.8-Apache-1.1.txt`。

<a id="lean-construction-and-system-components"></a>

## Lean、构造与系统组件

读法说明：每行列出固定组件或数学数据来源。

| 资源 | 来源与条款 | 署名与分发条件 |
|---|---|---|
| Lean 4.33.0-rc1 和 elan 4.2.3 | [Lean 许可](https://github.com/leanprover/lean4/blob/v4.33.0-rc1/LICENSE)和 [elan 许可](https://github.com/leanprover/elan/blob/master/LICENSE)，Apache-2.0 | 保留两者声明，以及镜像所含组件适用的声明。 |
| mathlib 提交 `5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3` | [固定 mathlib 许可](https://github.com/leanprover-community/mathlib4/blob/5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3/LICENSE)，Apache-2.0 | 保留文件级版权头。源码、编译缓存、版本和声明应相互匹配。 |
| Batteries、Aesop、Qq、ProofWidgets、ImportGraph、LeanSearchClient 和 Plausible | 各固定提交的许可；Apache-2.0 声明位于 `third-party/` | 保留组件声明。ProofWidgets 生成的浏览器代码包含使用各自许可的依赖；参见[前端许可记录](third-party/proofwidgets-npm-license-materials.json)。 |
| Lean4 CLI 提交 `da07ca808b6718cb2aed14dba154e5a08b8f8ecf` | mhuisi；[固定许可](https://github.com/leanprover/lean4-cli/blob/da07ca808b6718cb2aed14dba154e5a08b8f8ecf/LICENSE)，MIT | 保留其 MIT 声明；它独立于 Lean 的 Apache-2.0 许可。 |
| 基于 FormalizedFormalLogic/Foundation 的 Frege 定义层 | [上游许可](https://github.com/FormalizedFormalLogic/Foundation/blob/master/LICENSE)，Apache-2.0 | 署名 FormalizedFormalLogic/Foundation 贡献者，保留许可及[来源记录](third-party/frege-reference-source.json)中的改编说明。 |
| 含 136 个码字的二元码参考：`tasks/construction/binary-code-a24-10/solution/` | Laaksonen 和 Östergård；根据[论文](https://arxiv.org/abs/1604.06022)中的参数和轨道代表元转换得到 | 署名作者并标明来源。任务内容包含转换后的码字。参见[参考记录](third-party/a24-reference-source.json)。 |
| 极值图参考：124 个顶点、629 条边及 Lean 编码 | Jan Goedgebeur、Jorik Jooken、Gwenaël Joret 和 Tibo Van den Eede；[固定上游来源](https://github.com/AGT-Kulak/searchMaxSizeMinGirth/tree/f6c80b4aa75236b0d4e6ff4f11f197621080f180)，GPL-3.0 | GPL-3.0 适用于上游代码和图数据。保留原图、Lean 源码、署名、GPL 文本和转换说明。包含 GPL 材料的组合作品必须满足 GPL 条款。参见[来源记录](third-party/extremal-graph-source.json)和[组件文件列表](third-party/extremal-graph-distribution-files.json)。 |
| 本地生成示例，包括 Petersen 图、交叉多胞形和根系 | 各任务的生成代码和说明 | 将数学对象数据与复制的代码和第三方程序分别处理；对实际材料应用各来源条款。 |

容器镜像包含 Debian、Ubuntu、GNU 工具、Java、Python 和其他系统组件。各组件保留自身许可。保留组件声明，并在要求时提供对应源码。精确版本和源码位置见[系统许可材料](third-party/system-license-materials.json)。

ProofWidgets 中嵌入的 Graphviz 15.0.0 采用 EPL-2.0；外层 `@hpcc-js/wasm` 包采用 Apache-2.0。分发时必须包含 EPL 文本，并提供获取 Graphviz 源码及修改的可用途径。Expat 2.8.1、Emscripten 6.0.0 和 Penrose Rust 组件保留原始许可；参见[内嵌组件记录](third-party/proofwidgets-embedded-components.json)。

<a id="additional-full-materials"></a>

## Full 附加材料

以下声明也适用于 Full 和同源离线包：

- **JSPLIB 数据：** ScheduleOpt/benchmarks 及相应改编采用 CC BY-SA 4.0。署名原始实例作者和 ScheduleOpt 贡献者；参见[来源记录](third-party/full-review.json)。
- **MCQD 最大团代码：** `mcqd_anytime.h` 带有 Janez Konc 的 GPL-3.0-or-later 声明。保留其文件头，并标明节点限制、时间限制、输出移除和最优性查询修改。
- **电路定义：** Copyright 2026 Samuel Schlesinger，Apache-2.0；用于 `np-vs-acc` 和 `nexp-vs-tc0`，修改见源码头说明。
- **张量秩定义：** Copyright 2026 Jeroen Zuiddam，Apache-2.0；形式化源码署名 Christandl、Hoeberechts、Nieuwboer、Vrana 和 Zuiddam。参见逐任务来源记录。
- **排序网络比较器：** Green 1969；相同的比较器数据来自固定 SorterHunter 文件，Copyright 2017 Bert Dobbelaere，MIT。分发转换后的 Lean 元组时，保留署名和许可。
- **PACE 2019 实例：** M. Ayaz Dzulfikar、Johannes K. Fichte 和 Markus Hecher；官方 [Zenodo 记录 3368306](https://zenodo.org/records/3368306)，CC BY 4.0。保留其他原始来源和转换说明。
- **MaxSAT Evaluation 2026 补充材料：** Dieter Vandesande、Christoph Jabs、Jeremias Berg、Johannes Fichte、George Katsirelos、Ruben Martins、André Schidler 和 Dominik Schreiber；[Zenodo 记录 21358014](https://zenodo.org/records/21358014)，CC BY 4.0。保留实例族署名；所含求解器软件保留自身许可。
- **PACE 2024 判分器：** Copyright 2023 Philipp Kindermann、Fabian Klute 和 Soeren Nickel，MIT。保留所含 wheel 中的声明。

[逐任务许可记录](third-party/full-review.json)标明其他 MIT、BSD 风格、CC0、Apache 和 GPL 组件。对于条款尚未确认的材料，遵循[分发条件](distribution.zh-CN.md)。
