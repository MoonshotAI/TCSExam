# Solver judge isolation

[English](judge-execution-isolation.md) | [简体中文](judge-execution-isolation.zh-CN.md)

This document describes process privileges, network access, filesystem writes, and cleanup in Solver judges.
It is intended for maintainers of Online and Offline judge images and backend services.

## Check the execution host

The judge requires Linux x86-64, root supervision, seccomp filters, and an enabled
Landlock ABI of at least 3, including truncate protection. The preflight checks
the image's user/group transitions and actual syscall policy. Worker
startup runs a bounded enforcement preflight before opening its HTTP listener;
Offline workers run the same check before judging. A failed check exits at startup
and is reported through the existing judge boot failure path. Resolve the reported requirement before retrying.

To check a prepared judge image on the actual Docker host, run:

```sh
docker run --rm --network none --entrypoint python3 JUDGE_IMAGE \
  /judge/process_supervisor.py preflight
```

Success prints JSON containing `ok`, `landlock_abi`, uid/gid, groups,
`network_denied`, and `descendant_network_denied`. The probe
actually drops privileges, installs a policy, writes an allowed output, and checks
that a world-writable protected sentinel cannot be changed. It also checks socket
denial in both the submission process and an executed child, while permitting
private Unix socket pairs. An unsupported kernel,
disabled Landlock LSM, denied syscall, or unavailable identity transition fails.
Changing the container's userspace does not add missing host kernel support.
Landlock must be enabled in both the kernel build and boot configuration; see the
[Linux kernel documentation](https://docs.kernel.org/userspace-api/landlock.html#kernel-support).
Container seccomp policies must permit the three Landlock syscalls. Run the
same preflight after changing the host or its security profile.

Run the preflight on the same host and image that will execute judging.
After it passes, use the normal task workflow to execute submissions.

## Privileges, file access and cleanup

All 30 Solver tasks share `assets/environments/solver/judge-runtime/execution.py`.
Online judges install it through `run_checker.py`; the common Offline worker and
task-specific Offline workers use the same boundary. The scoring layer defines
the instances, reference values, time limits and shared time pools.

Build and solve commands run as uid/gid 65534 with no supplementary groups.
Trusted validators and input preparation retain the checker identity. The adapter
classifies calls from the audited build/solve functions; an unclassified scoring
subprocess fails explicitly. `test_judge_execution.py` checks the scoring
implementations' subprocess classifications.

Untrusted commands use `no_new_privs` to prevent privilege gains through setuid
executables or file capabilities. Their environment contains a fixed executable
search path, workspace and temporary-directory settings, locale, numeric budgets,
and required output paths. The search path includes the trusted MiniZinc and graph
tool directories declared by the development images; arbitrary inherited PATH,
loader settings, Python search paths, and service credentials are excluded.

An inherited seccomp filter blocks socket creation and connection, listening,
and `io_uring` in build and solve processes. This covers Internet, loopback and
Unix-domain service sockets. Private Unix socket pairs, pipes, threads and child
processes remain available for local computation. The supervisor closes inherited
file descriptors apart from standard input, output and error before executing the
command. Filter installation failure stops the command.

The trusted worker service and its tunnel keep their network access to receive
submissions and return results. Harbor's development-container allowlist remains
configured separately; Online Docker workers are created by the backend adapter
and enforce submission network isolation through this shared runtime.

Landlock restricts filesystem writes to the build directory, `/app`, explicit
output files or directories, and a private temporary directory for each command.
An input sharing a directory with an output file remains protected. JSSP
uses a separate `out-<instance>` output directory; that directory is writable so
its documented temporary-file-and-rename output protocol continues to work.
The shipped QBF wrapper's explicit `mktemp /tmp/...` template is redirected into
its private TMPDIR. Other temporary writes should use TMPDIR or the workspace.

Submission archives reject symlinks, hard links, and special files. Builds may
create symlinks within the build directory as needed by compilation tools;
links escaping the build directory are removed before returning to the checker. Solve commands cannot
create symlinks, and trusted Python writes reject symlink traversal. A separate
compilation directory returns to root ownership with group/other write permission
removed before inputs can be materialized there.

Each submission and each untrusted command has its own Linux subreaper supervisor.
It cleans up descendants even after `setsid` or a double fork. A scorer's SIGTERM
is forwarded to the candidate process group and preserves the scorer's original
grace period. The scorer's subsequent SIGKILL uses a separate supervisor control
signal to request immediate descendant cleanup. Normal exits and exceptions also
clean up background descendants. Cleanup targets only this supervisor's children.

Cleanup has a five-second deadline. A failure writes a trusted execution-error
marker. The Online worker observes that marker while waiting, records a
`judge_error`, stops its queue, rejects new submissions, and returns an unhealthy
status. Its bounded shutdown wait does not permit reuse after an unresolved
cleanup. `/submissions` retains completed and failed records and reports the
worker error; the backend archives those records and invokes its existing failed
shard teardown, which stops the actual worker. Offline workers exit unsuccessfully
and their controller removes the container. Cleanup failures count as judging
infrastructure failures rather than candidate build failures or timeouts.
