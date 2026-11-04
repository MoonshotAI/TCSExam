# Solver protocols

[English](solver-protocols.md) | [简体中文](solver-protocols.zh-CN.md)

This guide defines Solver feedback during development and protocol selection.
It is for users choosing an evaluation protocol or preparing its dependencies.

## Feedback and defaults

Full contains 100 tasks; Lite selects 20 from across Full's task categories. In either suite,
`--solver-protocol online|offline` chooses the Solver development-feedback
protocol. Theorem, construction and open-conjecture tasks share the same folders
under both choices. Full defaults to `online`; Lite defaults to `offline`.
Either suite accepts an explicit override.

Read each row as one complete development and final-judging protocol.

| Protocol | During the twelve-hour development period | After development |
|---|---|---|
| `online` | `submit.sh` can request judging and return feedback | Judge the final submission on hidden instances |
| `offline` | Run local self-tests on public instances | Judge the final submission on hidden instances |

Offline provides no hidden-judge feedback during development. Both protocols
use the same final task checker and scoring rules.

Internet access is a separate task setting: follow the task configuration and
instructions for allowed network use.

## Select and prepare a protocol

All thirty Solver tasks have online and offline packages. The
[task registry](../suites/tasks.json) maps tasks to their existing Harbor
directories. Suite selection and protocol selection resolve these directories
without changing task content.

```bash
tcsexam list --suite lite --track solver --solver-protocol offline
tcsexam list --suite full --track solver --solver-protocol online
```

Prepare the selected images with [`tcsexam build`](resources.md), then run
`tcsexam doctor` with the same selection. Missing dependencies stop `run` before
any model request; a missing variant is an error.

Online additionally requires a user-operated judging backend. The packages
supply clients and judging code; the [TCSEXAM interface](solver-backend.md)
defines authentication, sessions, attempt identity and result archives.

Offline uses a separate judging adapter after development. It selects
parallelism from available CPU and memory, with a serial fallback, while
preserving per-instance limits. Shared-time-pool tasks remain in one pool. The
model environment is isolated from hidden data and the Docker controller. See
[offline adapters](offline-adapters.md) for adapter behavior.

## Report the selected protocol

Keep online and offline results in separate series, including when they select
the same tasks. Record the actual protocol with the suite, source commit, model
and agent versions, scoring reference and adopted attempt count. See the
[reporting fields](citation.md#citing-results).
