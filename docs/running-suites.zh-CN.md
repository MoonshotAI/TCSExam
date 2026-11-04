这份指南介绍运行 Lite 和 Full 全部题目的命令。
面向已完成首次单题运行的评测使用者。

<a id="run-lite-or-full"></a>

# 运行 Lite 或 Full

[English](running-suites.md) | [简体中文](running-suites.zh-CN.md)

沿用[快速开始](getting-started.zh-CN.md)中的仓库和终端，激活 `.venv` 并加载 `.env`。运行整套评测前，先检查[主机要求](runtime-availability.zh-CN.md)。

<a id="7-run-all-20-lite-tasks"></a>
<a id="run-all-20-lite-tasks"></a>

## 运行全部 20 道 Lite 题

沿用已加载的模型配置。Lite 默认使用 Offline Solver，下面显式写出协议：

```bash
tcsexam build --suite lite --solver-protocol offline
tcsexam doctor --suite lite --solver-protocol offline \
  --output build/lite-readiness.json
tcsexam prepare --suite lite --solver-protocol offline \
  --attempts 1 --concurrency 1 --output build/lite-job.json
python -m tcsexam.harbor_launch run --config build/lite-job.json --print-config
```

处理检查报告中的问题，审阅任务配置后运行：

```bash
tcsexam run --suite lite --solver-protocol offline \
  --attempts 1 --concurrency 1 --output build/lite-job.json
```

将[查看结果的步骤](getting-started.zh-CN.md#6-read-the-actual-result)的配置路径改为 `build/lite-job.json`，即可查看结果。Offline Solver
使用 Docker 控制器，无需常驻判分服务。题目并发数与 Solver 判分中的实例并行数
分别控制；只有主机和模型服务有足够容量时才增加题目并发。20 次串行尝试，每次
最多开发 12 小时，再加上判分，可能需要数天。

<a id="8-run-full"></a>
<a id="run-full"></a>

## 运行 Full

Full 包含 100 道题，默认使用 Online Solver，在模型开发期间提供提交反馈，
需要后端判分服务。在同一台 Docker 主机上运行时，先检查
[Docker 后端的主机要求](backend/docker.zh-CN.md#host-requirements)，确认网络路由和
磁盘配额条件，然后构建：

```bash
tcsexam build --suite full --solver-protocol online \
  --output build/full-online-images.json
```

首次运行时创建服务凭据。命令拒绝覆盖已有的 `.env.backend`；后续运行复用该文件：

```bash
python - <<'PY'
from pathlib import Path
import secrets
p = Path('.env.backend')
with p.open('x') as f:
    p.chmod(0o600)
    f.write('TCSEXAM_BASE_URL=http://host.docker.internal:8420\n')
    f.write('TCSEXAM_TOKEN_ID=local-evaluation\n')
    f.write('TCSEXAM_TOKEN_SECRET=' + secrets.token_hex(32) + '\n')
    f.write('TCSEXAM_ARCHIVE_TOKEN=' + secrets.token_hex(32) + '\n')
PY
set -a
source .env.backend
set +a
tcsexam backend configure --suite full --solver-protocol online \
  --artifacts build/full-online-images.json \
  --judge-url "$TCSEXAM_BASE_URL" --config build/full-backend.yaml
tcsexam backend check --config build/full-backend.yaml
tcsexam backend serve --config build/full-backend.yaml
```

该地址使用 Linux Docker 的 host-gateway 路由，开发容器和判分容器都需要能访问。
其他网络部署方式见后端指南。归档凭据仅供判分使用。`configure` 生成
`build/full-backend.yaml` 和 `build/full-backend.plan.json`。

保持 `serve` 运行。在同一台主机上打开第二个终端，进入仓库目录后执行：

```bash
source .venv/bin/activate
set -a
source .env
source .env.backend
set +a
tcsexam doctor --suite full --solver-protocol online \
  --artifacts build/full-online-images.json \
  --backend-plan build/full-backend.plan.json \
  --output build/full-readiness.json
tcsexam prepare --suite full --solver-protocol online \
  --artifacts build/full-online-images.json \
  --backend-plan build/full-backend.plan.json \
  --attempts 1 --concurrency 1 --output build/full-job.json
python -m tcsexam.harbor_launch run --config build/full-job.json --print-config
```

处理检查报告中的问题，审阅任务配置后运行：

```bash
tcsexam run --suite full --solver-protocol online \
  --artifacts build/full-online-images.json \
  --backend-plan build/full-backend.plan.json \
  --attempts 1 --concurrency 1 --output build/full-job.json
```

将[查看结果的步骤](getting-started.zh-CN.md#6-read-the-actual-result)的配置路径改为 `build/full-job.json`，即可检查结果。生成的本地后端计划
一次运行一道题，根据主机资源安排实例 worker。网络、服务或资源错误见
[Online Solver 配置](running.zh-CN.md#online-solver)。

如果要运行 Full 的 Offline Solver 版本，用下面的流程替代后端服务步骤，并将
结果标为 **Full Offline**：

```bash
tcsexam build --suite full --solver-protocol offline
tcsexam doctor --suite full --solver-protocol offline \
  --output build/full-offline-readiness.json
# Resolve blockers before launching:
tcsexam run --suite full --solver-protocol offline \
  --attempts 1 --concurrency 1 --output build/full-offline-job.json
```

<a id="9-calculate-suite-scores"></a>
<a id="calculate-suite-scores"></a>

## 计算整套评测的分数

使用最终核验的结果，按照[评分指南](scoring.zh-CN.md)整理采纳的尝试记录和实验组配置。
其中提供 `tcsexam solver-score` 和 `tcsexam score` 的完整命令。Solver 需要将
最终逐实例记录与固定参考成绩比较，再将得到的相对分数填入尝试表。
Harbor 的任务奖励汇总和 TCSExam Index 用途不同。

包含全部选中题目及计划的尝试次数，保留判分失败或缺失的状态，并注明评测套件和
Solver 协议。评分输出包含四条题型的分数、覆盖情况和 Index；输入不完整时
Index 为 null。与结果一起保存模型配置、源码版本、镜像记录和后端计划。

