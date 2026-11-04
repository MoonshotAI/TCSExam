# Run the Online backend with Docker

[English](docker.md) | [简体中文](docker.zh-CN.md)

This guide deploys the TCSExam judging service on a local Linux Docker host.
It is for operators preparing Online Solver evaluations with the bundled adapter.

## Host requirements

Use Linux x86-64 with Docker Engine and a local Unix socket, normally
`/var/run/docker.sock`. The service user needs access to the socket. Set
`TCSEXAM_DOCKER_SOCKET` for another local socket path. The adapter supports local
Unix sockets; the CLI and Docker host share the task and output paths.

Docker must enforce memory and swap limits, CPU quotas and CPU sets. The planner checks
effective daemon and cgroup limits and CPU affinity, including capacity reserved
for development and the controller. Each judge image also needs the
[Landlock preflight](../judge-execution-isolation.md) to pass on this host.

A configured writable-layer storage quota requires support from the Docker
storage driver and filesystem. Keep the task's storage setting when reproducing
resource-constrained results. For a custom deployment without that quota, select
`--storage-limit none` explicitly; the plan records it as disabled.

The prepared worker image provides `/bin/sh`, `sleep`, `mkdir`, `setsid` and
`python3`. Image preparation uses the local build recipes or configured pinned
images; see [resource preparation](../resources.md).

## Generate a selected-task configuration

After [installing TCSExam](../getting-started.md), prepare a task and generate its
service configuration:

```bash
python -m pip install -e '.[runtime,backend]'
tcsexam build --suite full --track solver --task bpp-bpplib --solver-protocol online
tcsexam backend configure --suite full --track solver --task bpp-bpplib \
  --judge-url http://host.docker.internal:8420 --config build/backend.yaml
```

This writes `build/backend.yaml` and `build/backend.plan.json`. The plan holds the
prepared image identities, separate public/final client settings and host resource
limits. Keep the same selection, Docker context and cache for the following commands.

The generated service uses one live session and the job plan permits one trial at
a time. Within a task, independent instances can use concurrent workers as capacity
allows. Each worker keeps its declared CPU, memory and solver budget. Tasks with a
shared time pool use one complete judging group. A host unable to fit one required
worker receives a preparation error showing the missing capacity.

## Configure credentials and networking

Supply the following values through your service environment or secret manager:

| Variable | Use |
|---|---|
| `TCSEXAM_TOKEN_ID` | Service identity used by clients and worker tunnels |
| `TCSEXAM_TOKEN_SECRET` | Shared service secret |
| `TCSEXAM_ARCHIVE_TOKEN` | Verifier-only credential for hidden creation, reconciliation and archive access |
| `TCSEXAM_BASE_URL` | Service address reachable from development and verifier containers |

The `public_base_url` in the service configuration is the callback address used
by judge workers. With the service running on the Linux Docker host, the generated
host-gateway configuration uses `http://host.docker.internal:8420`. Set the client
address to the same route:

```bash
export TCSEXAM_BASE_URL=http://host.docker.internal:8420
```

For a different network layout, choose addresses reachable from the client and
worker networks and check both routes. A container's `127.0.0.1` refers to that
container. When the daemon runs in a separate network namespace, use a callback
address reachable from that namespace. Use authenticated HTTPS across untrusted
networks. Worker tunnels are outbound; judge ports remain unpublished.

Give the Docker socket only to the backend process and the archive token only to
the verifier. Keep both outside model containers and judge workers. The generated
configuration requires all three credential variables when the service starts.

## Check and start

In the service terminal:

```bash
: "${TCSEXAM_TOKEN_ID:?Set the service identity}"
: "${TCSEXAM_TOKEN_SECRET:?Set the service secret}"
: "${TCSEXAM_ARCHIVE_TOKEN:?Set the verifier-only secret}"
tcsexam backend check --config build/backend.yaml
tcsexam backend serve --config build/backend.yaml
```

`check` validates the configuration and loads the adapter. `serve` keeps the
service running. In another terminal, load the same service credentials, configure
your [model provider](../running.md#choose-an-agent), and run:

```bash
tcsexam prepare --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json \
  --output build/bpp-job.json
tcsexam doctor --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json
tcsexam run --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json \
  --output build/bpp-job.json
```

`TCSEXAM_BACKEND_PLAN` is the environment-variable equivalent of `--backend-plan`.
The launcher supplies public credentials to development and the archive credential
to the verifier. Judge results and task artifacts are collected in the job output.

## Resources and lifecycle

Docker workers receive `NanoCpus`, `Memory`, `MemorySwap=Memory` and non-overlapping
`CpusetCpus` reservations. Setting the combined memory-and-swap limit equal to
memory disables swap, matching Offline workers. The adapter checks Docker's swap
limit support and verifies the created image, network and resource settings.
Configured storage quotas are passed through `StorageOpt.size` and inspected after
creation. Workers run without privileged mode or host bind mounts.

Generated public clients release their workers after a completed submission
(`TCSEXAM_CLOSE_SESSION_AFTER_SUBMIT=1`). Final clients release the run's public
sessions before creating the hidden session (`TCSEXAM_CLOSE_AGENT_SESSIONS=1`).
Keep these settings together with the one-session service cap. The backend retains
submission records and archives after releasing compute resources.

The planner derives startup, read, idle and session deadlines from the selected
workload and checks the image's `JUDGE_TIMEOUT`. The task scorer enforces its own
solver timer. For a custom deployment, allow enough time for preparation,
compilation, solving and checking at the configured parallelism.

Workers carry `org.tcsexam.*` identity and expiry labels. On the next creation after
a restart, the service restores resource accounting and removes expired workers.
Expiry handling requires the backend process to be running. Inspect managed workers
with:

```bash
docker ps -a --filter label=org.tcsexam.managed=docker-adapter
```

Check container ownership before removing a stale worker.

## Troubleshooting

| Symptom | Action |
|---|---|
| Worker callback fails | Check `public_base_url` from the worker network and the Docker bridge firewall. |
| Client cannot reach the service | Check `TCSEXAM_BASE_URL` from the development and verifier networks. |
| CPU, memory or quota admission fails | Resolve the resource requirement reported in the plan or use a host supporting the configured quota. |
| Docker lacks swap-limit support | Enable swap accounting in the host kernel/cgroup configuration and verify Docker reports `SwapLimit: true`. |
| Recovered workers have missing or overlapping CPU reservations | Let those owned workers finish or remove the identified stale containers before new admission. |
| Recovered worker has no enforced swap prohibition | Let the worker finish or remove that owned container; newly created workers receive the updated resource settings. |
| Image pull exceeds an API timeout | Image pulls use the full worker-creation deadline; check `backend.ready_timeout_seconds` and per-image routes. Ordinary Engine calls use `docker_api_timeout_seconds`. |
| Docker exec times out | The command can remain active inside the worker. Inspect the worker and delete that owned worker if execution must stop. Control-file reads and captured output are limited to 64 MiB each. |

## Adapter development and manual configuration

For custom service settings, start from [config.example.yaml](config.example.yaml)
and use the [service configuration reference](service.md#configuration-reference).
Other platforms use `adapter: module:factory` and the
[platform adapter contract](service.md#writing-a-platform-adapter).

To exercise actual Docker worker creation, execution and cleanup:

```bash
python -m tcsexam.backend.contracttest \
  --adapter docker --config build/backend.yaml \
  --image YOUR_REVIEWED_JUDGE_IMAGE --profile local
```

Use an available judge image. The suite creates a 3-CPU/4096-MiB worker and
additional workers with configured defaults, then removes its resources. Provision
capacity for them together. The `local` profile is retained as metadata in the
Docker adapter.
