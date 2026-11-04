This reference defines task selection, agent configuration, budgets and result handling in TCSExam.
It is for researchers configuring an evaluation after the [getting-started guide](getting-started.md).

<a id="run-tcsexam-evaluations"></a>

# Run configuration and parameters

Language: [English](running.md) | [简体中文](running.zh-CN.md)

[Documentation home](index.md) · First run: [Run TCSExam from scratch](getting-started.md)

## Install and select

Use Linux x86-64, Python 3.12+, Docker Engine with Compose and Buildx, and a user
that can access the local Docker Unix socket. Run the CLI on the execution host
so Docker can bind the same task and job paths. Check the host before building:

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

The runtime extra installs Harbor 0.22.0. Online Solver's local backend also
needs the `backend` extra. Solver execution has additional
[host and isolation requirements](runtime-availability.md#host-and-task-resources),
including Landlock ABI 3 or later. Check the actual judge image with the
[isolation preflight](judge-execution-isolation.md) before an evaluation.

Commands find the checkout from the current directory or source location. Use
`--root /path/to/TCSExam` or `TCSEXAM_ROOT` when working elsewhere. The CLI
reads the shell environment; load `.env` explicitly as shown in
[getting started](getting-started.md#3-configure-the-model).

Read the table by selector. Use the same selection for `build`, `doctor`,
`prepare` and `run`.

| Option | Meaning and default |
|---|---|
| `--suite lite\|full` | Full contains 100 tasks; Lite selects 20 from across Full's task categories; default `lite` |
| `--track theorem\|solver\|construction\|open` | Select one track; omitted selects all tracks |
| `--task TASK_ID` | Filter the suite and track; repeat or use comma-separated IDs |
| `--solver-protocol online\|offline` | Full defaults to `online`; Lite defaults to `offline` |

For `prepare` and `run`, also set `--attempts N` for the number of attempts per
task and `--concurrency N` for the number of concurrent task attempts. Both
default to 1 and apply only to these two commands.

A task filter selects from the chosen suite; use `--suite full` for a Full-only
task. Solver protocols select separate task packages. The other tracks share
their task folders across selections. Evaluate protocols in separately labeled
jobs; [Solver protocols](solver-protocols.md) defines their feedback rules.

## Settings and budgets

Read the table by phase. All `timeout_sec` values use real seconds and Harbor's
timeout multiplier is **1**. Phase budgets are independent.

| Phase or setting | Effective configuration |
|---|---|
| Image preparation before launch | Separate `tcsexam build` step |
| Environment setup/build | Task's `environment.build_timeout_sec`; 1,800–18,000 seconds across the task packages |
| Agent installation | Harbor 0.22.0 default: 360 seconds |
| Model development | 43,200 seconds per attempt |
| Final verification | Task's `verifier.timeout_sec`, with Online lifecycle waits adjusted for its worker plan |
| Whole-task automatic retries | 0 |
| Collected workspace | `/app` |

For `discrete-bidding-games`, environment setup is 3,600 seconds, model
development is 43,200 seconds, and final verification is 1,800 seconds. Other
Lean verifiers allow 18,000 seconds. Offline Solver controllers allow 345,600 or
1,209,600 seconds for their lifecycle; these outer limits cover scheduling and
judging, while the scorer enforces each task's own per-instance or shared-pool
solver budget. Read each task's `task.toml` and instruction for its limits.
The complete job includes installation and judging in addition to development
and may take longer than twelve hours.

Online preparation derives polling, session lifetime and verifier waits from
the instance count, solver budget and worker concurrency. A local backend plan
uses the host's available capacity; an external backend must supply the standard
workers and resources recorded under `standard_client_timing` in the selection
record. The effective verifier limit is recorded per attempt as
`effective_verifier_timeout_sec`. Changing outer waits leaves the scorer's
computation budget unchanged.

Prepared task copies allow the selected agent installer to reach its package
sources. The provider host is added to the agent's allowlist. Task development
and verifier network policies otherwise retain their declared settings. Use
prepared copies for direct Harbor execution so installation has the intended
network access.

## Choose an agent

An agent CLI is the program through which the model edits files and runs tools.
Select it with `--agent` or `TCSEXAM_AGENT`. `--model` overrides
`TCSEXAM_MODEL`; only Kimi has a default model. Use the same settings for
`prepare`, `doctor` and `run`.

Read the table by agent. The endpoint must implement the API used by that CLI.

| Agent | Model and reasoning defaults | CLI version | Provider API |
|---|---|---|---|
| `kimi-code` | `kimi-k3`, effort `max`, context 1,048,576 tokens | 0.43.0 | Kimi-compatible endpoint |
| `claude-code` | Explicit model; effort from Harbor or configured environment | Harbor reuse/install policy | Anthropic Messages |
| `codex` | Explicit model, effort `high` | Harbor reuse/install policy | OpenAI Responses |
| `grok-build` | Explicit model, effort `high` | Harbor reuse/install policy | Selected Responses, Chat Completions or Messages backend |

Use `--agent-version` or `TCSEXAM_AGENT_VERSION` for an exact numeric version
pin. Without a pin, Harbor reuses a detected non-Kimi CLI or installs its default;
record the actual CLI version when reporting results.

### Credentials and endpoints

`TCSEXAM_API_KEY` takes priority over the selected agent's native key. Set
`--base-url` or `TCSEXAM_API_BASE_URL` to use a custom endpoint; otherwise the
native base-URL variable or provider default applies. Jobs contain the selected
key variable's placeholder, keeping its value in the launch environment.

Read the table by agent. Native variables apply when the corresponding common
override is unset.

| Agent | Native key variables, in priority order | Native base-URL variables | Default base URL |
|---|---|---|---|
| Kimi Code | `KIMI_MODEL_API_KEY`, `KIMI_API_KEY`, `MOONSHOT_API_KEY` | `KIMI_MODEL_BASE_URL`, `KIMI_BASE_URL` | `https://api.kimi.com/coding/v1` |
| Claude Code | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` |
| Codex | `OPENAI_API_KEY` | `OPENAI_BASE_URL` | `https://api.openai.com/v1` |
| Grok Build, bare model or `xai/MODEL` | `XAI_API_KEY` | `XAI_BASE_URL` | `https://api.x.ai/v1` |

Grok also accepts `openai/MODEL`, `anthropic/MODEL` and `openrouter/MODEL`.
They use `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `OPENROUTER_API_KEY`, with
Responses, Messages and Chat Completions respectively. Their native base-URL
variables are `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` and `OPENROUTER_BASE_URL`.
A custom xAI endpoint requires an explicit `--grok-api-backend` choice.
Claude accepts a bare model ID or `anthropic/MODEL`; Codex accepts a bare ID or
`openai/MODEL`. This interface uses API-key authentication. Use a supported API
key when a local CLI is otherwise configured through OAuth or Bedrock.

### Optional agent limits

Read the table by option. Unsupported options produce a configuration error.

| Option | Environment variable | Applies to |
|---|---|---|
| `--reasoning-effort` | `TCSEXAM_REASONING_EFFORT` | All four agents, within each agent's supported values |
| `--max-context-tokens` | `TCSEXAM_MAX_CONTEXT_TOKENS` | Kimi |
| `--max-output-tokens` | `TCSEXAM_MAX_OUTPUT_TOKENS` | Claude |
| `--max-turns` | `TCSEXAM_MAX_TURNS` | Claude and Grok |
| `--grok-api-backend` | `TCSEXAM_GROK_API_BACKEND` | Grok: `responses`, `chat_completions`, or `messages` |

No output-token or turn cap is added by default. Claude also reads
`CLAUDE_CODE_EFFORT_LEVEL`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS` and
`CLAUDE_CODE_MAX_TURNS`; Grok also reads `GROK_BUILD_MAX_TURNS`. A provider must
support the requested settings. Turn and token caps can end an attempt before
its wall-clock budget. Clear incompatible settings when switching agents.

`tcsexam run` forwards Claude's output-token limit to both the job and the Harbor
subprocess. When launching a saved job directly, set
`CLAUDE_CODE_MAX_OUTPUT_TOKENS` in that shell to the same requested value.

### Agent examples

First [build the single task](getting-started.md#4-build-and-check-one-task).
Choose one block below, replace its placeholders and then use the common
preview/check/run commands. These examples set connection and model choices
explicitly so a previous agent's endpoint is overridden. When switching, clear
optional settings before applying the chosen block:

```bash
unset TCSEXAM_AGENT_VERSION TCSEXAM_REASONING_EFFORT TCSEXAM_MAX_CONTEXT_TOKENS
unset TCSEXAM_MAX_OUTPUT_TOKENS TCSEXAM_MAX_TURNS TCSEXAM_GROK_API_BACKEND
unset CLAUDE_CODE_EFFORT_LEVEL CLAUDE_CODE_MAX_OUTPUT_TOKENS CLAUDE_CODE_MAX_TURNS
unset GROK_BUILD_MAX_TURNS
```

Kimi Code:

```bash
export TCSEXAM_AGENT=kimi-code
export TCSEXAM_API_KEY="YOUR_KIMI_API_KEY"
export TCSEXAM_API_BASE_URL="https://YOUR_KIMI_PROVIDER.example/v1"
export TCSEXAM_MODEL="kimi-k3"
```

Claude Code:

```bash
export TCSEXAM_AGENT=claude-code
export TCSEXAM_API_KEY="YOUR_CLAUDE_API_KEY"
export TCSEXAM_API_BASE_URL="https://YOUR_ANTHROPIC_PROVIDER.example"
export TCSEXAM_MODEL="YOUR_CLAUDE_MODEL_ID"
```

Codex:

```bash
export TCSEXAM_AGENT=codex
export TCSEXAM_API_KEY="YOUR_CODEX_API_KEY"
export TCSEXAM_API_BASE_URL="https://YOUR_RESPONSES_PROVIDER.example/v1"
export TCSEXAM_MODEL="YOUR_CODEX_MODEL_ID"
```

Grok Build, using a custom Responses endpoint:

```bash
export TCSEXAM_AGENT=grok-build
export TCSEXAM_API_KEY="YOUR_GROK_API_KEY"
export TCSEXAM_API_BASE_URL="https://YOUR_GROK_PROVIDER.example/v1"
export TCSEXAM_MODEL="YOUR_GROK_MODEL_ID"
export TCSEXAM_GROK_API_BACKEND=responses
```

With the chosen settings loaded:

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

To use the native endpoint instead, clear `TCSEXAM_API_BASE_URL` and the selected
agent's native URL overrides. Keep credentials out of committed files and public
logs.

## Check prerequisites and run

Read the table by command. Build and inspect before starting model execution.

| Command | Effect | Calls the model |
|---|---|---|
| `list` | Show selected task paths | No |
| `build` | Acquire declared inputs, prepare images and save a selection manifest | No |
| `setup` | Pull or verify complete images from a supplied/cached manifest | No |
| `prepare` | Stage task copies and write a Harbor job and selection record | No |
| `doctor` | Check prepared images, host prerequisites and backend settings | No |
| `run` | Verify images, check prerequisites, write a new job and launch Harbor | Yes |

For the five Lite Offline Solver tasks:

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

`doctor` exits with code 2 when prerequisites remain unmet. Inspect its
`blockers` and correct the listed image, resource, runtime or backend setting.
Its `agent_configuration` checks configuration and credential presence locally;
it leaves `model_endpoint_contacted: false`. Provider authentication and model
availability are checked when the agent connects during a run.

`prepare` writes a job and adjacent `*.selection.json`, recording the source
revision, dirty state, model, protocol and per-attempt runtime paths. It stages
tasks outside the source task tree. `run --output PATH` regenerates that job;
to execute an existing file exactly, use:

```bash
python -m tcsexam.harbor_launch run --config build/lite-solver.json
```

Use the same cache, Docker context and credentials as preparation. The launcher
applies the prepared Harbor host-support images. `run` passes these settings
automatically. With a named local context, set `DOCKER_CONTEXT=NAME` for direct
launches. Harbor asks before loading declared host environment variables;
review and confirm them, or use `tcsexam run --yes` for explicit unattended
approval.

### Inputs, images and cache

`build` reuses local products, pulls available published images and builds
missing products from declared recipes. Local builds need no registry account.
The default Solver recipes acquire pinned official inputs or use fixed inputs
included in source. See [resource preparation](resources.md) for dataset-specific
requirements, including MaxSAT's official-archive reconstruction.

The default cache is `~/.cache/tcsexam`. Set `TCSEXAM_CACHE` to an absolute path
before preparation or repeat `--cache PATH`. Docker images use Docker's own
storage directory. Keep the checkout, selection, protocol, cache and Docker
target consistent across commands. The latest successful `build` for that
selection is reused by `prepare`, `doctor` and `run`.

`build --output PATH` saves an image manifest; `prepare/run --output PATH` names
a Harbor job. Use `--artifacts PATH` to select a saved image manifest explicitly.
`--image-map PATH` overrides task image roles with fixed published references.
`--docker-context NAME` selects a local Unix-socket Docker context. External
manifest formats are in [resource preparation](resources.md#use-an-external-image-manifest).

## Online Solver

Online Solver needs a running backend before model execution. Follow the
[Docker backend guide](backend/docker.md) to prepare the service address,
host-gateway routing, quota support and credentials. Set these separately from
model-provider credentials:

```bash
export TCSEXAM_BASE_URL="http://host.docker.internal:8420"
: "${TCSEXAM_TOKEN_ID:?Set the service identity}"
: "${TCSEXAM_TOKEN_SECRET:?Set the service secret}"
: "${TCSEXAM_ARCHIVE_TOKEN:?Set the verifier-only secret}"
```

The service address must be reachable from development and judge containers.
`--judge-url` overrides it. `TCSEXAM_ARCHIVE_TOKEN` is injected only into the
verifier, and saved jobs retain its placeholder. Keep hidden data and this
credential outside the development environment. Each prepared attempt gets a
unique `TCSEXAM_RUN_ID` shared by development and final judging; direct Harbor
users must provide a unique ID themselves. `TCSEXAM_AGENT_NAME` is optional
metadata. Prepared image assignments supply `TCSEXAM_JUDGE_IMAGE`.

For one Online task:

```bash
python -m pip install -e '.[runtime,backend]'
tcsexam build --suite full --track solver --task bpp-bpplib --solver-protocol online
tcsexam backend configure --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --judge-url "$TCSEXAM_BASE_URL" \
  --config build/backend.yaml
tcsexam backend check --config build/backend.yaml
tcsexam backend serve --config build/backend.yaml
```

`configure` writes the service configuration and adjacent `backend.plan.json`.
The plan fits workers to effective host resources while retaining each instance's
compute and solver time. It keeps shared time pools together. The generated
service admits one session and its launch plan allows one trial at a time.
Leave `serve` running in that terminal. In another terminal on the same host,
activate the environment and load the same credentials, cache and model settings:

```bash
tcsexam doctor --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json \
  --output build/bpp-readiness.json
tcsexam run --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json \
  --output build/bpp-online.json
```

Resolve blockers before running. Regenerate the plan after changing selected
images or host resources. `TCSEXAM_BACKEND_PLAN` is the environment-variable
alternative to `--backend-plan`. For an external service, use the same
[HTTP interface](solver-backend.md) and supply its required capacity; platform
adapters are described in [the service guide](backend/service.md#writing-a-platform-adapter).

## Keep outputs and statuses

The generated job's `jobs_dir` and `job_name` identify its output directory.
For example, after running `build/first-job.json`:

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

The job contains an aggregate `result.json` and per-attempt directories with
`result.json`, `agent/`, `verifier/` and `artifacts/`. Inspect exceptions,
verifier logs and detailed task reports alongside rewards. Artifact collection
manifests identify the exact paths of the saved `/app` work products.

A completed judgement that earned zero is a valid zero. A startup error,
verifier crash or missing result remains an execution failure or missing result.
Preserve judge status and model-interruption status separately, including when a
verified submission survives an interrupted model run. Copy the entire job
directory, job configuration, selection record and any runtime/backend plan
when archiving an experiment. Save earlier attempts before replacing outputs.

Use [scoring](scoring.md) to convert final Solver instance records and assemble
the adopted-attempt table. `tcsexam score` uses that table and a declared cohort;
it neither retries tasks nor selects the best attempt automatically.

## Development and source export

Use [CONTRIBUTING.md](../.github/CONTRIBUTING.md) for source export, the complete test
suite and documentation checks.
[Source packages](source-delivery.md) lists the shipped components.
