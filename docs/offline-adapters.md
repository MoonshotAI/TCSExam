# Offline Solver adapters

[English](offline-adapters.md) | [简体中文](offline-adapters.zh-CN.md)

This guide describes local Docker execution for Offline Solver judging.
It is for users preparing public self-tests and hidden final judging.

## Run a suite

After [installing the runtime and configuring a model](getting-started.md), run:

```bash
tcsexam build --suite lite --track solver --solver-protocol offline
tcsexam doctor --suite lite --track solver --solver-protocol offline
tcsexam run --suite lite --track solver --solver-protocol offline
```

Use `--suite full` for all thirty Solver tasks or `--task TASK_ID` for one task.
The builder prepares development and verifier images and saves their identities
in the local cache. `doctor` checks the selected images and execution host.
Resolve its reported blockers before starting the run.

During final judging, Harbor starts a verifier controller. The controller creates
isolated Docker workers, supplies the submission and assigned hidden inputs,
collects their results and removes its workers. Offline execution uses this
per-attempt controller; Online service deployment is described in the
[Docker backend guide](backend/docker.md).

## Execution-host resources

Use a rootful Linux Docker daemon with `/var/run/docker.sock` on the execution
host. The verifier's `tests/docker-compose.yaml` mounts this socket and a
read-only host cgroup tree and uses the host PID and cgroup namespaces. The CLI
user needs Docker access. This compose configuration requires the standard socket
path, including when selecting a Docker context.

The socket belongs exclusively to the trusted verifier controller. Development
containers and judging workers run without it. Judge workers also require
[Landlock and the image preflight](judge-execution-isolation.md); build and solver
commands run as UID/GID 65534 under root supervision.

Worker reservations are declared in each task's `tests/runtime/task.json`.
The controller admits workers only when their full CPU and memory reservations
fit, with one additional CPU and 512 MiB reserved for the controller. For example,
a 32 GiB worker requires at least 33,280 MiB of visible host memory, plus enough
free memory and disk at admission time. A four-CPU worker needs at least five
visible CPUs including the controller reserve. The development container has its
own additional requirements, checked before model execution.

Each task uses at most ten concurrent judging workers. Smaller hosts run fewer
workers at once while preserving each worker's resources and each instance's
solver budget. Where a task declares shared shard memory, a worker reserves the
full amount. Insufficient capacity produces an environment error with the required
resources in the report.

## Judging and results

Each worker invokes the task's preparation script and checker for its assigned
instances. The checker validates the candidate output and computes its objective
value. The controller combines the complete instance records into the final task
result. See [scoring](scoring.md) for task rewards, failed judging and Index
calculation.

Bin packing, graph partitioning, sports timetabling, logic synthesis, quadratic
assignment and set covering each use one worker for the complete shared time pool: all instances
share one total solver budget. Keep these groups intact when configuring
parallelism. Other tasks use their declared per-instance limits and grouping.

The outer worker deadline allows time for compilation, solving and validation.
The scoring program separately enforces the task's solver budget. CPU indices
used by a scorer map to the CPUs reserved for its worker.

## Troubleshooting

| Symptom | Action |
|---|---|
| Docker socket or cgroup access fails | Run on the rootful Docker host with the standard socket and the task's verifier compose configuration. |
| Judge startup reports an isolation error | Run the image preflight on that host and resolve the reported kernel, syscall or identity-transition requirement. |
| Worker admission reports insufficient capacity | Free the required resources or choose a larger host; retain the task's declared worker size. |
| Initial archive upload fails | Inspect `resources.json`. The controller automatically retries the specific pre-start missing-root error up to three times with the same submission and instance group. Other errors are reported for operator action. |
| A result is missing or judging failed | Inspect the verifier logs and instance records before calculating the task score. |

## Build a selected adapter

```bash
tcsexam build --suite full --task ce-pace2021 --solver-protocol offline
```

The task's `offline-adapter.json` declares its Online development image, backend
and verifier-tool dependencies. The builder resolves these dependencies and reuses
unchanged local products. For resource inputs and cache options, see
[resource preparation](resources.md). For development and source checks, see
[contributing](../.github/CONTRIBUTING.md).
