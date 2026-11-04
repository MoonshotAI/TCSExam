Run one theorem-proving task and inspect its result.
For first-time users with a Linux host and model API access.

<a id="run-tcsexam-from-scratch"></a>

# Quickstart

Language: [English](getting-started.md) | [简体中文](getting-started.zh-CN.md)

[Documentation home](index.md) · Parameter lookup: [Run configuration and parameters](running.md)

Use Bash for the commands below and replace `YOUR_...` placeholders. You provide
a Docker host and model API access. The agent runs the model's tools inside a
task container; a separate verifier checks the submission. This guide uses Kimi
Code. For Claude Code, Codex or Grok Build, use the
[agent examples](running.md#agent-examples) at step 3, then follow the same path.
A host using a remote model API generally needs no GPU.

## 1. Prepare the host

Use Linux x86-64, Python 3.12+, Docker Engine, Compose and Buildx. On Ubuntu
24.04, install the basic packages:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates nano python3 python3-venv python3-pip libarchive13t64
python3 --version
uname -m
```

Confirm Python is at least 3.12 and the architecture is `x86_64`.
`libarchive13t64` provides RAR support for the BPPLIB dataset used later in Lite;
other distributions may call the package `libarchive13`.

Install Docker Engine and its Compose/Buildx plugins using the
[Docker Ubuntu guide](https://docs.docker.com/engine/install/ubuntu/).
Grant the evaluation user appropriate Docker access and verify:

```bash
docker info
docker compose version
docker buildx version
docker buildx inspect --bootstrap
```

If Docker reports permission denied, check the user's socket permissions; after
a Docker group change, log in again. The Docker group has extensive host access.
Run subsequent commands on this host. For long SSH sessions, use a session
manager such as `tmux`.

The first task requests 4 CPU cores and 16 GiB memory. A host with 8 cores and
32 GiB leaves room for the operating system and preparation. Reserve at least
40 GB of disk for the shared Lean environment, plus downloads, build space and
results. Solver tasks require additional resources and enabled Landlock ABI 3
or later; check [runtime requirements](runtime-availability.md) before Lite or
Full. If a host cannot fit one full-size judging worker, use a larger host.

## 2. Clone and install

Clone the repository and install the runtime dependencies:

```bash
git clone https://github.com/MoonshotAI/TCSExam.git TCSExam
cd TCSExam
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[runtime,backend]'
tcsexam --help
tcsexam validate
```

The extras install Harbor 0.22.0 and the backend dependencies used for Full
Online later. `validate` checks the source task configuration. Continue from
the checkout root. In a new terminal, enter this directory and activate `.venv`.

## 3. Configure the model

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Set these lines to your provider's values, retaining quotes:

```bash
TCSEXAM_AGENT="kimi-code"
TCSEXAM_API_BASE_URL="https://YOUR_PROVIDER.example/v1"
TCSEXAM_MODEL="YOUR_MODEL_ID"
TCSEXAM_API_KEY="YOUR_API_KEY"
```

Use the provider's API endpoint and exact model ID. Kimi Code is the default
agent; its provider must support the requested API and settings. For another
agent, follow [agent configuration](running.md#choose-an-agent), including its
endpoint, model and optional settings, before continuing.

Load the file explicitly in every terminal used to launch a job:

```bash
set -a
source .env
set +a
```

The CLI does not load `.env` automatically. It is ignored by Git; keep real
keys out of public logs and Issues. Model API usage starts at `tcsexam run`.
Build and configuration-preview commands need no model key.

If your downloads need another disk, set an absolute writable `TCSEXAM_CACHE`
path in `.env`, then load it again. This moves the preparation cache. Docker
layers remain in Docker's storage directory; check both locations:

```bash
docker info --format '{{.DockerRootDir}}'
df -h
```

## 4. Build and check one task

Start with `discrete-bidding-games`, a theorem-proving task included in Lite:

```bash
tcsexam list --suite lite
tcsexam source-inputs
tcsexam build --suite lite --task discrete-bidding-games
tcsexam doctor --suite lite --task discrete-bidding-games \
  --output build/first-readiness.json
```

`source-inputs` acquires and verifies fixed Lean build archives. `build`
prepares the development and verifier images and saves their records. Later
commands reuse prepared products for the same selection and cache.

Open `build/first-readiness.json` and resolve any `blockers`. For a failed
download or checksum, use [resource preparation](resources.md); it provides
exact-file import commands when an upstream download is blocked. For image or
host errors, use [troubleshooting](#troubleshooting). The readiness report checks
local configuration; the model endpoint is contacted when the agent runs.

Preview the job without starting a model:

```bash
tcsexam prepare --suite lite --task discrete-bidding-games \
  --output build/first-job.json
python -m tcsexam.harbor_launch run \
  --config build/first-job.json --print-config
```

This writes `build/first-job.json` and `build/first-job.selection.json` and stages
runtime task copies with the prepared image references. Leave the source
`task.toml` files unchanged. Check the selected model and task before running.

## 5. Run the task

```bash
tcsexam run --suite lite --task discrete-bidding-games \
  --attempts 1 --concurrency 1 --output build/first-job.json
```

This starts model API usage. Review and confirm Harbor's request to load declared
host environment variables. `run` checks prerequisites and regenerates the job
before launching one attempt of the selected task.

The attempt allows 12 hours (43,200 seconds) of model development, with timeout multiplier `1`. Installation, environment preparation and verification have separate limits;
see [stage budgets](running.md#settings-and-budgets). The model can finish early.

If the provider returns an authentication or model error, check the key,
endpoint, model ID and selected agent API. Use the result inspection below to
retain the failed attempt's logs before starting a new one.

## 6. Read the actual result

Locate the job from the generated configuration and print its attempt results:

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

Each attempt directory contains its `result.json`, `agent/` logs, `verifier/`
outputs and `artifacts/`. Open the verifier logs and detailed task report to
understand the score. Artifact collection manifests locate the saved `/app`
work products. [Result handling](running.md#keep-outputs-and-statuses) gives the
full output layout and inspection commands.

A completed judgement can legitimately earn zero. A startup error, verifier
crash or missing judgement needs investigation. Keep that state separate from
a valid zero. Preserve the entire job directory together with the job and
selection JSON files before updating or replacing an attempt.

## Next: Lite or Full

<a id="7-run-all-20-lite-tasks"></a>
<a id="8-run-full"></a>
<a id="9-calculate-suite-scores"></a>

- [Run the 20-task Lite suite](running-suites.md#run-all-20-lite-tasks).
- [Run the 100-task Full suite](running-suites.md#run-full).
- [Calculate track scores and the Index](scoring.md).

## Troubleshooting

Read the table by symptom. After correcting a preparation error, reuse the
verified cache with the same selection.

| Symptom | Action |
|---|---|
| Docker permission denied | Check socket access and log in again after group changes |
| Docker or cache disk is full | Check both storage locations; move the cache or provision Docker storage as needed |
| Download or checksum failure | Use the pinned-source and exact-file import instructions in [resources](resources.md) |
| Images missing or stale | Repeat `build` for the same task selection, protocol, cache and Docker target |
| `doctor` reports blockers | Read the named image, host, resource or backend requirement and correct it before `run` |
| Landlock preflight fails | Check kernel support and container syscall policy on the execution host |
| Online service is unreachable | Check `serve`, host-gateway routing, credentials in both terminals and the selected backend plan |
| Provider returns 401 or unknown model | Check key, endpoint, model ID and agent API compatibility |
| Score is zero or missing | Inspect the attempt exception and verifier output before assigning a result state |

## Switch agents

Use the [four agent examples](running.md#agent-examples), then repeat the
prepare/check/run commands with a new output filename. Reload the chosen
settings in each launch terminal. [Run configuration and parameters](running.md)
also lists agent-specific limits and the settings to clear when switching.
