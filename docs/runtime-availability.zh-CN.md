本参考文档介绍运行 TCSExam 所需的主机和镜像条件。
面向配置评测主机资源或准备判分服务的用户。

<a id="runtime-requirements"></a>

# 运行环境要求

[English](runtime-availability.md) | [简体中文](runtime-availability.zh-CN.md)

<a id="host-and-task-resources"></a>

## 主机与题目资源

在 Linux x86-64 上运行，使用 Python 3.12+、Docker Engine、Compose 和 Buildx。
使用评测用户可以访问的本地 Docker Unix socket。CLI 和 Docker 必须使用相同的
题目与任务输出路径；不接受远程 SSH/TCP Docker context。安装检查见
[运行评测](running.zh-CN.md#install-and-select)。

每道 Lean 题申请 4 个 CPU 核和 16 GiB 内存。为操作系统和构建预留额外资源，
并为共享 Lean 环境、镜像层和日志预留至少 40 GB 磁盘。这部分磁盘空间涵盖共享
环境；Full 构建还需要存放所选数据集和镜像。

Solver 资源要求因题目和数据划分而异。请查看题目的 `task.toml`，以及控制器或
后端规划器生成的资源计划。主机必须能够同时容纳开发容器、控制器预留资源，
以及至少一个获得题目规定的完整单实例资源的 worker。降低题目并发数无法减小
单个 worker 的资源需求。实例调度保留每个实例的计算资源和时间配额；共享时间池
题将完整时间池保留在同一个 worker 中。见 [Offline 资源规则](offline-adapters.zh-CN.md)
和 [Online 后端资源](backend/docker.zh-CN.md#resources-and-lifecycle)。

读法说明：按题目组查看。镜像角色说明所选题目需要准备哪些镜像。

| 题目组 | 镜像角色 | 额外执行要求 |
|---|---|---|
| 定理证明、构造和开放猜想 | 开发环境和独立判分器 | Harbor 支持镜像及题目声明的资源 |
| Offline Solver | 开发环境、判分控制器和判分 worker | 控制器可访问 Docker socket，并以只读方式查看 cgroup |
| Online Solver | 开发环境和后端判分 worker | 运行中的后端、服务凭据，以及开发容器和判分容器均可访问的地址 |

两种 Solver 方式都要求启用 Landlock ABI 3 或以上版本、允许 Landlock 系统调用，
并在判分容器中以 root 身份进行监督管理。构建和求解器命令以受限权限运行。
[隔离预检查](judge-execution-isolation.zh-CN.md)在执行主机上检查实际准备的镜像。
如果检查失败，应修正主机策略或换用受支持的主机，然后再开始评测。

<a id="prepare-and-check"></a>

## 准备与检查

对于默认的 Lite 选择：

```bash
tcsexam source-inputs
tcsexam build --suite lite
tcsexam doctor --suite lite --output build/lite-readiness.json
```

`build` 准备题目镜像和配套的 Harbor 主机支持镜像。固定输入及其获取命令见
[资源准备](resources.zh-CN.md)。对于外部准备的镜像，通过 `--artifacts` 提供完整清单；
其中的记录必须标明实际镜像和 Harbor 支持产物。

`doctor` 在 JSON 报告中写入所选题目的前置条件和 `blockers`。
在执行 `run` 前解决这些问题。agent 检查核验配置和本地凭据是否存在，不会连接
模型服务。Online 服务配置与连通性检查见
[后端指南](backend/docker.zh-CN.md#check-and-start)。

<a id="verification-and-results"></a>

## 验证与结果

Lean 判分器使用固定的项目和依赖配置。定理证明题和构造题接受
`Task/Basic.lean`；开放猜想题还接受各题文档说明的额外 Lean 源文件。
提交中的构建配置、依赖目录、编译文件和评分脚本会被忽略。
提交源码路径中的符号链接会被拒绝。

最终 Lean 源码必须使用普通定义和证明。所有提交源文件中，运行自定义元程序
或改变 elaboration 过程的命令都会被拒绝，例如 `run_cmd`、`run_tac`、`elab`、
`macro`、`initialize` 和 `#eval`。判分器检查公理的完全限定名。
构造题保留题目文档说明的 `native_decide` 支持；在接受之前，会通过求值检查其
生成的布尔等式。开放猜想题若提交同时通过猜想及其否定的检查，得分为零。

Solver 隐藏输入只提供给判分环境。模型开发容器既没有这些输入，也没有 Docker
socket。Online 归档凭据仅供最终验证使用；见
[运行 Online Solver](running.zh-CN.md#online-solver)。

成功执行的评分器会输出有限数值的 Harbor 奖励。`score-details.json` 或
`judge_result.json` 等题目详细报告说明结果。判分失败时，应先检查判分器日志和
异常，再确定分数。通过[结果检查](running.zh-CN.md#keep-outputs-and-statuses)定位这些
文件，并将已完成判分的零分与执行失败分开记录。
