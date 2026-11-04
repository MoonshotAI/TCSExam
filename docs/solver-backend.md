# Online Solver backend protocol

[English](solver-backend.md) | [简体中文](solver-backend.zh-CN.md)

This reference describes the HTTP interface used by Online Solver clients.
It is for service operators and developers implementing a compatible adapter.

## Deployment scope

1. Prepare the selected development and judge images with `tcsexam build`.
2. Configure credentials and start the service using the [Docker deployment guide](backend/docker.md)
   or a [custom platform adapter](backend/service.md#writing-a-platform-adapter).
3. Configure `prepare`, `doctor` and `run` for the chosen deployment:

   - Docker deployment: supply the generated `--backend-plan PATH`, which includes
     the service address and the worker plan for the selected tasks.
   - External service: pass `--judge-url URL` or set `TCSEXAM_BASE_URL` to an
     address reachable from the task containers. A generated Docker plan is
     optional; without one, the launcher uses each task's standard worker count,
     resources and timing recorded under `standard_client_timing` in the selection
     record. The service must provide those resources and honor the task budgets.
4. Inspect submission records and final results in the job output.

The clients are `tasks/solver/online/<task>/environment/submit.sh` and
`tasks/solver/online/<task>/tests/fetch_final.py`. They use the task's declared
instance sets, time budgets and scoring rules.

## Credentials and attempt identity

All requests use authentication. Archive credentials are supplied to the verifier alone. Header names are case insensitive.

| HTTP header | Value |
|---|---|
| `X-TCSEXAM-Token-Id` | `TCSEXAM_TOKEN_ID` |
| `X-TCSEXAM-Token-Secret` | `TCSEXAM_TOKEN_SECRET` |
| `X-TCSEXAM-Client-Id` | Stable identifier for this task attempt |
| `X-TCSEXAM-Run-Id` | The same task-attempt identifier |
| `X-TCSEXAM-Agent-Name` | Optional `TCSEXAM_AGENT_NAME` |
| `X-TCSEXAM-Archive-Token` | Verifier-only credential from `/tests/archive_token` |

Set `TCSEXAM_RUN_ID` to a unique, stable identifier for each attempt. The clients
use the container hostname when it is absent. The backend must isolate different
attempts sharing an egress address. Credentials and archive contents must stay
scoped to the owning attempt; the model must not receive the archive credential.

The supplied service checks each session's declared Run-Id. This separates
cooperating callers using shared service credentials. Run-Id is a caller-supplied
label; deployments that must prevent deliberate impersonation also need
independently authenticated credentials for each attempt. See the service's
[security boundaries](backend/service.md#security-boundaries).

Use the same header names for foreground requests, background keepalive requests,
final judging and audit downloads. The TCSEXAM interface uses this namespace
throughout. Hidden-session creation, every creation carrying `judge_payload`,
and every session list/reconciliation query require the archive header in
addition to the service token pair. Missing, wrong and unconfigured archive
credentials receive 403 on these create/list operations. Public self-test
creation without `judge_payload`, status, submission and result polling use
only the service token pair. Send the archive header only to the create/list
and archive/payload service endpoints, not through solver submission relays
into judge workers.

Use the TCSExam launcher to pass credentials into the agent and verifier
containers. For a custom launcher, populate the task's
`${TCSEXAM_*}` placeholders and preserve verifier-only credential placement.

## Session interface

These paths are relative to `TCSEXAM_BASE_URL`. The existing clients define exact per-task behavior; the endpoints below show their shared interface.

| Method and path | Behavior |
|---|---|
| `POST /v1/judge/sessions` | Accept `judge_image`, `ttl`, `n_shards`, `resources`, and optional `instance_set` and `judge_payload`; return `session_id`. Public self-tests request `public` and require an exact `public_image_map` entry. Without a payload they use only service authentication. Omitted instance set defaults to `hidden`; hidden creation and every creation carrying `judge_payload` also require the archive header. |
| `GET /v1/judge/sessions` | List live and recently destroyed sessions. Requires the archive header; this also applies to the `session_ids` and `client_ip` query forms below. |
| `GET /v1/judge/sessions/{id}` | Report readiness and failures. Provisioning must finish before judging starts. |
| `POST /v1/judge/sessions/{id}/submit` | Accept raw tar.gz with `Content-Type: application/gzip`; return integer `submission` after accepting it. Do not send the archive header through this relay. |
| `GET /v1/judge/sessions/{id}/submissions` | Return `submissions`, each with `submission`, `status`, and per-instance `records`. Unfinished submissions use `running`. |
| `GET /v1/judge/sessions/{id}/archive` | Require the archive header and return raw per-shard records, including `instance_set`, `n_shards`, `shard_payloads`, and `failed_shards`. |
| `GET /v1/judge/sessions?session_ids=a,b` | Require the archive header. Return per-session hidden `submissions`, `public_submissions` and `present`; retain counts after resource teardown. |
| `DELETE /v1/judge/sessions/{id}` | Release workers while retaining the counts and records needed for verification. |

The optional audit endpoints `GET /v1/judge/sessions/{id}/payload/submissions`
and `GET /v1/judge/sessions/{id}/payload/submissions/{seq}` list submission
numbers and return original uploaded tar bytes. They use the archive header.
Unavailable optional payloads are recorded separately from judging failures.
The legacy operational query `GET /v1/judge/sessions?client_ip=self` is optional
telemetry and also requires the archive header; it must not decide an attempt's
score or submission allowance.

A submission is counted once when accepted. HTTP 503 means it has not been
accepted and can be retried. An ambiguous upload disconnect must not be retried
blindly. The current verifier interprets HTTP 429 on `/submit` as the submission
cap, so the backend must not use that response for ordinary worker congestion.
HTTP 410 or `error_class=terminal` means the session is permanently unavailable.

Retain every instance's objective value, validity and status, including instances
excluded from a particular score average. Infrastructure failures must remain
distinct from valid zero scores. Preserve each task's time pools, certificate
checks, budgets, history-selection rules and public/hidden separation.

## Images and deployment

Public creation resolves an exact `public_image_map` key from the requested judge
image to a public-only worker image. Missing entries receive HTTP 403 before any
worker is created. Hidden creation uses the requested hidden image.

Prepare images with `tcsexam build`, or provide an external manifest with
immutable backend image assignments. Before registering a public image, follow
[public-image preparation](backend/public-images.md) to check its inputs and
retained layers. Then configure the map and start the service through the
[Docker guide](backend/docker.md).
