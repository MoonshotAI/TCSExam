<a id="resource-inventories"></a>

# 资源清单

[English](README.md) | [简体中文](README.zh-CN.md)

这些清单描述任务环境、数据准备和源码来源。
供维护构建配方的贡献者阅读；路径均相对于仓库根目录。

读法说明：每行列出一个文件或目录及其内容。

| 文件或目录 | 内容 |
|---|---|
| `images.json` | 运行、工具和数据产物，镜像标识、依赖及获取配方 |
| `files.json` | 未随包提供的源码输入、路径、大小、哈希值、权限模式和分发条件 |
| `sources.json` | 来源提交、原始哈希值和当前打包哈希值 |
| `data/` | 数据准备配方、逐文件清单和共用的数据镜像 Dockerfile |
| `build-inputs.json` | Dockerfile FROM/COPY/ADD 依赖及未随包提供的输入 |
| `resource-groups.json` | 按用途及分发条件分组的未随包提供文件 |
| [`environments/lean-base/`](../docs/environments/lean-base/README.zh-CN.md) | 共用 Lean 构建材料及固定依赖版本 |
| `environments/cpsolver/` | CPSolver 源码和构建材料；参见[说明](../docs/licenses/cpsolver-source.zh-CN.md) |

使用 `tcsexam build` 根据这些配方准备所选资源。它会下载固定输入、构建依赖，并组装 Harbor 使用的完整镜像。数据镜像在构建阶段提供文件。生成的镜像标识存入本地缓存，供 `doctor` 和 `run` 使用。外部的 `artifacts.json` 可提供可选的不可变镜像分配。命令及输入要求参见[资源准备](../docs/resources.zh-CN.md)。

将公开练习数据、隐藏判分数据和参考答案分别保存在各自产物中。开发镜像和公开自测镜像的每一层均不得包含隐藏输入。完整镜像继承其输入的[分发条件](../docs/licenses/distribution.zh-CN.md)。

生成的镜像、数据集、作业和私有配置存放在源码包之外。[贡献指南](../.github/CONTRIBUTING.zh-CN.md)介绍源码检查和导出。
