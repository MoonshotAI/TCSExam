本参考文档定义 TCSExam 的题目选择、agent 配置、预算和结果处理方式。
面向读完[入门指南](getting-started.zh-CN.md)、开始配置评测的研究者。

<a id="run-tcsexam-evaluations"></a>

# 运行配置与参数

语言：[English](running.md) | [简体中文](running.zh-CN.md)

[文档首页](index.zh-CN.md) · 首次运行：[从零运行 TCSExam](getting-started.zh-CN.md)

<a id="install-and-select"></a>

## 安装与选择

使用 Linux x86-64、Python 3.12+、带 Compose 和 Buildx 的 Docker Engine，
以及可以访问本地 Docker Unix socket 的用户。在执行主机上运行 CLI，以便 Docker
能够挂载相同的题目和任务输出路径。构建前检查主机：

```bash
docker info
docker compose version
docker buildx version
docker buildx inspect --bootstrap
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[runtime]'
tcsexam list --suite lite
```

runtime 依赖组安装 Harbor 0.22.0。Online Solver 的本地后端还需要 `backend`
依赖组。Solver 执行另有[主机与隔离要求](runtime-availability.zh-CN.md#host-and-task-resources)，
包括 Landlock ABI 3 或以上版本。评测前，应通过
[隔离预检查](judge-execution-isolation.zh-CN.md)检查实际判分镜像。

命令根据当前目录或源码位置查找工作副本。在其他位置工作时，使用
`--root /path/to/TCSExam` 或 `TCSEXAM_ROOT`。CLI 读取 shell 环境；按
[入门指南](getting-started.zh-CN.md#3-configure-the-model)说明显式加载 `.env`。

读法说明：按选择选项查看。`build`、`doctor`、`prepare` 和 `run` 应使用相同选择。

| 选项 | 含义与默认值 |
|---|---|
| `--suite lite\|full` | Full 包含 100 道题；Lite 从 Full 的各类题目中选取 20 道；默认 `lite` |
| `--track theorem\|solver\|construction\|open` | 选择一条题型；省略时选择全部题型 |
| `--task TASK_ID` | 在评测套件和题型内筛选；可重复使用，或用逗号分隔 ID |
| `--solver-protocol online\|offline` | Full 默认 `online`；Lite 默认 `offline` |

对于 `prepare` 和 `run`，还可设置 `--attempts N` 指定每道题的尝试次数，
用 `--concurrency N` 指定同时运行的题目尝试数。两者默认均为 1，且仅适用于
这两个命令。

题目筛选在所选评测套件内进行；仅属于 Full 的题目需使用 `--suite full`。
不同 Solver 协议选择不同题目包。其他题型在各种选择中共用题目目录。
各协议应在分别标注的任务中评测；[Solver 协议](solver-protocols.zh-CN.md)定义其反馈规则。

<a id="settings-and-budgets"></a>

## 设置与预算

读法说明：按阶段查看。所有 `timeout_sec` 值均以实际秒数计，Harbor 的超时倍率
为 **1**。各阶段预算相互独立。

| 阶段或设置 | 生效配置 |
|---|---|
| 启动前的镜像准备 | 单独的 `tcsexam build` 步骤 |
| 环境设置/构建 | 题目的 `environment.build_timeout_sec`；各题目包为 1,800–18,000 秒 |
| agent 安装 | Harbor 0.22.0 默认值：360 秒 |
| 模型开发 | 每次尝试 43,200 秒 |
| 最终验证 | 题目的 `verifier.timeout_sec`，Online 生命周期等待会按其 worker 计划调整 |
| 整道题的自动重试次数 | 0 |
| 收集的工作目录 | `/app` |

`discrete-bidding-games` 的环境设置时限为 3,600 秒，模型开发为 43,200 秒，
最终验证为 1,800 秒。其他 Lean 判分器允许 18,000 秒。Offline Solver 控制器的
生命周期时限为 345,600 或 1,209,600 秒；这些外层时限涵盖调度和判分，评分器则
执行各题自身的逐实例或共享时间池求解预算。各题限制请查看其 `task.toml` 和题面。
完整任务除开发外还包括安装和判分，因此可能超过十二小时。

Online 准备流程根据实例数、求解器预算和 worker 并发数计算轮询、会话生命周期
和判分器等待时间。本地后端计划使用主机的可用资源；外部后端必须提供选择记录中
`standard_client_timing` 所记载的标准 worker 和资源。实际判分器时限按尝试记录为
`effective_verifier_timeout_sec`。修改外层等待时间不会改变评分器的计算预算。

准备的题目副本允许所选 agent 安装程序访问其软件包来源。模型服务主机会加入
agent 的允许访问列表。除此之外，题目开发环境和判分器的网络策略保留声明的设置。
直接通过 Harbor 执行时也应使用准备好的副本，以确保安装过程具有预期的网络权限。

<a id="choose-an-agent"></a>

## 选择 agent

agent CLI 是模型用来编辑文件和运行工具的程序。通过 `--agent` 或
`TCSEXAM_AGENT` 选择。`--model` 覆盖 `TCSEXAM_MODEL`；只有 Kimi 设有默认模型。
`prepare`、`doctor` 和 `run` 应使用相同设置。

读法说明：按 agent 查看。服务地址必须实现该 CLI 使用的 API。

| agent | 模型与推理默认设置 | CLI 版本 | 服务 API |
|---|---|---|---|
| `kimi-code` | `kimi-k3`，推理强度 `max`，上下文 1,048,576 token | 0.43.0 | 兼容 Kimi 的服务接口 |
| `claude-code` | 显式指定模型；推理强度取自 Harbor 或配置的环境变量 | Harbor 复用/安装策略 | Anthropic Messages |
| `codex` | 显式指定模型，推理强度 `high` | Harbor 复用/安装策略 | OpenAI Responses |
| `grok-build` | 显式指定模型，推理强度 `high` | Harbor 复用/安装策略 | 所选的 Responses、Chat Completions 或 Messages 后端 |

使用 `--agent-version` 或 `TCSEXAM_AGENT_VERSION` 固定到准确的数字版本号。
未固定版本时，Harbor 会复用检测到的非 Kimi CLI，或安装其默认版本；报告结果时
应记录实际 CLI 版本。

<a id="credentials-and-endpoints"></a>

### 凭据与服务地址

`TCSEXAM_API_KEY` 的优先级高于所选 agent 的原生密钥。设置 `--base-url` 或
`TCSEXAM_API_BASE_URL` 可使用自定义地址；否则使用原生 base-URL 变量或服务默认值。
任务配置保存所选密钥变量的占位符，实际值保留在启动环境中。

读法说明：按 agent 查看。对应的通用覆盖项未设置时，原生变量生效。

| agent | 原生密钥变量，按优先级排列 | 原生 base-URL 变量 | 默认 base URL |
|---|---|---|---|
| Kimi Code | `KIMI_MODEL_API_KEY`、`KIMI_API_KEY`、`MOONSHOT_API_KEY` | `KIMI_MODEL_BASE_URL`、`KIMI_BASE_URL` | `https://api.kimi.com/coding/v1` |
| Claude Code | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` |
| Codex | `OPENAI_API_KEY` | `OPENAI_BASE_URL` | `https://api.openai.com/v1` |
| Grok Build，裸模型 ID 或 `xai/MODEL` | `XAI_API_KEY` | `XAI_BASE_URL` | `https://api.x.ai/v1` |

Grok 还接受 `openai/MODEL`、`anthropic/MODEL` 和 `openrouter/MODEL`。
它们分别使用 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY` 和 `OPENROUTER_API_KEY`，
对应 Responses、Messages 和 Chat Completions。原生 base-URL 变量分别为
`OPENAI_BASE_URL`、`ANTHROPIC_BASE_URL` 和 `OPENROUTER_BASE_URL`。
使用自定义 xAI 地址时，必须显式选择 `--grok-api-backend`。
Claude 接受裸模型 ID 或 `anthropic/MODEL`；Codex 接受裸 ID 或 `openai/MODEL`。
此接口使用 API 密钥认证。如果本地 CLI 通过 OAuth 或 Bedrock 配置，请改用
受支持的 API 密钥。

<a id="optional-agent-limits"></a>

### 可选的 agent 限制

读法说明：按选项查看。不支持的选项会导致配置错误。

| 选项 | 环境变量 | 适用范围 |
|---|---|---|
| `--reasoning-effort` | `TCSEXAM_REASONING_EFFORT` | 四种 agent，取值限于各 agent 支持的范围 |
| `--max-context-tokens` | `TCSEXAM_MAX_CONTEXT_TOKENS` | Kimi |
| `--max-output-tokens` | `TCSEXAM_MAX_OUTPUT_TOKENS` | Claude |
| `--max-turns` | `TCSEXAM_MAX_TURNS` | Claude 和 Grok |
| `--grok-api-backend` | `TCSEXAM_GROK_API_BACKEND` | Grok：`responses`、`chat_completions` 或 `messages` |

默认不增加输出 token 数或回合数上限。Claude 还读取 `CLAUDE_CODE_EFFORT_LEVEL`、
`CLAUDE_CODE_MAX_OUTPUT_TOKENS` 和 `CLAUDE_CODE_MAX_TURNS`；Grok 还读取
`GROK_BUILD_MAX_TURNS`。服务提供方必须支持所请求的设置。回合数和 token 数限制
可能使尝试在实际时长预算耗尽前结束。切换 agent 时应清除不兼容的设置。

`tcsexam run` 会将 Claude 的输出 token 上限同时传给任务配置和 Harbor 子进程。
直接启动已保存的任务配置时，应在该 shell 中将 `CLAUDE_CODE_MAX_OUTPUT_TOKENS`
设置为相同的请求值。

<a id="agent-examples"></a>

### agent 示例

先[构建单道题目](getting-started.zh-CN.md#4-build-and-check-one-task)。
从下面选择一组配置，替换占位值，然后使用通用的预览、检查和运行命令。
这些示例显式设置连接和模型选项，因此会覆盖之前 agent 的地址。
切换时，先清除可选设置，再应用选定配置：

```bash
unset TCSEXAM_AGENT_VERSION TCSEXAM_REASONING_EFFORT TCSEXAM_MAX_CONTEXT_TOKENS
unset TCSEXAM_MAX_OUTPUT_TOKENS TCSEXAM_MAX_TURNS TCSEXAM_GROK_API_BACKEND
unset CLAUDE_CODE_EFFORT_LEVEL CLAUDE_CODE_MAX_OUTPUT_TOKENS CLAUDE_CODE_MAX_TURNS
unset GROK_BUILD_MAX_TURNS
```

Kimi Code：

```bash
export TCSEXAM_AGENT=kimi-code
export TCSEXAM_API_KEY="YOUR_KIMI_API_KEY"
export TCSEXAM_API_BASE_URL="https://YOUR_KIMI_PROVIDER.example/v1"
export TCSEXAM_MODEL="kimi-k3"
```

Claude Code：

```bash
export TCSEXAM_AGENT=claude-code
export TCSEXAM_API_KEY="YOUR_CLAUDE_API_KEY"
export TCSEXAM_API_BASE_URL="https://YOUR_ANTHROPIC_PROVIDER.example"
export TCSEXAM_MODEL="YOUR_CLAUDE_MODEL_ID"
```

Codex：

```bash
export TCSEXAM_AGENT=codex
export TCSEXAM_API_KEY="YOUR_CODEX_API_KEY"
export TCSEXAM_API_BASE_URL="https://YOUR_RESPONSES_PROVIDER.example/v1"
export TCSEXAM_MODEL="YOUR_CODEX_MODEL_ID"
```

Grok Build，使用自定义 Responses 地址：

```bash
export TCSEXAM_AGENT=grok-build
export TCSEXAM_API_KEY="YOUR_GROK_API_KEY"
export TCSEXAM_API_BASE_URL="https://YOUR_GROK_PROVIDER.example/v1"
export TCSEXAM_MODEL="YOUR_GROK_MODEL_ID"
export TCSEXAM_GROK_API_BACKEND=responses
```

加载选定设置后：

```bash
tcsexam prepare --suite lite --task discrete-bidding-games \
  --output build/agent-job.json
python -m tcsexam.harbor_launch run --config build/agent-job.json --print-config
tcsexam doctor --suite lite --task discrete-bidding-games \
  --output build/agent-readiness.json
# Resolve blockers, then start model API usage:
tcsexam run --suite lite --task discrete-bidding-games \
  --attempts 1 --concurrency 1 --output build/agent-job.json
```

要使用原生服务地址，请清除 `TCSEXAM_API_BASE_URL` 和所选 agent 的原生 URL
覆盖变量。不要将凭据写入已提交的文件或公开日志。

<a id="check-prerequisites-and-run"></a>

## 检查前置条件并运行

读法说明：按命令查看。开始模型执行前应先构建并检查。

| 命令 | 作用 | 调用模型 |
|---|---|---|
| `list` | 显示所选题目路径 | 否 |
| `build` | 获取声明的输入、准备镜像并保存选择清单 | 否 |
| `setup` | 根据提供或缓存的清单拉取或核验完整镜像 | 否 |
| `prepare` | 准备题目副本，写入 Harbor 任务配置和选择记录 | 否 |
| `doctor` | 检查准备好的镜像、主机前置条件和后端设置 | 否 |
| `run` | 核验镜像、检查前置条件、写入新任务配置并启动 Harbor | 是 |

对于五道 Lite Offline Solver 题：

```bash
tcsexam build --suite lite --track solver --solver-protocol offline
tcsexam prepare --suite lite --track solver --solver-protocol offline \
  --output build/lite-solver.json
tcsexam doctor --suite lite --track solver --solver-protocol offline \
  --output build/lite-solver-readiness.json
# After resolving blockers and setting model credentials:
tcsexam run --suite lite --track solver --solver-protocol offline \
  --attempts 1 --concurrency 1 --output build/lite-solver.json
```

前置条件仍未满足时，`doctor` 以退出码 2 结束。查看其 `blockers`，修正所列的
镜像、资源、运行环境或后端设置。`agent_configuration` 在本地检查配置和凭据
是否存在，保留 `model_endpoint_contacted: false`。服务认证和模型可用性会在
运行期间 agent 连接服务时检查。

`prepare` 写入任务配置及相邻的 `*.selection.json`，记录源码版本、工作副本是否
有未提交修改、模型、协议和每次尝试的运行路径。题目副本放在源码题目树之外。
`run --output PATH` 会重新生成任务配置；要严格按已有文件执行，请使用：

```bash
python -m tcsexam.harbor_launch run --config build/lite-solver.json
```

使用与准备阶段相同的缓存、Docker context 和凭据。启动程序应用准备好的 Harbor
主机支持镜像。`run` 自动传递这些设置。使用具名本地 context 时，直接启动需设置
`DOCKER_CONTEXT=NAME`。Harbor 加载声明的主机环境变量前会询问；检查并确认，
或使用 `tcsexam run --yes` 显式批准无人值守运行。

<a id="inputs-images-and-cache"></a>

### 输入、镜像与缓存

`build` 复用本地产物、拉取可用的已发布镜像，并根据声明的配方构建缺少的产物。
本地构建不需要镜像仓库账户。默认 Solver 配方获取固定版本的官方输入，或使用
源码中包含的固定输入。各数据集要求见[资源准备](resources.zh-CN.md)，其中包括
MaxSAT 的官方归档重建方法。

默认缓存为 `~/.cache/tcsexam`。准备前将 `TCSEXAM_CACHE` 设为绝对路径，或在
各命令中重复指定 `--cache PATH`。Docker 镜像使用 Docker 自身的存储目录。
各命令应保持工作副本、题目选择、协议、缓存和 Docker 目标一致。
`prepare`、`doctor` 和 `run` 复用该选择最近一次成功 `build` 的结果。

`build --output PATH` 保存镜像清单；`prepare/run --output PATH` 指定 Harbor
任务配置文件。使用 `--artifacts PATH` 显式选择已保存的镜像清单。
`--image-map PATH` 用固定的已发布镜像引用覆盖题目镜像角色。
`--docker-context NAME` 选择本地 Unix-socket Docker context。
外部清单格式见[资源准备](resources.zh-CN.md#use-an-external-image-manifest)。

## Online Solver

Online Solver 需要在模型执行前启动后端。按照
[Docker 后端指南](backend/docker.zh-CN.md)准备服务地址、host-gateway 路由、磁盘配额
支持和凭据。这些凭据与模型服务凭据分开设置：

```bash
export TCSEXAM_BASE_URL="http://host.docker.internal:8420"
: "${TCSEXAM_TOKEN_ID:?Set the service identity}"
: "${TCSEXAM_TOKEN_SECRET:?Set the service secret}"
: "${TCSEXAM_ARCHIVE_TOKEN:?Set the verifier-only secret}"
```

开发容器和判分容器必须能够访问该服务地址。`--judge-url` 可覆盖该地址。
`TCSEXAM_ARCHIVE_TOKEN` 只注入判分器，保存的任务配置中保留其占位符。
隐藏数据和这项凭据应放在开发环境之外。准备流程为每次尝试分配唯一的
`TCSEXAM_RUN_ID`，供开发阶段和最终判分共用；直接使用 Harbor 时，用户必须
自行提供唯一 ID。`TCSEXAM_AGENT_NAME` 是可选元数据。准备好的镜像分配提供
`TCSEXAM_JUDGE_IMAGE`。

对于一道 Online 题目：

```bash
python -m pip install -e '.[runtime,backend]'
tcsexam build --suite full --track solver --task bpp-bpplib --solver-protocol online
tcsexam backend configure --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --judge-url "$TCSEXAM_BASE_URL" \
  --config build/backend.yaml
tcsexam backend check --config build/backend.yaml
tcsexam backend serve --config build/backend.yaml
```

`configure` 写入服务配置及相邻的 `backend.plan.json`。计划根据主机实际资源
安排 worker，同时保留每个实例的计算资源和求解时间，并将共享时间池保留在一起。
生成的服务允许一个会话，其启动计划一次允许一个 trial。
保持 `serve` 在该终端中运行。在同一主机上的另一个终端中，激活环境并加载相同的
凭据、缓存和模型设置：

```bash
tcsexam doctor --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json \
  --output build/bpp-readiness.json
tcsexam run --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json \
  --output build/bpp-online.json
```

运行前解决报告中的问题。更改所选镜像或主机资源后，应重新生成计划。
`TCSEXAM_BACKEND_PLAN` 是 `--backend-plan` 对应的环境变量。
外部服务应使用相同的 [HTTP 接口](solver-backend.zh-CN.md)，并提供所需容量；
平台适配器见[服务指南](backend/service.zh-CN.md#writing-a-platform-adapter)。

<a id="keep-outputs-and-statuses"></a>

## 保存输出与状态

生成的任务配置中，`jobs_dir` 和 `job_name` 确定输出目录。
例如，运行 `build/first-job.json` 后：

```bash
python - <<'PY'
import json
from pathlib import Path
config = json.loads(Path('build/first-job.json').read_text())
job = Path(config['jobs_dir']) / config['job_name']
print('Job directory:', job)
for result in sorted(job.rglob('result.json')):
    print('\n' + str(result))
    print(result.read_text())
for reward in sorted(job.rglob('reward.*')):
    print('\n' + str(reward))
    print(reward.read_text())
PY
```

任务输出包括汇总的 `result.json`，以及每次尝试的目录，其中包含 `result.json`、
`agent/`、`verifier/` 和 `artifacts/`。查看奖励时同时检查异常、判分器日志和题目
详细报告。产物收集清单给出已保存的 `/app` 工作文件的准确路径。

已完成判分并得到零分是有效零分。启动错误、判分器崩溃或结果缺失应保留为执行
失败或结果缺失。判分状态和模型运行中断状态分别保存，包括提交已通过核验、
但模型运行发生中断的情况。归档实验时，复制整个任务输出目录、任务配置、选择
记录以及所有运行环境/后端计划。替换输出前先保存早先的尝试。

按[评分指南](scoring.zh-CN.md)转换 Solver 最终逐实例记录，并整理采纳的尝试表。
`tcsexam score` 使用该表和声明的实验组；它不会重试题目，也不会自动选择最佳尝试。

<a id="development-and-source-export"></a>

## 开发与源码导出

源码导出、完整测试套件和文档检查见 [CONTRIBUTING.md](../.github/CONTRIBUTING.zh-CN.md)。
[源码包](source-delivery.zh-CN.md)列出分发组件。
