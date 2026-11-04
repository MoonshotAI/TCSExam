<a id="component-source-and-license-records"></a>

# 组件源码与许可记录

[English](full-review.md) | [简体中文](full-review.zh-CN.md)

中文译文供参考，许可条款以原文为准。

本页给出 TCSExam 组件的固定来源、文件及许可记录位置。
供检查署名或准备分发的用户阅读。

首先查看[许可](README.zh-CN.md)中的项目许可，以及[分发条件](distribution.zh-CN.md)中的各资源要求。[第三方声明](THIRD_PARTY_NOTICES.zh-CN.md)列出组件作者和条款；原始许可文本保存在 [third-party/](third-party/) 中。

<a id="find-a-component-record"></a>

## 查找组件记录

读法说明：每行列出相应材料的记录。记录标明固定版本和路径；使用与所分发资源对应的条目。

| 材料 | 记录 |
|---|---|
| 任务代码、数据和参考材料 | [逐任务来源与许可清单](third-party/full-review.json)及[资源分发记录](third-party/distribution-decisions.json) |
| 运行镜像 | [镜像组件清单](third-party/image-license-inventory.json)、[系统包材料](third-party/system-license-materials.json)及[镜像清单](../../assets/images.json) |
| Lean 包和缓存 | [Mathlib 材料](third-party/lean-public-rebuild-mathlib-materials.json)及[附加系统材料](third-party/lean-public-rebuild-system-materials.json) |
| ProofWidgets 浏览器代码 | [前端依赖材料](third-party/proofwidgets-npm-license-materials.json)、[内嵌组件](third-party/proofwidgets-embedded-components.json)及 [Graphviz 源码材料](../environments/lean-base/graphviz-epl/SOURCE-OFFER.zh-CN.md) |
| CPSolver 及其依赖 | [源码、构建与替换指南](cpsolver-source.zh-CN.md) |
| 资源获取和本地准备 | [资源指南](../resources.zh-CN.md)、[文件清单](../../assets/files.json)及[数据配方](../../assets/data/) |

逐任务清单按照固定源码版本记录材料。同源任务变体保留各材料的具体条款。共享镜像时，应按所有所含组件的精确固定版本，收集适用声明和对应源码。
