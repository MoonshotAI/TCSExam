"""Local-process platform adapter (``adapter: local-test``).

**For tests and local verification only — not a production adapter.** It
provides no isolation: "workers" are temp directories on the service
machine, and the uploaded judge_session_agent runs as a LOCAL process
dialing the service tunnel like a real one. The judge worker it relays to
must already listen on the configured judge port (a local test config sets
``command: ""`` so the agent does not try to start one itself), e.g. the
synthetic worker from :mod:`tcsexam.backend.testing.synthetic_worker`.

Deterministic failure injection: ``fail_app_suffix`` (constructor argument,
defaulting to the ``TCSEXAM_LOCAL_TEST_FAIL_APP_SUFFIX`` environment
variable) names an app-name suffix whose shard's agent is never launched
(file uploads and the agent_config.json write run normally, so the failure
lands in the tunnel wait exactly like a wedged in-worker agent would). The
app name is derived from the shard index, so shard-level retries hit the
same suffix again — a deterministic "one shard fails to boot" injection
for sharded-session failure tests.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ..adapter import WorkerResources

LOGGER = logging.getLogger("tcsexam.backend.testing.local_adapter")

#: Environment variable naming the app-name suffix whose agent is never
#: launched (deterministic shard-boot failure injection; see module docstring).
FAIL_APP_SUFFIX_ENV = "TCSEXAM_LOCAL_TEST_FAIL_APP_SUFFIX"
_DELETE_TIMEOUT_SECONDS = 5.0


def _process_status(pid: int) -> tuple[str, str] | None:
    """Return Linux state and start time, keeping reused PIDs distinct."""
    try:
        # comm may contain spaces or ')'; fields after its final ')' begin
        # at state (field 3), with starttime (field 22) at offset 19.
        fields = Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return fields[0], fields[19]


class _LocalCtrl:
    """Minimal ctrl shim: file ops land in a local dir, run() is a subprocess."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _resolve(self, path: str) -> Path:
        # The agent's work dir is absolute in-worker; map it under the root.
        return self.root / path.lstrip("/")

    async def write_bytes(self, path: str, data: bytes, parents: bool = False) -> None:
        dest = self._resolve(path)
        if parents:
            dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    async def read_text(self, path: str) -> str:
        return self._resolve(path).read_text(errors="replace")

    async def run(self, cmd: str, shell: bool = False, text: bool = False, timeout: float = 30, env: dict | None = None) -> Any:
        work_dir = self._resolve(self._work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        # Commands are written for the in-worker absolute layout (cd
        # /tcsexam-backend && ...); rewrite the work-dir path to this
        # adapter's local mirror.
        cmd = cmd.replace(self._work_dir, str(work_dir))
        proc = subprocess.run(
            cmd, shell=shell, cwd=work_dir, timeout=timeout,
            capture_output=True, text=text, env=env,
        )
        return proc

    _work_dir: str = ""  # set by LocalWorker


class _GatedCtrl(_LocalCtrl):
    """Skips launching the session agent for shards whose app_name ends
    with the injected suffix (the rest of the boot — file uploads, the
    agent_config.json write — runs normally, so the failure lands in the
    tunnel wait exactly like a wedged in-worker agent would)."""

    fail_app_suffix: str = ""

    async def run(self, cmd, shell: bool = False, text: bool = False, timeout: float = 30, env: dict | None = None):
        if self.fail_app_suffix and "judge_session_agent.py" in cmd:
            try:
                cfg = json.loads(
                    (self.root / self._work_dir.lstrip("/") / "agent_config.json").read_text()
                )
                app_name = str(cfg.get("app_name") or "")
            except Exception:  # noqa: BLE001 - config unreadable: don't gate
                app_name = ""
            if app_name.endswith(self.fail_app_suffix):
                return subprocess.CompletedProcess(cmd, 0, "", "")
        return await super().run(cmd, shell=shell, text=text, timeout=timeout, env=env)


class LocalWorker:
    """A fake worker: ctrl writes/runs locally; delete() kills its processes."""

    _counter = 0

    def __init__(self, work_dir: str, *, fail_app_suffix: str = "") -> None:
        LocalWorker._counter += 1
        self.id = f"local-{LocalWorker._counter}"
        self.name = self.id
        self.root = Path(tempfile.mkdtemp(prefix="tcsexam-local-worker-"))
        self.ctrl = _GatedCtrl(self.root)
        self.ctrl._work_dir = work_dir
        self.ctrl.fail_app_suffix = fail_app_suffix
        self.work_dir = work_dir

    async def delete(self) -> None:
        # Kill the detached agent (and anything it started): its cmdline is a
        # relative path, so match on /proc/*/cwd under this worker's root
        # instead of pkill -f. Sending SIGKILL does not itself wait for exit.
        root = str(self.root)
        targets = {}
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                cwd = os.readlink(f"/proc/{entry}/cwd")
            except OSError:
                continue
            if cwd == root or cwd.startswith(root + "/"):
                pid = int(entry)
                status = _process_status(pid)
                if status is None:
                    continue
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    continue
                targets[pid] = status[1]

        deadline = asyncio.get_running_loop().time() + _DELETE_TIMEOUT_SECONDS
        while targets:
            remaining = {}
            for pid, started in targets.items():
                status = _process_status(pid)
                # A zombie has already exited; its parent owns wait/reaping.
                # A new process reusing this PID is outside this deletion.
                if status is not None and status[1] == started and status[0] not in {"Z", "X"}:
                    remaining[pid] = started
            targets = remaining
            if not targets:
                break
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(f"Local worker processes did not exit: {sorted(targets)}")
            await asyncio.sleep(0.01)


class LocalProcessAdapter:
    """Local-mock backend: "workers" are temp dirs on this machine.

    Test-only double of the PlatformAdapter protocol (see the module
    docstring). The judge_session_agent uploaded into the fake worker runs
    as a local process and dials the service tunnel like a real one; the
    judge worker it relays to must already listen on the worker's judge
    port.
    """

    def __init__(self, config: Any, *, fail_app_suffix: str | None = None) -> None:
        self.config = config
        sessions_cfg = config.backend.judge_sessions
        self._sessions_cfg = sessions_cfg
        self.ready_timeout_seconds = float(config.backend.ready_timeout_seconds)
        self._fail_app_suffix = (
            os.environ.get(FAIL_APP_SUFFIX_ENV, "") if fail_app_suffix is None else fail_app_suffix
        )
        self._long_lived: dict[str, Any] = {}
        # Creation records behind long_lived_memory_mb: app name -> the
        # resources requested at create_sandbox time (the adapter does not
        # inherit the base class, so it keeps its own records — see the
        # adapter module docstring's accounting rule).
        self._long_lived_resources: dict[str, WorkerResources] = {}
        self._port_counter = 0  # per-worker judge ports for sharded mock sessions
        self._work_dir = sessions_cfg.work_dir

    async def create_sandbox(
        self,
        profile: str,
        image_url: str,
        *,
        ttl_seconds: float | None = None,
        spec: dict[str, int] | None = None,
        ready_timeout_seconds: float | None = None,
        group_name: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> Any:
        LOGGER.info("local worker created (image %s accepted, not executed)", image_url)
        worker = LocalWorker(self._work_dir, fail_app_suffix=self._fail_app_suffix)
        # The creation-time resources ride on the worker (the Worker
        # Protocol's optional metadata member) and are copied onto the
        # accounting table at register time. An absent spec falls back to
        # the configured default spec, mirroring the base class's
        # WorkerResources.from_spec(spec or default_spec).
        worker.resources = WorkerResources.from_spec(spec or self._sessions_cfg.spec)
        # Sharded mock sessions run one local judge worker per shard, each on
        # its own port; the session store reads ``judge_port`` off the worker
        # (real isolated workers don't carry it — they all use the configured
        # port, as each has its own localhost).
        self._port_counter += 1
        worker.judge_port = self._sessions_cfg.judge_port + self._port_counter - 1
        return worker

    # Historical alias; matches the adapter protocol's name pair.
    _create_sandbox = create_sandbox

    def register_long_lived(self, app_name: str, worker: Any) -> None:
        """Put a worker on the long-lived table (the adapter protocol)."""
        self._long_lived[app_name] = worker
        resources = getattr(worker, "resources", None)
        if not isinstance(resources, WorkerResources):
            # A foreign worker (no creation record of ours): fall back to
            # the configured default spec, same as a spec-less create.
            resources = WorkerResources.from_spec(self._sessions_cfg.spec)
        self._long_lived_resources[app_name] = resources

    def long_lived_count(self) -> int:
        """Registered long-lived workers (the store's global usage pre-check
        reads it)."""
        return len(self._long_lived)

    def long_lived_memory_mb(self) -> int:
        """Memory dimension of the same registry: the sum of the per-worker
        creation records (the requested spec, or the configured default
        spec for spec-less creates)."""
        return sum(int(r.memory_mb or 0) for r in self._long_lived_resources.values())

    async def stop_app(self, app_name: str) -> None:
        worker = self._long_lived.pop(app_name, None)
        self._long_lived_resources.pop(app_name, None)
        if worker is None:
            return
        try:
            text = await worker.ctrl.read_text(f"{self._work_dir}/agent.log")
            LOGGER.info("local agent.log tail for %s:\n%s", app_name, "\n".join(text.splitlines()[-50:]))
        except Exception:  # noqa: BLE001
            pass
        try:
            await worker.delete()
        except Exception:  # noqa: BLE001
            pass

    def sandbox_for_app(self, app_name: str) -> Any:
        return self._long_lived.get(app_name)
