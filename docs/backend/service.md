# Deploy the Online judging service

[English](service.md) | [简体中文](service.zh-CN.md)

This guide covers service configuration, operation and platform adapters.
It is for operators hosting Online Solver judging.

The service manages HTTP requests, judge sessions, parallel workers, feedback,
archives and submission counts. Select the bundled Docker adapter for a local
Docker host, or implement the platform adapter interface for another runtime.
Operators provide the execution hosts, judge images and service credentials.

For a local Docker deployment, follow the [generated configuration workflow](docker.md).
The [HTTP protocol reference](../solver-backend.md) defines client requests and responses.

## Install

```bash
python -m pip install -e '.[runtime,backend]'
```

## Configure

For a manually configured service, copy the example and set credentials in the
service environment:

```bash
mkdir -p build
cp docs/backend/config.example.yaml build/backend.yaml
: "${TCSEXAM_TOKEN_ID:?Set the service identity}"
: "${TCSEXAM_TOKEN_SECRET:?Set the service secret}"
: "${TCSEXAM_ARCHIVE_TOKEN:?Set the verifier-only secret}"
```

Start from [config.example.yaml](config.example.yaml), a Docker example whose
commented values show the defaults. Secrets come from the environment first
(`TCSEXAM_TOKEN_ID`, `TCSEXAM_TOKEN_SECRET`, `TCSEXAM_ARCHIVE_TOKEN`,
`TCSEXAM_WORKER_GROUP`) and override the YAML values; keep real tokens out of
committed files. `TCSEXAM_DOCKER_SOCKET` overrides the Docker socket path.

`public_base_url` deserves attention: the agent inside each judge worker
dials `<public_base_url>/v1/tunnel/{app}`, so it must be an address the judge
workers can reach. It defaults to `http://127.0.0.1:<port>`, which works for
local testing with the bundled test adapter. The Docker example explicitly
uses `http://host.docker.internal:8420`; the Docker adapter rejects a
container-loopback URL on a non-host worker network. See the
[Docker networking and host requirements](docker.md#host-requirements).

Keep the archive credential exclusive to the verifier. Confirm that the worker
callback address is reachable and that the selected images are prepared before
starting the service.

## Start and check

```bash
tcsexam backend check --config build/backend.yaml   # validate config + load the adapter
tcsexam backend serve --config build/backend.yaml   # run the service
```

`check` prints the effective configuration as JSON and loads the configured
adapter. It exits 0 on success and 2 on any configuration problem (including
an empty `adapter` or an adapter that fails to load), so it is safe to wire
into deployment pipelines. `serve` accepts `--host` / `--port` overrides.
`python -m tcsexam.backend --config build/backend.yaml` is an equivalent entry point.

## Configuration reference

Reading the tables: every value is the built-in default, applied when the key
is absent from the YAML. Keys marked "env" are overridden by the environment
variable of the same name when set.

Top-level keys:

| Key | Default | Description |
|---|---|---|
| `host` | `0.0.0.0` | Bind address of the HTTP service |
| `port` | `8420` | Bind port |
| `public_base_url` | `""` (falls back to `http://127.0.0.1:<port>`) | Externally reachable base URL; in-worker agents dial `<public_base_url>/v1/tunnel/{app}` |
| `auth.token_id` | empty | Shared-token auth id (env `TCSEXAM_TOKEN_ID`); both empty = unauthenticated, local testing only |
| `auth.token_secret` | empty | Shared-token auth secret (env `TCSEXAM_TOKEN_SECRET`) |
| `auth.additional_tokens` | `[]` | Extra accepted (id, secret) pairs for graceful rotation |
| `auth.run_id_mode` | `warn` | Caller-identity enforcement: `warn` logs and serves, `required` rejects with 400, `off` does not read the header |
| `state_dir` | `/tmp/tcsexam-backend-state` | Session journal, archives, persisted payloads |
| `adapter` | `""` | Platform adapter spec: `docker`, `module:factory`, or `local-test` for testing only; empty = the service refuses to create sessions with a clear error |
| `docker_socket` | `/var/run/docker.sock` | Local Docker Engine Unix socket (env `TCSEXAM_DOCKER_SOCKET`); remote TCP endpoints are rejected |
| `docker_network` | `bridge` | Docker network for judge workers; `public_base_url` must be reachable from it |
| `docker_pull_missing_images` | `true` | Pull a missing judge image, using the full creation budget; private images should be pulled by the operator |
| `docker_host_gateway` | `true` | Add `host.docker.internal:host-gateway` to workers for the Docker-host tunnel address |
| `docker_api_timeout_seconds` | `60` | Ordinary Docker API call timeout; cold image pulls use the full creation budget instead |
| `worker_group` | `tcsexam` | Worker-group tagging prefix (env `TCSEXAM_WORKER_GROUP`); empty = no group tagging. When a session is created with a run-id, EVERY shard's worker creation carries `labels={run_id, token_id}` and `group_name="<worker_group>--<run-id slug>"` (the platform can reap exactly one attempt's workers); sessions without a run-id are created untagged |
| `archive_token` | `""` | Verifier-only credential (env `TCSEXAM_ARCHIVE_TOKEN`) for archive/payload, hidden-session creation, every creation carrying `judge_payload`, and session list/reconciliation queries; empty disables those operations |
| `public_image_map` | `{}` | Exact map from a client-requested original judge image to its public-only worker image. Public creation fails closed with 403 when this is empty or the requested image is absent; hidden creation never uses the map |

`backend` section (worker creation and global usage caps):

| Key | Default | Description |
|---|---|---|
| `create_retries` | `20` | Extra creation attempts after the first failure, transient errors only |
| `create_retry_delay_seconds` | `60` | Base delay between creation retries; attempt N waits base x 2^(N-1), capped at 10 min |
| `create_concurrency` | `64` | Upper bound on concurrent worker creations |
| `session_create_concurrency` | `64` | Per-session creation concurrency, taken before the global gate |
| `max_sandboxes_global` | `4096` | Global worker-count pre-check at create accept time |
| `max_sandbox_memory_mb` | `32768000` | Memory dimension (MiB) of the same pre-check |
| `ready_timeout_seconds` | `2400` | Platform-side creation/readiness budget handed to the adapter |

`backend.judge_sessions` section (the main knobs; the example file comments
the rest):

| Key | Default | Description |
|---|---|---|
| `max_sessions` | `16` | Global live-session cap; creates beyond it fail as transient |
| `profile` | `""` | Opaque scheduling hint passed to the adapter as-is |
| `spec` | `{cpu_count: 4, memory_mb: 8192, storage_mb: 20480}` | Per-worker resources handed to the adapter verbatim |
| `command` | `python3 /judge/judge_worker.py` | Judge worker started inside the worker; empty = the agent only relays to an already-running server |
| `judge_port` | `8082` | Port the in-worker judge server listens on |
| `ttl_seconds` | `21600` | Default per-session TTL (platform safety net) |
| `max_ttl_seconds` | `46800` | Clamp for caller-requested TTL |
| `idle_ttl_seconds` | `14400` | Idle-reap threshold; must exceed the longest single judge request |
| `ready_timeout_seconds` | `1800` | Create + boot budget before the tunnel wait fails |
| `max_shards` | `512` | Upper bound on `n_shards` per session |
| `min_ready_ratio` | `1.0` | Degraded-ready floor; 1.0 = partial provisioning fails the whole session rather than producing a partial score |
| `hibernate_enabled` | `true` | Recycle settled, quiet sessions to metadata-only and re-provision on the next submit |
| `hibernate_grace_seconds` | `1800` | Quiet period before a settled session hibernates |
| `submission_cap.enabled` | `false` | Per-session submission cap (opt-in); counting always runs for reconciliation visibility |
| `submission_cap.default` | `10` | Cap per judging session |
| `submission_cap.overrides` | `{}` | Per-image-family cap; a family hit beats the default |
| `routes` | `[]` | Per-image-family readiness/lifecycle budgets; first `image_contains` substring match wins. `ready_timeout_seconds` drives tunnel wait and agent startup; `create_ready_timeout_seconds` goes to the adapter. `ttl_seconds` supplies the default when the caller omits TTL; `idle_ttl_seconds` sets that session's idle threshold. Explicit requested TTL takes precedence and still obeys `max_ttl_seconds`. Routed values survive hibernation and wake-up. |

The primary `auth.token_id` and `auth.token_secret` must both be non-empty
strings. Omit both to disable authentication for a local test. A partial or
empty pair fails configuration validation. Each `additional_tokens` entry
must contain exactly two non-empty strings, and rotation credentials require
a primary pair: workers use the primary credentials to connect their tunnels.
Validation runs after environment overrides when loading YAML and again when
building the application; errors name the invalid field without printing its
value. Credential comparison accepts Unicode and uses constant-time byte
comparison for both elements of every pair.

Concurrent creates share a provisioning session only with an explicit
`X-TCSEXAM-Client-Id` and identical effective inputs: token identity, validated
run-id, effective worker image (after public mapping), uploaded file names
and contents, resources, lifetime, shard count and instance set. Omitting default resources or lifetime is equivalent
to passing the same defaults explicitly. A changed input creates a separate
session; it cannot silently reuse a worker containing another upload.

Session lifetime, worker startup and request reading are separate budgets.
The shipped development clients request 46800 seconds (12 hours plus one
hour of margin); the default `max_ttl_seconds` is also 46800. The public
sharded store starts the service-side lifetime when the group becomes ready,
while the platform worker lifetime starts at worker creation. Startup time
therefore consumes some platform margin. Hibernation releases workers and a
later submission provisions new ones; it retains submission history and
renews the service-side lifetime at readiness. Final-evaluation clients
create separate sessions and retain their per-task 14400–28800 second
lifetimes. Reducing `max_ttl_seconds` clamps either client's request and can
expire an active session before its budget is used; allow both judging time
and startup margin in the platform configuration.

`ready_timeout_seconds` bounds the tunnel connection wait. The worker agent
uses the same startup budget, capped at 7200 seconds, in both single-worker
and sharded creation. Per-image `create_ready_timeout_seconds` goes to the
platform adapter. `read_timeout_seconds` (default 7200) bounds an upstream
judge response and is forwarded to every worker agent. For a long judging
request, increase its read timeout and the corresponding fan-out timeout;
increasing session lifetime alone does not increase these request limits.

## Behavior contract

These semantics are fixed by the task clients and covered by tests; a
deployment must not change them.

* A submission is counted once, when accepted. `POST
  /v1/judge/sessions/{id}/submit` returns an integer submission number after
  accepting the body. The counting unit is the relay-level `/submit`; shard
  fan-out is judging-internal parallelism and never counts.
* HTTP 429 on `/submit` means the per-session submission cap, with body
  `{"error": "submission_cap_exceeded", "cap": ..., "used": ...}`. The
  verifier interprets 429 as the cap, so the backend must not use it for
  ordinary worker congestion.
* HTTP 503 (`error_class=transient`) means the submission was not accepted
  and can be retried. It covers still-provisioning sessions and
  global-capacity rejections. Transient messages carry the marker "please
  try again", which the task-side retry matchers match verbatim.
* HTTP 410 (or `error_class=terminal` in a JSON body) means the session is
  permanently destroyed.
* DELETE destroys every worker and closes every service-side reverse tunnel
  belonging to the session, including every shard. A late reconnection using
  the destroyed session's one-shot app name is rejected with 404; ordinary
  tunnel drops still allow reconnection. The retained archive and the
  creation/submission payload history remain readable by the verifier after
  the session status becomes 410.
* Infrastructure failures never produce a valid zero score. With the default
  `min_ready_ratio: 1.0`, partial provisioning fails the whole session; a
  failed provisioning never accepted a submission, so the caller's submission
  budget is untouched.
* Tasks with one shared time pool across instances must be created with
  `n_shards=1` — the whole instance set on one worker. Sharding a pool task
  would change its judging semantics. The shipped clients already encode
  this.
* The archive credential (`X-TCSEXAM-Archive-Token`) is presented by the
  verifier alone. It gates archive and payload downloads, hidden-session
  creation (including an omitted `instance_set`, which defaults to hidden),
  every public or hidden creation carrying `judge_payload`, and every session
  list/reconciliation query. Missing, wrong and unconfigured credentials are
  rejected before any worker is created or session data is returned. Archive
  and payload endpoints retain their uniform-404 contract; the create and list
  gates answer 403.
* Public self-test sessions (`instance_set=public`) without `judge_payload`
  need only the service token pair. Their status, submission and
  result-polling paths do not use the archive credential. Public creation
  requires an exact `public_image_map` entry and uses its public-only value as
  the session and worker image. An empty map or unregistered requested image
  answers 403 before session registration or worker creation; there is no
  fallback to the original image. Hidden creation never applies the map.
  Public sessions are journaled for history but never count against the
  submission cap.
* Sessions are owned by the run that created them. The effective run-id
  (`X-TCSEXAM-Run-Id`, validated by the auth middleware) is stored on the
  session and journaled, so it survives DELETE and service restarts. Every
  session-level endpoint — status, relay (`/submit`, `/submissions`, and
  any forwarded tail), DELETE, archive, the three payload endpoints, and
  the `?session_ids=` reconciliation query — serves only requests whose
  run-id matches the session's owner. A mismatch answers exactly like an
  unknown session id: the uniform 404 (`unknown judge session {sid}`),
  never a 401/403 and never the 410 destroyed shape, so the check does not
  leak whether the session exists; in the `?session_ids=` answer a
  mismatched sid reports `present=false` with its counts withheld. Sessions
  returned by the ordinary list and `?client_ip=` diagnostic query obey
  the same ownership filter, including retained destroyed sessions; the
  diagnostic query's total includes only visible rows. DELETE of an
  unknown session answers the same 404 as a wrong run, while repeated
  DELETE by the owner of a known released session stays 200 and returns
  `stopped=false`, including after journal replay. The `/v1/status` route
  remains a service-wide operations view with global statistics.
  Sessions created without a run-id are unowned and unrestricted (local and legacy
  callers that never send run-ids keep working). Creation dedup keys on the
  run-id too: two runs never share a provisioning session even when they
  send the same `X-TCSEXAM-Client-Id`, while one run's concurrent retry
  still shares.

## Security boundaries

- Use a service token pair for authenticated deployments and inject it through
  the environment. Store real credentials outside the source repository.
- Give the archive token only to the verifier. It authorizes hidden-session
  creation, session reconciliation and archive access; keep it out of model
  environments, workers and submission relays.
- Run-Id is a caller-supplied attempt label. For mutually untrusted callers,
  provide independently authenticated per-attempt credentials or an equivalent
  authorization layer in addition to the shared-token service.
- Map public sessions to images containing only public data. Review every retained
  image layer using the [public-image guide](public-images.md); select the public
  judging mode after separating the image contents.
- Give the Docker socket only to the backend process. It controls the host and
  must remain outside model containers and judge workers.
- Keep platform credentials inside the adapter configuration and exclude them
  from logs, worker environments and exception messages.

## Troubleshooting

| Symptom or deployment condition | Action |
|---|---|
| Docker admission or quota check fails | Check the effective CPU, memory and configured storage quota in the [Docker host guide](docker.md#host-requirements). |
| A worker remains after the service stopped | Restart the service to recover its managed workers, or inspect and remove only the identified owned container. Expiry handling runs in the backend process. |
| A custom or older worker gets HTTP 400 with `run_id_mode=required` | Send its owning `X-TCSEXAM-Run-Id` on the tunnel connection. Keep `warn` during a mixed-version upgrade and update worker agents before enabling `required`. |
| A long evaluation loses its session | Allow the requested lifetime and startup margin in `max_ttl_seconds`; also check request read timeouts in the configuration reference. |
| Selecting `local-test` | Use it only for backend development tests. Its workers are local temporary directories with no resource limits or isolation. |

## Writing a platform adapter

The full contract is the module docstring of `tcsexam.backend.adapter`. A
minimal, annotated skeleton ships at
[examples/adapter_minimal.py](examples/adapter_minimal.py).

Reading the table: these are the members the session stores call. The loader
verifies all of them at startup; a missing member is a configuration error,
never a silent degradation.

| Member | Signature | Contract |
|---|---|---|
| `ready_timeout_seconds` | attribute `float` | The adapter's own creation budget, read by the store's provisioning-deadline math |
| `create_sandbox` | `(profile, image_url, *, ttl_seconds, spec, ready_timeout_seconds, group_name, labels) -> Worker` | Create one worker from `image_url` with exactly the requested resources |
| `register_long_lived` | `(app_name, worker) -> None` | Put a worker on the long-lived table (the tunnel-close reaper and `stop_app` work through it) |
| `sandbox_for_app` | `(app_name) -> Worker \| None` | The live long-lived worker for an app, no state change |
| `long_lived_count` / `long_lived_memory_mb` | `() -> int` | Long-lived table size and total memory, for usage accounting |
| `stop_app` | `async (app_name) -> None` | Destroy a long-lived worker; idempotent, unknown app = no-op |

The worker surface the stores use:

| Member | Signature | Contract |
|---|---|---|
| `worker.ctrl.write_bytes` | `async (path, data: bytes, parents=False) -> None` | Write bytes inside the worker; `parents=True` creates missing directories |
| `worker.ctrl.run` | `async (cmd, shell=False, text=False, timeout=30)` | Run a command inside the worker; returns an object with a `stdout` attribute. Raise on transport failure; a non-zero exit code is reported, not raised |
| `worker.ctrl.read_text` | `async (path) -> str` | Read a text file; raises when missing or unreadable |
| `worker.name` | attribute `str` | Platform-side identifier, used in logs only |
| `worker.delete` | `async () -> None` | Destroy the worker; idempotent, best-effort (the worker's own TTL is the final safety net) |
| `worker.resources` | optional attribute `WorkerResources` | The creation-time resources. Not required: `BasePlatformAdapter` prefers it for the `long_lived_memory_mb` accounting and otherwise falls back to the resources its own `create_sandbox` recorded |

Behavior rules every implementation must keep:

* Honor the requested image and resources as given. If the platform cannot
  provide them, raise a clear error. Silently booting a smaller worker is a
  contract violation: judging runs assume the declared resources.
* Error classification is by class name. Names in
  `errors.NON_TRANSIENT_ERROR_NAMES` (`AuthenticationError`,
  `PermissionDeniedError`, `InvalidArgumentError`,
  `InsufficientCreditsError`, `JudgeBootError`) are never retried; every
  other exception is treated as transient and retried with exponential
  backoff. `ValueError` is always non-transient (a caller bug).
* `stop_app` and `worker.delete()` are idempotent.
* Cleanup is scoped: only ever destroy resources the adapter itself created,
  never account-wide purges.
* A cancelled creation must not leak a half-created worker.
* Platform credentials live in the adapter's own configuration and must never
  appear in logs, worker environment variables, or exception messages —
  exception text propagates to task clients.

Subclassing `BasePlatformAdapter` provides the transient-retry loop under a
creation concurrency gate, the long-lived table, and an idempotent `stop_app`
with agent.log tail recovery; you then implement only `_create_worker`, one
creation attempt against your platform.

Loading: `adapter: docker` selects the bundled Docker implementation described
in the [Docker guide](docker.md). For another platform, set `adapter` to a
`module:factory` spec. The factory is imported, called with the loaded `Config`
when it accepts one positional argument (otherwise with no arguments), and the
result is checked for the full surface above. An empty `adapter` fails at
startup with a `ConfigurationError` — the service never falls back to a test
double silently. The explicit value `local-test` selects the bundled
local-process test adapter (testing only; its "workers" are temp directories
on the service machine, with no isolation and no resource enforcement).

Self-check any adapter against the bundled contract suite:

```bash
python -m tcsexam.backend.contracttest --adapter mypackage.cloud:make_adapter --config config.yaml \
    --image registry.example.com/your-judge:1 --profile your-profile
python -m tcsexam.backend.contracttest --adapter docker --config config.yaml \
    --image registry.example.com/your-judge:1 --profile local
python -m tcsexam.backend.contracttest --adapter local-test   # exercise the test double
```

The suite prints one line per check and exits 0 when all pass, 1 when any
check fails, 2 when the adapter cannot be loaded. It creates real resources
through the adapter and destroys every worker it creates — point it at a test
environment. The checks are platform-neutral: creation honoring the request
verbatim, unique worker identity, file preparation, status diagnostics,
command start, memory accounting, idempotent stop/delete, creation-failure
cleanup, and scoped cleanup.

`--image` and `--profile` select what the checks pass to `create_sandbox`.
Pass an available image and the profile your platform expects. The defaults
(`registry.example.com/contract-judge:1` / `contract-profile`) are examples for
the local test adapter.

## Testing and verification

```bash
python -m pytest src/tcsexam/backend/tests/
```

The suite exercises HTTP requests, sharding, submission accounting, archives,
run ownership, lifecycle and adapter behavior. Docker unit tests use a simulated
Engine over a Unix socket. To exercise actual worker creation and cleanup, run
the [adapter contract suite](#writing-a-platform-adapter) with an available image
and platform profile.
See [contributing](../../.github/CONTRIBUTING.md) for the complete source checks.
