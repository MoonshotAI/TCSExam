<a id="resource-access-and-distribution-conditions"></a>

# 资源访问与分发条件

[English](distribution.md) | [简体中文](distribution.zh-CN.md)

中文译文供参考，许可条款以原文为准。

本指南列出 TCSExam 资源的获取途径和共享条件。
供在本地准备数据，或分发源码、数据及镜像的用户阅读。

<a id="apply-conditions-to-the-selected-material"></a>

## 对所选材料应用相应条件

使用 [`tcsexam build`](../resources.zh-CN.md) 获取固定官方输入、验证并转换它们，再组装本地镜像。标记为 `local_prepare` 的资源可按其来源条款在本地准备。`private_only` 表示该材料不得包含在公开源码导出和公开镜像分发中。

再分发产物前，遵循下述资源具体条件，并保留所需源码、署名和声明。每行适用于指定材料和版本；镜像需要同时满足全部输入及继承层的条件。本地生成产物保留来源材料适用的限制。精确产物标识和文件范围见链接记录。

<a id="data-and-task-materials"></a>

## 数据与任务材料

读法说明：逐资源查看。来源链接和记录标明覆盖的输入；共享条件同时适用于生成材料及包含它们的镜像。

| 资源 | 获取途径与来源 | 条款与处理方式 |
|---|---|---|
| 原创代码、判分器、脚本和构建配置 | 仓库源码 | 在项目贡献者拥有相应权利的范围内采用 Apache-2.0。保留作者声明、`LICENSE` 和 `NOTICE`，并标明修改。 |
| 原创题面、说明文档和网站内容 | 仓库源码和网站仓库 | 在项目贡献者拥有相应权利的范围内采用 CC BY 4.0。保留署名并标明修改。 |
| QBF 评测数据：十三个公开实例和 57 个隐藏变换实例 | Mark Peyrer、Maximilian Heisinger 和 Martina Seidl 的 [ParaProofa v1 补充材料](https://doi.org/10.5281/zenodo.18832723)；[固定来源记录](third-party/qbf-data-distribution-source.json) | CC BY 4.0，署名补充材料作者及原始实例族。三个 BMC 实例 `ex018`、`ex019` 和 `ex020` 还保留 University of Toronto 2007 非商业教学研究条款，包括不收费、声明和宣传条件。固定产物范围列于下方。补充材料中的软件保留自身许可。 |
| BPPLIB 实例、装箱方案及注册表提取数据 | [BPPLIB](https://github.com/mdelorme2/BPPLIB) 的固定官方文件；[准备记录](third-party/bpplib-reconstruction.json) | CC BY-NC-ND 4.0。保留署名、非商业和禁止演绎条件。生成文件和所有包含它们的镜像均限于本地使用，不得放入公开镜像仓库或公开下载。 |
| PACE 2019 Vertex Cover 公开开发数据 | public-v2 归档的[来源记录](third-party/vc-pace2019-source.json)；[Zenodo 数据集](https://zenodo.org/records/3368306) | M. Ayaz Dzulfikar、Johannes K. Fichte 和 Markus Hecher 的 CC BY 4.0。范围：`solver-vc-pace2019-development-data`，包含使用 XZ 5.2.5 重新压缩的 100 个奇数编号公开实例。保留 CC BY 文本、`PACE2019-VC-NOTICE.txt`、来源和 PACE 报告链接、图实例族署名及重新压缩说明。 |
| PACE 2021 Cluster Editing 公开开发数据 | [固定来源与 XZ 重建记录](third-party/ce-pace2021-source.json) | CC0-1.0 覆盖 `solver-ce-pace2021-development-data` 中 100 个奇数编号公开实例。附上 CC0 文本和来源记录。 |
| PACE 2022 Directed Feedback Vertex Set 公开开发数据 | [固定来源与重建记录](third-party/dfvs-pace2022-source.json) | 仅限本地准备：官方归档没有数据许可。保留其声明，官方归档、生成实例及包含它们的镜像均不得公开分发。PACE 报告自身采用 CC BY 4.0。 |
| PACE 2024 OSCM 公开开发数据 | [两个固定官方归档](third-party/oscm-pace2024-source.json) | 合并后的 173 文件产物仅限本地使用。MIT 覆盖 60 个中等规模和十三个微型测试集实例；100 个 Exact Track 实例没有数据许可。保留来源声明及测试集 MIT 文本。两个官方归档、合并生成的产物及包含它们的镜像均不得公开分发。准备时排除上游 `.sol` 文件。 |
| AHC058 公开开发数据 | [官方 AtCoder 归档与锁定生成器](third-party/ahc058-atcoder-source.json) | 仅限本地准备：尚未确定题面、输入、生成器、计分程序或可视化程序的开放再分发许可。保留来源声明。官方归档、生成实例及包含它们的镜像均不得公开分发。 |
| 课程排课实例 | [cb-ctt](https://github.com/iolab-uniud/cb-ctt) 提供二十个对应实例及变换；[来源比较](third-party/ctt-source-comparison.json) | 原作者提供 CC BY 4.0。标明格式和名称变化，包括 `comp15` 对应官方 `comp03`。`comp11` 和 OptHub 解需要遵循自身来源条款；请从[官方来源](https://www.eeecs.qub.ac.uk/itc2007/)获取。其再分发条款尚未确认。 |
| IWLS 2022 公开真值表 | [固定来源与变换记录](third-party/logic-syn-iwls2023-source.json) | 为 100 个公开真值表保留 IWLS 2022 的 MIT 许可，并标明变换。ABC 归档采用下方单列的软件条款。 |
| MQLib 实例 | [各实例族来源与许可记录](third-party/mqlib-family-license-review.json) | OR-Library 实例 `g001642`、`g002564` 和 `g002776` 有明确的 MIT 许可依据；保留 J. E. Beasley 署名和完整许可证。其他实例族按各自条款从相应来源获取。 |
| ROADEF/EURO 2012 实例和参考分配方案 | [固定 Google OR-Tools 源码](https://github.com/google/or-tools/tree/06376d5ff5bbaead64e9b2df61ccbe74e99e5f8c/data/roadef_challenge_2011/solution_checker)；[来源链记录](third-party/roadef-hidden-source-chain.json) | 所含实例和判分器源码采用 Apache-2.0。保留 Google 署名、许可及修改说明。参考分配方案是项目生成的数值输出，单独记录。从[官方页面](https://www.roadef.org/challenge/2012/en/sujet.php)获取竞赛 PDF；其再分发条款尚未确认。 |
| MaxSAT 隐藏数据 | [固定官方 Zenodo 归档与重建配方](../../assets/data/solver/solver-maxsat-mse-judging-data-recipe.json) | MaxSAT Evaluation 2026 补充材料采用 CC BY 4.0。保留[第三方声明](THIRD_PARTY_NOTICES.zh-CN.md#additional-full-materials)中的补充材料及实例族署名。所含求解器程序保留自身许可。 |
| 参考答案内容 | [参考答案处理](../oracle-answers.zh-CN.md) | 将具体可通过判分的答案保存在模型解题环境之外。默认保持私有，普通构建和运行无需这些答案。对于获准分发的答案产物，应使用显式发布接口，并遵循资源具体条件。 |
| 论文、规则 PDF、模型输出和其他外部材料 | 原始来源及各材料具体许可 | 遵循所共享材料的条款。软件或数据集许可仅适用于其覆盖的内容。 |

固定 QBF 产物范围为 `qbf-public`、`qbf-judging`、`qbf-qbfeval-online-development`、`qbf-qbfeval-offline-development`、`qbf-qbfeval-online-backend`、`qbf-qbfeval-offline-verifier` 和 `backend-public-online-qbf-qbfeval`。对应的固定变换数据、标准答案及 `ex*` 映射具有[来源记录](third-party/qbf-data-distribution-source.json)中记载的数据许可。任何分发产物都应附带适用的软件、系统和逐实例声明，答案内容还应遵循答案处理指南。

<a id="tools-and-runtime-components"></a>

## 工具与运行组件

读法说明：每行给出组件许可，以及源码或替换要求。

| 资源 | 获取途径与来源 | 条款与处理方式 |
|---|---|---|
| PACE 2021 Cluster Editing 和 PACE 2022 Directed Feedback Vertex Set 判分器 | 固定官方 [2021 ZIP](https://pacechallenge.org/2021/verifier.zip) 和 [2022 tar.gz](https://pacechallenge.org/2022/verifier.tar.gz)，通过本地配方编译 | 再分发条款尚未确认。在本地下载和编译，保留上游声明，并将源码快照及生成镜像保持私有。 |
| VC 公开自测判分器 | `backend-public-online-vc-pace2019` 的[组件要求](third-party/vc-public-judge-image.json) | 保留项目和数据许可、vc_validate 对应源码及构建说明，以及适用的系统包源码材料。 |
| OSCM NumPy 开发工具 | [固定 NumPy 2.2.6 wheel](third-party/oscm-pace2024-development-tools-source.json) | 仅限本地准备。配方验证 wheel 及其 RECORD 条目，并保留四份上游声明。随附依赖的源码义务尚未确认；wheel、工具镜像及包含它们的镜像均保持私有。 |
| CPSolver、dom4j 和 log4j | [源码、构建与替换指南](cpsolver-source.zh-CN.md) | Java 源码：LGPL-3.0-or-later；原始 Ant 文件：LGPL-2.1-or-later；dom4j：五条款 BSD 风格条款；log4j：Apache Software License 1.1。分发二进制文件时附上要求的对应源码、构建材料和完整声明。 |
| Qute、drat-trim 和 qrp2rup | [第三方声明](THIRD_PARTY_NOTICES.zh-CN.md)中的固定源码 | Qute 后来添加的 MIT 声明是否适用于较旧快照尚未确认；保留原始版本及版本比较。drat-trim 采用 MIT。qrp2rup 依照作者补充材料采用 CC BY 4.0：署名、标明修改，并随二进制文件提供源码。分别保留 MiniSat 和 docopt.cpp 的 MIT/Boost 声明。 |
| MQLib 软件 | [MQLib 仓库](https://github.com/MQLib/MQLib) | MIT。保留版权、许可证及修改声明。实例数据适用上方各实例族条款。 |
| ABC 源码 | [固定来源记录](third-party/logic-syn-iwls2023-source.json) | 保留 UC Regents BSD 风格声明。 |
| Lean、mathlib、elan 和系统包 | [系统来源](third-party/system-license-materials.json)、[附加包描述](third-party/lean-public-rebuild-system-materials.json)及 [mathlib 清单](third-party/lean-public-rebuild-mathlib-materials.json) | 保留各组件声明，并在许可要求时提供完整对应源码。源码、编译缓存和版本应相互匹配。 |
| 智能体工具 | 固定 Harbor 运行时安装器；[智能体工具记录](third-party/claude-code-distribution.json) | 智能体包保留自身许可。记录中的 Claude Code 包声明保留所有权利，没有一般性再分发授权；应在运行时安装，并从分发的环境镜像中排除。 |
| ProofWidgets 中的 Graphviz 及其他浏览器组件 | [内嵌组件记录](third-party/proofwidgets-embedded-components.json)和 [Graphviz 源码材料](../environments/lean-base/graphviz-epl/SOURCE-OFFER.zh-CN.md) | Graphviz 采用 EPL-2.0，封装层采用 Apache-2.0。通过 `tcsexam source-inputs` 准备固定源码归档。保留 EPL 文本、Graphviz 对应源码、封装层修改和构建规则，以及安装在 `/usr/share/doc/tcsexam/` 下适用的 Lake、浏览器和 npm 声明。 |

署名文本见[第三方声明](THIRD_PARTY_NOTICES.zh-CN.md)，固定文件清单见[组件记录](full-review.zh-CN.md)。[文件清单](../../assets/files.json)和[镜像清单](../../assets/images.json)记录输入路径、产物标识和可用获取地址。
