This reference describes the host and image requirements for running TCSExam.
It is for users sizing an evaluation host or preparing a judging service.

# Runtime requirements

[English](runtime-availability.md) | [简体中文](runtime-availability.zh-CN.md)

## Host and task resources

Run on Linux x86-64 with Python 3.12+, Docker Engine, Compose and Buildx.
Use a local Unix Docker socket accessible to the evaluation user. The CLI and
Docker must share task and job paths; remote SSH/TCP Docker contexts are
rejected. Installation checks are in [running evaluations](running.md#install-and-select).

Lean tasks request 4 CPU cores and 16 GiB of memory each. Reserve additional
capacity for the operating system and builds, and at least 40 GB of disk for
the shared Lean environment, layers and logs. This disk allowance covers that
shared environment; a Full build also needs its selected datasets and images.

Solver requirements vary by task and split. Read the task's `task.toml` and the
resource plan produced by the controller or backend planner. The host must fit
the development container, controller reserve and at least one worker with the
task's full per-instance allocation. Reducing task concurrency cannot make an
individual worker smaller. Instance scheduling preserves each instance's compute
and time allowance; shared-time-pool tasks keep their complete pool in one worker.
See [Offline resource rules](offline-adapters.md) and
[Online backend resources](backend/docker.md#resources-and-lifecycle).

Read the table by task group. Image roles describe what must be prepared for the
selected tasks.

| Task group | Image roles | Additional execution requirements |
|---|---|---|
| Theorem, construction and open | Development and separate verifier | Harbor support images and the resources declared by the task |
| Offline Solver | Development, verifier controller and judge worker | Controller access to the Docker socket and a read-only cgroup view |
| Online Solver | Development and backend judge worker | Running backend, service credentials and an address reachable from development and judge containers |

Both Solver paths require enabled Landlock ABI 3 or later, permitted Landlock
syscalls and root supervision inside judge containers. Builds and solver commands
run with restricted privileges. The [isolation preflight](judge-execution-isolation.md)
checks the actual prepared image on the execution host. If it fails, correct
the host policy or use a supported host before starting an evaluation.

## Prepare and check

For the default Lite selection:

```bash
tcsexam source-inputs
tcsexam build --suite lite
tcsexam doctor --suite lite --output build/lite-readiness.json
```

`build` prepares task images and matching Harbor host-support images. Fixed
inputs and their acquisition commands are documented in
[resource preparation](resources.md). For externally prepared images, supply a
complete manifest with `--artifacts`; its records must identify the actual
images and Harbor support products.

`doctor` writes the selected prerequisites and `blockers` to its JSON report.
Resolve blockers before `run`. The agent check validates configuration and local
credential presence without contacting the model endpoint. Online service
configuration and connectivity checks are described in the
[backend guide](backend/docker.md#check-and-start).

## Verification and results

Lean verifiers use fixed project and dependency configuration. Theorem and
construction tasks accept `Task/Basic.lean`; open tasks also accept the
additional Lean sources documented by their task. Submitted build configuration,
dependency directories, compiled files and scoring scripts are ignored.
Symbolic links in submitted source paths are rejected.

Final Lean sources must use ordinary definitions and proofs. Commands that run
custom metaprograms or change elaboration, such as `run_cmd`, `run_tac`, `elab`,
`macro`, `initialize` and `#eval`, are rejected in every submitted source file.
The verifier checks fully qualified axiom names. Construction tasks retain their
documented `native_decide` support; its generated Boolean equalities are checked
by evaluating them before acceptance. An open task submission that passes both
the conjecture and its negation receives zero.

Solver hidden inputs are provided only to judging. The model development
container has neither those inputs nor the Docker socket. Online archive
credentials are restricted to final verification; see
[running Online Solver](running.md#online-solver).

A successful scorer publishes a finite Harbor reward. Detailed task reports,
such as `score-details.json` or `judge_result.json`, explain the result. When
judging fails, investigate the verifier logs and exception before assigning a
score. Use [result inspection](running.md#keep-outputs-and-statuses) to locate
these files and retain completed zero scores separately from execution failures.
