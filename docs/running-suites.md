Commands for running the complete Lite and Full task suites.
For users who have completed their first task.

# Run Lite or Full

[English](running-suites.md) | [简体中文](running-suites.zh-CN.md)

Continue in the checkout and shell used for [Quickstart](getting-started.md), with `.venv` active and `.env` loaded. Check [host requirements](runtime-availability.md) before running a suite.

<a id="7-run-all-20-lite-tasks"></a>

## Run all 20 Lite tasks

Use the same loaded model settings. Lite defaults to Offline Solver; specifying
it below makes the protocol explicit:

```bash
tcsexam build --suite lite --solver-protocol offline
tcsexam doctor --suite lite --solver-protocol offline \
  --output build/lite-readiness.json
tcsexam prepare --suite lite --solver-protocol offline \
  --attempts 1 --concurrency 1 --output build/lite-job.json
python -m tcsexam.harbor_launch run --config build/lite-job.json --print-config
```

Resolve the readiness report's blockers and review the job, then launch:

```bash
tcsexam run --suite lite --solver-protocol offline \
  --attempts 1 --concurrency 1 --output build/lite-job.json
```

Read results using [the result inspection steps](getting-started.md#6-read-the-actual-result) with `build/lite-job.json`. Offline Solver uses its
Docker controller and needs no persistent judging service. Task concurrency and
Solver instance parallelism are separate; increase task concurrency only when
the host and provider have capacity. Twenty serial twelve-hour attempts plus
judging can take days.

<a id="8-run-full"></a>

## Run Full

Full contains 100 tasks. Its default Online Solver protocol provides
submission feedback during development and needs a backend service. For the
same Docker host, first check the routing and quota requirements in the
[Docker backend guide](backend/docker.md#host-requirements), then build:

```bash
tcsexam build --suite full --solver-protocol online \
  --output build/full-online-images.json
```

Create service credentials once. The command refuses to overwrite an existing
`.env.backend`; reuse that file on later launches:

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

The URL uses Linux Docker's host-gateway route. Both development and judge
containers must reach it; use the backend guide for another network layout.
The archive credential is reserved for verification. `configure` writes
`build/full-backend.yaml` and `build/full-backend.plan.json`.

Leave `serve` running. Open a second terminal on the same host, enter the
checkout, and run:

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

Resolve blockers and review the job, then launch:

```bash
tcsexam run --suite full --solver-protocol online \
  --artifacts build/full-online-images.json \
  --backend-plan build/full-backend.plan.json \
  --attempts 1 --concurrency 1 --output build/full-job.json
```

Use [the result inspection steps](getting-started.md#6-read-the-actual-result) with `build/full-job.json` to inspect results. The generated local
backend plan schedules one task at a time and fits instance workers to host
resources. For routing, service or resource errors, use
[Online Solver configuration](running.md#online-solver).

To evaluate Full with Offline Solver, use the following commands in place of
the backend steps and label the result **Full Offline**:

```bash
tcsexam build --suite full --solver-protocol offline
tcsexam doctor --suite full --solver-protocol offline \
  --output build/full-offline-readiness.json
# Resolve blockers before launching:
tcsexam run --suite full --solver-protocol offline \
  --attempts 1 --concurrency 1 --output build/full-offline-job.json
```

<a id="9-calculate-suite-scores"></a>

## Calculate suite scores

Use final verified outcomes and the [scoring guide](scoring.md) to create the
adopted-attempt table and cohort file. It gives the complete commands for
`tcsexam solver-score` and `tcsexam score`. Solver requires final per-instance
records compared with the fixed reference; use the resulting relative score in
the attempt table. Harbor's aggregate task reward has a different purpose from
the TCSExam Index.

Include all selected tasks and planned attempts, retain failed or missing
judging states, and report the suite and Solver protocol. The score output
includes four track scores, coverage and the Index; incomplete input leaves the
Index null. Keep the model configuration, source revision, image records and
backend plan alongside the results.

