本参考文档介绍 TCSExam 源码包及其构建入口。
供从源码准备环境或创建源码分发包的用户阅读。

<a id="source-packages"></a>

# 源码包

[English](source-delivery.md) | [简体中文](source-delivery.zh-CN.md)

仓库包含 100 道题，共 130 个任务文件夹：70 个共用的 Lean 文件夹，以及 30 道分别提供 Online 和 Offline 文件夹的 Solver 题。Lite 从 Full 的各类题目中选取 20 道，使用相同的题目文件夹。

读法说明：按目录查看内容。运行产物与源码分开存放。

| 路径 | 内容 |
|---|---|
| `tasks/` | 题面、任务配置、环境构建配方和判分器 |
| `suites/` | Full/Lite 任务选择及任务、协议路径 |
| `src/tcsexam/` | 命令行工具、计分、判分后端和固定计分参照 |
| `assets/` | 资源清单、固定输入配方、环境构建和声明 |
| `docs/` | 使用说明、技术参考、来源与许可 |

每道任务均采用 Harbor 的文件夹格式，包含 `instruction.md`、`task.toml`、`environment/` 和 `tests/`。运行镜像、大批量准备的数据集、模型输出和参考答案归档是单独的产物。

<a id="build-from-source"></a>

## 从源码构建

按照[快速开始](getting-started.zh-CN.md)安装命令行工具并检查宿主机。构建入口为：

```bash
tcsexam source-inputs
tcsexam build --suite lite
```

`source-inputs` 准备固定的公开 Lean 源码归档。`build` 在 Docker 宿主机上准备选定的依赖和镜像。固定输入、获取失败、镜像清单及缩小构建范围的说明见[资源准备](resources.zh-CN.md)。普通评测使用任务输入和判分器；参考答案归档是[参考答案工具](oracle-answers.zh-CN.md)的可选输入。

要准备全部任务变体，先使用 Online Solver 构建一次 Full，再构建 Offline Solver 题型：

```bash
tcsexam build --suite full --solver-protocol online
tcsexam build --suite full --track solver --solver-protocol offline
```

通过[运行评测](running.zh-CN.md)配置模型并检查所选运行环境。Online Solver 还需要[后端服务](backend/docker.zh-CN.md)。

<a id="export-and-redistribution"></a>

## 导出与再分发

[CONTRIBUTING.md](../.github/CONTRIBUTING.zh-CN.md) 提供源码导出命令和开发检查。导出时将源码与缓存、凭据及评测输出分离。保存实验时，也应将运行镜像和作业目录分别保留。

保留适用的[许可证与声明](licenses/README.zh-CN.md)。[分发条件](licenses/distribution.zh-CN.md)说明哪些第三方材料和镜像可以共享。
