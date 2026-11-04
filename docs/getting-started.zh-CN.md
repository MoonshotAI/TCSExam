这份指南介绍如何运行一道定理证明题并查看结果。
适合已准备 Linux 主机和模型 API 的首次使用者。

<a id="run-tcsexam-from-scratch"></a>

# 快速开始

语言：[English](getting-started.md) | [简体中文](getting-started.zh-CN.md)

[文档首页](index.zh-CN.md) · 参数查询：[运行配置与参数](running.zh-CN.md)

以下命令使用 Bash；请替换 `YOUR_...` 占位值。你需要准备 Docker 主机和模型
API。模型通过 agent 命令行程序在题目容器内编辑文件、执行工具，提交结果由
独立判分器检查。指南默认使用 Kimi Code；如果选择 Claude Code、Codex 或
Grok Build，在第 3 步使用[对应配置示例](running.zh-CN.md#agent-examples)，之后沿用
相同流程。模型 API 位于远端时，执行主机通常不需要 GPU。

<a id="1-prepare-the-host"></a>

## 1. 准备主机

使用 Linux x86-64、Python 3.12 及以上版本、Docker Engine、Compose 和 Buildx。
Ubuntu 24.04 可先安装：

```bash
sudo apt update
sudo apt install -y git curl ca-certificates nano python3 python3-venv python3-pip libarchive13t64
python3 --version
uname -m
```

确认 Python 版本至少为 3.12，架构为 `x86_64`。`libarchive13t64` 为后续 Lite
中的 BPPLIB 数据集提供 RAR 支持；其他发行版可能将该包命名为 `libarchive13`。

按照 [Docker 官方 Ubuntu 安装说明](https://docs.docker.com/engine/install/ubuntu/)
安装 Docker Engine 及 Compose、Buildx 插件。为运行评测的用户配置 Docker
访问权限，然后检查：

```bash
docker info
docker compose version
docker buildx version
docker buildx inspect --bootstrap
```

如果出现权限错误，检查用户对 Docker socket 的访问权限；修改 Docker 用户组后
需要重新登录。Docker 用户组拥有较大的主机控制权限。后续命令均在这台主机上
执行；长时间 SSH 会话可以使用 `tmux` 等会话管理工具。

第一道题申请 4 个 CPU 核和 16 GiB 内存。8 核、32 GiB 的主机可以为操作系统
和准备工作留出余量。共享 Lean 环境至少预留 40 GB 磁盘，另需下载、构建和
结果空间。Solver 题另有资源要求，并且需要启用 Landlock ABI 3 或以上版本。
运行 Lite 或 Full 前，检查[运行环境要求](runtime-availability.zh-CN.md)。如果主机
无法容纳一个按题目规格分配资源的判分 worker，请使用资源更多的主机。

<a id="2-clone-and-install"></a>

## 2. 克隆并安装

克隆仓库并安装运行依赖：

```bash
git clone https://github.com/MoonshotAI/TCSExam.git TCSExam
cd TCSExam
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[runtime,backend]'
tcsexam --help
tcsexam validate
```

这两个依赖组安装 Harbor 0.22.0，以及后续 Full Online 使用的后端依赖。
`validate` 检查源码中的题目配置。后续命令均从仓库根目录执行；每次打开新终端，
先进入该目录并激活 `.venv`。

<a id="3-configure-the-model"></a>

## 3. 配置模型

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

将以下配置改为模型服务提供方给出的值，保留引号：

```bash
TCSEXAM_AGENT="kimi-code"
TCSEXAM_API_BASE_URL="https://YOUR_PROVIDER.example/v1"
TCSEXAM_MODEL="YOUR_MODEL_ID"
TCSEXAM_API_KEY="YOUR_API_KEY"
```

填写服务提供方的 API 地址和准确模型 ID。默认 agent 是 Kimi Code，服务需要
支持该 agent 使用的 API 和配置。使用其他 agent 时，先按
[agent 配置](running.zh-CN.md#choose-an-agent)设置地址、模型和可选参数。

在每个用于发起任务的终端中显式加载配置：

```bash
set -a
source .env
set +a
```

CLI 不会自动读取 `.env`。该文件已被 Git 忽略，请勿将真实密钥写入公开日志或
Issue。`tcsexam run` 开始调用模型并产生 API 用量；构建和预览配置不需要模型密钥。

下载缓存需要放到其他磁盘时，在 `.env` 中将 `TCSEXAM_CACHE` 设为可写的绝对路径，
然后重新加载。该设置只移动准备缓存；Docker 镜像层仍使用 Docker 的存储目录。
分别检查两处空间：

```bash
docker info --format '{{.DockerRootDir}}'
df -h
```

<a id="4-build-and-check-one-task"></a>

## 4. 构建并检查一道题

先运行 Lite 中的定理证明题 `discrete-bidding-games`：

```bash
tcsexam list --suite lite
tcsexam source-inputs
tcsexam build --suite lite --task discrete-bidding-games
tcsexam doctor --suite lite --task discrete-bidding-games \
  --output build/first-readiness.json
```

`source-inputs` 获取并核验固定版本的 Lean 构建归档。`build` 准备开发镜像和
独立判分镜像，保存镜像记录。后续命令在选择和缓存一致时复用这些产物。

打开 `build/first-readiness.json`，处理其中的 `blockers`。下载或校验和失败时，
查看[资源准备](resources.zh-CN.md)；其中提供了上游下载受阻时导入指定原始文件的命令。
镜像或主机错误见[故障处理](#troubleshooting)。检查报告核验本地配置；agent 开始运行后
才会连接模型服务。

在不调用模型的情况下预览任务配置：

```bash
tcsexam prepare --suite lite --task discrete-bidding-games \
  --output build/first-job.json
python -m tcsexam.harbor_launch run \
  --config build/first-job.json --print-config
```

命令生成 `build/first-job.json` 和 `build/first-job.selection.json`，并准备引用
实际镜像的运行时题目副本。保持源码中的 `task.toml` 不变。运行前检查配置中的
模型和题目选择。

<a id="5-run-the-task"></a>

## 5. 运行这道题

```bash
tcsexam run --suite lite --task discrete-bidding-games \
  --attempts 1 --concurrency 1 --output build/first-job.json
```

该命令开始产生模型 API 用量。Harbor 提示加载声明的主机环境变量时，检查后确认。
`run` 会检查前置条件，重新生成任务配置，然后启动这道题的一次尝试。

每次尝试的模型开发预算为 43,200 秒，超时倍率为 1。安装、环境准备和最终判分
各有独立时限，详见[各阶段预算](running.zh-CN.md#settings-and-budgets)。模型可以提前交卷。

服务返回认证或模型错误时，检查密钥、地址、模型 ID，以及所选 agent 使用的 API。
启动下一次尝试前，先按下一步保留本次失败的日志。

<a id="6-read-the-actual-result"></a>

## 6. 查看实际结果

从生成的配置定位结果目录，并打印每次尝试的实际结果：

```bash
python - <<'PY'
import json
from pathlib import Path
config = json.loads(Path('build/first-job.json').read_text())
job = Path(config['jobs_dir']) / config['job_name']
print('Job directory:', job)
for path in sorted(job.rglob('result.json')):
    result = json.loads(path.read_text())
    if 'trial_name' in result:
        print('\nAttempt:', result['trial_name'])
        print('Verifier result:', result.get('verifier_result'))
        print('Exception:', result.get('exception_info'))
        print('Details:', path.parent)
PY
```

每次尝试的目录包含 `result.json`、`agent/` 日志、`verifier/` 输出和 `artifacts/`。
结合判分日志和题目详细报告理解得分。产物收集清单给出了 `/app` 工作文件的保存
位置。[结果保存参考](running.zh-CN.md#keep-outputs-and-statuses)说明完整目录结构及检查命令。

已完成的判分可能得到零分。启动失败、判分器崩溃或判分结果缺失需要进一步检查，
记录时应与有效零分分开。更新或替换一次尝试前，保存整个任务结果目录，以及任务
配置和选择记录两个 JSON 文件。

<a id="next-lite-or-full"></a>

## 下一步：Lite 或 Full

<a id="7-run-all-20-lite-tasks"></a>
<a id="8-run-full"></a>
<a id="9-calculate-suite-scores"></a>

- [运行 20 道题的 Lite](running-suites.zh-CN.md#run-all-20-lite-tasks)。
- [运行 100 道题的 Full](running-suites.zh-CN.md#run-full)。
- [计算各题型分数和 Index](scoring.zh-CN.md)。

<a id="troubleshooting"></a>

## 故障处理

表格按现象查阅。修复准备阶段的错误后，使用相同选择复用已核验的缓存。

| 现象 | 处理方法 |
|---|---|
| Docker 权限不足 | 检查 socket 访问权限；修改用户组后重新登录 |
| Docker 或缓存磁盘空间不足 | 分别检查两处存储，按需移动缓存或增加 Docker 存储空间 |
| 下载或校验和失败 | 按[资源准备](resources.zh-CN.md)中的固定来源和指定文件导入方法处理 |
| 镜像缺失或记录过期 | 使用相同题目、协议、缓存和 Docker 目标重新执行 `build` |
| `doctor` 报告问题 | 根据报告修复镜像、主机、资源或后端要求，再执行 `run` |
| Landlock 预检查失败 | 检查执行主机的内核支持和容器系统调用策略 |
| Online 服务无法访问 | 检查 `serve`、host-gateway 路由、两个终端的凭据和后端计划 |
| 模型服务返回 401 或模型不存在 | 检查密钥、地址、模型 ID 和 agent 的 API 兼容性 |
| 分数为零或缺失 | 先检查尝试中的异常和判分输出，再记录结果状态 |

<a id="switch-agents"></a>

## 切换 agent

使用[四种 agent 的配置示例](running.zh-CN.md#agent-examples)，改用新的输出文件名，
再执行准备、检查和运行命令。在每个发起任务的终端重新加载所选配置。
[运行配置与参数](running.zh-CN.md)同时列出了 agent 专用限制，以及切换时需要清除的设置。
