"""Judge-session endpoints (``/v1/judge/sessions/*``): one throwaway worker
per session, created from the task's judge image, running the task's judge
server on localhost, reached from the task container through the reverse
tunnel.

    task client --HTTP-->  /v1/judge/sessions/{sid}/<path>  --frames-->
    tunnel  --HTTP-->  localhost:<judge_port> inside the judge worker

Endpoints:

* ``POST   /v1/judge/sessions``             — create a session from a judge image.
  **Asynchronous**: the response is ``202`` with the session registered as
  ``status: "provisioning"``; the worker creation + tunnel wait run as a
  background task flipping the session to ``ready`` or ``failed``.
  Poll ``GET /v1/judge/sessions/{sid}`` for the status. Synchronous failure
  contract preserved for everything that can fail at request time (400
  validation, 503 session cap).
* ``GET    /v1/judge/sessions``             — list sessions (live + recently
  destroyed); rows carry ``status``/``error``. Also the reconciliation
  query surface (``?client_ip=`` / ``?session_ids=``).
* ``GET    /v1/judge/sessions/{sid}``       — session status (incl. ``status``
  and ``error``).
* ``ALL    /v1/judge/sessions/{sid}/{tail}``— relay to the in-worker judge server
  (custom headers ride through untouched). A ``provisioning`` session answers
  503 transient (``judge session is still provisioning; please try again``).
* ``DELETE /v1/judge/sessions/{sid}``       — destroy (idempotent, always 200);
  destroys a provisioning session too (cancels its background creation and
  recycles the worker).

Lifecycle rules: creation goes through the adapter's retry-with-backoff, and
every created worker is destroyed on exactly one path — an explicit DELETE,
the TTL/idle reaper, a tunnel drop (after the reconnect grace), service
shutdown, or a failed/cancelled creation (the provision task recycles the
worker itself).

Creation is singleflighted on caller identity and the complete creation request
(:meth:`JudgeSessionStore.begin_create`): concurrent same-key requests are
all immediately registered against one shared creation instead of churning
one worker per client retry. Sharing REQUIRES the explicit
``X-TCSEXAM-Client-Id`` header — without it every create gets its own
session (a shared-egress IP must never merge unrelated runs into one
provisioning session).

Caller identity: the run-id validated by the auth middleware
(``request["run_id"]``) is stored on the session, surfaced by the session
status endpoint and the ``/v1/status`` callers table, and stamped onto the
worker as creation tags — ``labels = {run_id, token_id}`` and, when
``config.worker_group`` is set, ``group_name = "<worker_group>--<run-id
slug>"`` so the platform can clean up one attempt's workers precisely.
Sessions created without a run-id carry no labels and no group_name.

Error classification returned to the caller (the task-side client maps these
onto its retry policy): ``transient`` (session cap reached / worker pool
full / platform flap — retry with backoff), ``infra_error`` (service-side
fault), ``judge_error`` (surfaced by the in-worker judge server, relayed
untouched).

The store drives the adapter through the small public protocol defined in
``tcsexam.backend.adapter`` (``create_sandbox`` / ``register_long_lived`` /
``stop_app``) — never through private members.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import re
import secrets
import shlex
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from aiohttp import web

from .agent_files import agent_file_path
from .auth import ATTR_AGENT_NAME
from .config import (
    BaseServiceConfig,
    JudgeSessionsConfig,
    read_exempt_identities_file,
)
from .errors import (
    PROVISIONING_MESSAGE,
    TRANSIENT_HINT as _TRANSIENT_HINT,
    is_transient_platform_error as _is_transient_platform_error,
    transient_suffix,
)
from .status import image_family

LOGGER = logging.getLogger("tcsexam.backend.sessions_base")

#: The in-worker agent bundle uploaded to every session worker: the flat
#: agent files (they import each other by bare top-level name inside the
#: worker). Read as bytes; never imported from here.
_JUDGE_SESSION_AGENT_PY = agent_file_path("judge_session_agent.py")
_SANDBOX_AGENT_PY = agent_file_path("sandbox_agent.py")
_TUNNEL_PROTOCOL_PY = agent_file_path("tunnel_protocol.py")

# Boot fail-fast: the in-worker agent writes a "BOOT-FATAL: ..." line to
# agent.log when the judge server dies during boot or reports the terminal
# {"status": "error"} health state. While waiting for the tunnel, _provision
# polls agent.log in slices and fails the session within seconds of the
# sentinel appearing — a broken judge image no longer burns the whole ready
# budget.
_BOOT_FATAL_SENTINEL = "BOOT-FATAL:"
_AGENT_LOG_POLL_SECONDS = 15.0

#: Accepted resources keys -> worker spec keys (the contract says
#: ``resources{cpu,mem}``; the task-side client sends
#: cpu/memory_mb/storage_mb).
_RESOURCE_KEYS = {
    "cpu": "cpu_count",
    "cpu_count": "cpu_count",
    "mem": "memory_mb",
    "memory_mb": "memory_mb",
    "storage_mb": "storage_mb",
}


class SessionsFullError(Exception):
    """The global session cap is reached — a transient condition by contract."""


class JudgeBootError(RuntimeError):
    """The in-worker judge server failed during boot (process exited early
    or reported the terminal ``{"status": "error"}`` health state). Named in
    ``NON_TRANSIENT_ERROR_NAMES``: the judge image is broken and a retry
    recreates the same failure. Subclasses RuntimeError so
    ``except RuntimeError`` callers keep working."""


#: Retention for the session list endpoint: the most recent destroyed
#: sessions are kept for attribution; the list itself caps at 200 rows.
DESTROYED_SESSIONS_KEEP = 100
SESSION_LIST_LIMIT = 200


#: Slug rules for the group_name run-id suffix: every character outside
#: [a-zA-Z0-9-_] becomes "-", truncated to 40 chars.
_SLUG_UNSAFE = re.compile(r"[^a-zA-Z0-9\-_]")
_RUN_ID_SLUG_MAX = 40


def run_id_slug(run_id: str) -> str:
    """Group-name-safe form of a run-id (see the module docstring)."""
    return _SLUG_UNSAFE.sub("-", run_id)[:_RUN_ID_SLUG_MAX]


@dataclass
class JudgeSession:
    """A live judge session: one worker + one reverse tunnel."""

    session_id: str
    app_name: str  # tunnel app name
    image: str
    created: float
    last_active: float  # relay activity; idleness is measured from this
    expires: float  # created + ttl
    destroyed: bool = False
    # Caller identity: run-id from the validated X-TCSEXAM-Run-Id header
    # ("" when the caller sent none) and the auth token id ("-" when absent).
    run_id: str = ""
    token_id: str = ""
    # Attribution attrs: the auth middleware's synthesized dict
    # (TCSEXAM_RUN_ID / TCSEXAM_CLIENT_ID / TCSEXAM_AGENT_NAME).
    attrs: dict[str, str] = field(default_factory=dict)
    # Lifecycle: per-session idle-reap threshold, routed by image family at
    # create time. 0 = unset.
    idle_ttl_seconds: float = 0.0
    # Async creation state: "provisioning" (registered, the background
    # provision task is still booting the worker / waiting for the tunnel),
    # "ready" (tunnel connected, judge traffic flows), "failed" (creation
    # failed; ``error`` carries the wire-contract wording). Default "ready"
    # so sessions hand-built outside the store (tests) count as live.
    status: str = "ready"
    error: str = ""  # failure wording when status == "failed", else ""
    # Tunnel reconnect grace: timestamp of the moment the store claimed this
    # session's tunnel drop; 0 = tunnel up (or never dropped). The reaper
    # only destroys a tunnel-down ready session after
    # ``tunnel_reconnect_grace_seconds`` — within the window the worker is
    # kept so the agent can redial and resume.
    tunnel_down_at: float = 0.0
    # Creator identity: the proxy-attested identity (XFF first ?? remote) of
    # the request that created this session. Informational; the submission
    # cap counts SUBMISSION identities, not this.
    identity: str = ""

    @property
    def agent_name(self) -> str:
        """Caller-declared agent name ("" when not forwarded)."""
        return self.attrs.get(ATTR_AGENT_NAME) or ""


class JudgeSessionStore:
    """In-memory table of live judge sessions plus their reaper.

    In-memory by design: a service restart loses the table, and the workers'
    platform-side TTL reaps the orphans.
    """

    def __init__(
        self,
        executor: Any,
        config: JudgeSessionsConfig,
        service_config: BaseServiceConfig,
        *,
        journal: Any = None,
    ) -> None:
        self._executor = executor
        self._service_config = service_config
        self.cfg: JudgeSessionsConfig = config
        self._tunnels: Any = None  # set via attach_tunnels (built after us)
        # Session journal: append-only ledger for lifecycle events and
        # accepted submissions (cap counter + reconciliation query). None in
        # tests: events are skipped.
        self._journal = journal
        self._sessions: dict[str, JudgeSession] = {}
        # Recently destroyed sessions, kept for the list endpoint.
        self._destroyed: deque[JudgeSession] = deque(maxlen=DESTROYED_SESSIONS_KEEP)
        # Identity plus normalized creation parameters -> provisioning
        # session. Emptied as creations settle.
        self._inflight: dict[tuple, JudgeSession] = {}
        # Background provision tasks of registered sessions, keyed by sid;
        # popped on destroy. A completed task stays referenced so a late
        # waiter still observes its outcome.
        self._provision_tasks: dict[str, asyncio.Task] = {}
        self._reaper_task: asyncio.Task | None = None

    def attach_tunnels(self, tunnels: Any) -> None:
        self._tunnels = tunnels

    def claim_tunnel_close(self, app_name: str) -> bool:
        """Claim a tunnel drop for the reconnect grace.

        Returns True when the app is one of this store's live ready sessions:
        the caller must then NOT tear anything down — the reaper destroys the
        session (and its worker) only after
        ``tunnel_reconnect_grace_seconds``, so the in-worker agent can redial
        and resume. Unknown apps and non-ready sessions return False
        (the immediate-teardown path).
        """
        session = self._sessions.get(app_name)
        if session is None or session.destroyed or session.status != "ready":
            return False
        if not session.tunnel_down_at:
            session.tunnel_down_at = time.time()
            LOGGER.info(
                "judge session %s tunnel down; holding the worker for a %.0fs reconnect grace",
                app_name,
                self.cfg.tunnel_reconnect_grace_seconds,
            )
        return True

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start_reaper(self) -> None:
        """Start the TTL/idle-reaper loop (called on app startup)."""
        self._reaper_task = asyncio.create_task(self._reap_loop())

    async def shutdown(self) -> None:
        """Service shutdown: stop the reaper and destroy every session."""
        if self._reaper_task is not None:
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                pass
            self._reaper_task = None
        for sid in list(self._sessions):
            await self.destroy(sid)

    def _creation_key(
        self,
        key: tuple,
        image: str,
        payload_files: dict[str, bytes] | None,
        resources: dict[str, int] | None,
        ttl_seconds: float | None,
        *,
        run_id: str,
        token_id: str,
        default_ttl: float,
    ) -> tuple:
        """Only identical effective requests can share worker creation.

        Hash file contents rather than retaining another copy of uploads in
        the key. Sorted file paths and resource keys make ordering irrelevant.
        Explicit default resources/TTL match their omitted equivalents.
        """
        files = [
            (path, hashlib.sha256(content).hexdigest())
            for path, content in sorted((payload_files or {}).items())
        ]
        payload_digest = hashlib.sha256(
            json.dumps(files, ensure_ascii=True, separators=(",", ":")).encode()
        ).hexdigest()
        spec = {**self.cfg.spec, **(resources or {})}
        ttl = max(60.0, min(ttl_seconds or default_ttl, self.cfg.max_ttl_seconds))
        return (*key, token_id, run_id, image, payload_digest,
                tuple(sorted(spec.items())), ttl)

    def begin_create(
        self,
        key: tuple | None,
        image: str,
        payload_files: dict[str, bytes] | None,
        resources: dict[str, int] | None,
        ttl_seconds: float | None,
        *,
        run_id: str = "",
        token_id: str = "",
        attrs: dict[str, str] | None = None,
        identity: str = "",
    ) -> JudgeSession:
        """Register a provisioning session and kick off its creation in the
        background (async creation). Returns immediately.

        The session lands in :attr:`_sessions` with ``status="provisioning"``
        before this returns; a background task (:meth:`_provision`) runs the
        worker creation + tunnel wait and flips the session to ``ready`` or
        ``failed`` (with the wire-contract error wording in ``session.error``).

        Singleflight: with ``cfg.singleflight`` and a ``key``, a concurrent
        same-key call returns the already-registered provisioning session —
        every caller gets the same session_id instantly, no waiting. The key
        settles out of :attr:`_inflight` when the creation finishes (success
        or failure), so a later same-key create starts a brand-new session
        (the legitimate rebuild path). ``key=None`` never shares.

        Synchronous failures: the session cap raises
        :class:`SessionsFullError` (HTTP 503 transient), a missing adapter
        raises ``RuntimeError`` (HTTP 500) — both before any registration.
        Platform failures surface asynchronously via
        ``session.status == "failed"``.

        ``run_id`` / ``token_id`` additionally isolate callers in the
        effective sharing key, alongside uploaded contents, resources and
        lifetime. ``attrs`` only labels the session; the leader's labels
        are retained when identical requests share creation.
        """
        if key is not None and self.cfg.singleflight:
            key = self._creation_key(
                key, image, payload_files, resources, ttl_seconds,
                run_id=run_id, token_id=token_id,
                default_ttl=self.cfg.resolve_lifecycle(image)[1],
            )
            shared = self._inflight.get(key)
            if shared is not None:
                LOGGER.info(
                    "judge session create shares provisioning session for key %s (image %s)",
                    key[:1], image,
                )
                return shared
        session, task = self._register(
            image, payload_files, resources, ttl_seconds,
            run_id=run_id, token_id=token_id, attrs=attrs, identity=identity,
        )
        if key is not None and self.cfg.singleflight:
            self._inflight[key] = session

            def _settle(done: asyncio.Task, key=key, session=session) -> None:
                if self._inflight.get(key) is session:
                    self._inflight.pop(key, None)
                if not done.cancelled():
                    # HTTP-path leaders have no waiter: mark the outcome
                    # retrieved (shield waiters still receive it).
                    done.exception()

            task.add_done_callback(_settle)
            LOGGER.info("judge session create leader for key %s (image %s)", key[:1], image)
        return session

    def _register(
        self,
        image: str,
        payload_files: dict[str, bytes] | None,
        resources: dict[str, int] | None,
        ttl_seconds: float | None,
        *,
        run_id: str = "",
        token_id: str = "",
        attrs: dict[str, str] | None = None,
        identity: str = "",
    ) -> tuple[JudgeSession, asyncio.Task]:
        """Allocate and register the provisioning session, spawn its creation
        task. The cap check runs here, synchronously, before registration."""
        live = sum(
            1
            for s in self._sessions.values()
            if not s.destroyed and s.status != "failed"
        )
        if live >= self.cfg.max_sessions:
            raise SessionsFullError(
                f"judge session cap reached ({self.cfg.max_sessions}); {_TRANSIENT_HINT}"
            )
        creator = getattr(self._executor, "create_sandbox", None)
        if creator is None:
            raise RuntimeError("judge sessions require a platform adapter")

        # Per-image-family readiness + lifecycle budgets; no route -> the
        # section defaults everywhere. Resolved here so the 202 body already
        # carries the final expires_at.
        ready_timeout, create_ready_timeout = self.cfg.resolve_readiness(image)
        idle_ttl, route_ttl = self.cfg.resolve_lifecycle(image)
        ttl = ttl_seconds if ttl_seconds else route_ttl
        ttl = max(60.0, min(ttl, self.cfg.max_ttl_seconds))
        spec = {**self.cfg.spec, **(resources or {})}

        now = time.time()
        session_id = "jsess-" + uuid.uuid4().hex[:12]
        session = JudgeSession(
            session_id=session_id,
            app_name=session_id,  # tunnel app name == session id
            image=image,
            created=now,
            last_active=now,
            expires=now + ttl,
            run_id=run_id,
            token_id=token_id,
            attrs=dict(attrs or {}),
            idle_ttl_seconds=idle_ttl,
            status="provisioning",
            identity=identity,
        )
        self._sessions[session_id] = session
        if self._journal is not None:
            self._journal.record_register(
                session_id, image, image_family(image), identity, created=now
            )

        # Janitor: wall-clock deadline for the WHOLE provisioning flow, not
        # just the tunnel wait. Ready timeout (wait_connected) only bounds
        # the last stage; a create the platform never answers or a judge that
        # wedges pre-tunnel would otherwise leave the task — and its
        # singleflight key — hanging forever.
        create_budget = (
            create_ready_timeout
            if create_ready_timeout is not None
            else float(getattr(self._executor, "ready_timeout_seconds", 2400.0))
        )
        provision_deadline = (
            create_budget + ready_timeout + self.cfg.provision_janitor_margin_seconds
        )

        async def _provision_with_deadline() -> None:
            try:
                await asyncio.wait_for(
                    self._provision(
                        session, image, payload_files, spec, ttl,
                        ready_timeout, create_ready_timeout,
                    ),
                    timeout=provision_deadline,
                )
            except asyncio.TimeoutError:
                # wait_for cancels _provision; its CancelledError path already
                # recycles the worker. Here we settle the session state.
                if not session.destroyed and session.status == "provisioning":
                    session.status = "failed"
                    session.error = (
                        "judge session create failed: RuntimeError: "
                        f"provisioning deadline exceeded ({provision_deadline:.0f}s)"
                        f" (transient platform error, {_TRANSIENT_HINT})"
                    )
                LOGGER.warning(
                    "provisioning janitor: judge session %s marked failed after "
                    "%.0fs (image %s)",
                    session.session_id, provision_deadline, image,
                )
                raise RuntimeError(
                    f"provisioning deadline exceeded ({provision_deadline:.0f}s)"
                )

        task = asyncio.create_task(_provision_with_deadline())
        self._provision_tasks[session_id] = task
        return session, task

    async def _wait_provision(self, session: JudgeSession) -> JudgeSession:
        """Await the background creation of a registered session; returns the
        session once ``ready``. The provision task's own exception propagates
        unchanged (same object for every concurrent waiter). This is the
        synchronous semantics for store-level callers; the HTTP layer does
        not use it (202 + polling instead)."""
        task = self._provision_tasks.get(session.session_id)
        if task is not None:
            await asyncio.shield(task)
        if session.status == "failed":
            raise RuntimeError(session.error)
        return session

    async def _wait_tunnel_or_boot_failure(self, session: JudgeSession, ctrl: Any, ready_timeout: float) -> bool:
        """Wait for the session agent's tunnel in slices (``wait_connected``
        semantics unchanged); between slices scan the in-worker agent.log for
        the ``BOOT-FATAL:`` sentinel and raise with the judge's own error
        wording when it appears. Log reads share the remaining deadline and
        race a tunnel waiter so diagnostics cannot block a connected worker.
        Returns False when the budget runs out (the caller keeps its generic
        timeout wording for that path).
        """
        deadline = time.monotonic() + ready_timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            connected = await self._tunnels.wait_connected(
                session.app_name, min(_AGENT_LOG_POLL_SECONDS, remaining)
            )
            if connected:
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            log_read = asyncio.create_task(
                ctrl.read_text(f"{self.cfg.work_dir}/agent.log")
            )
            tunnel_wait = asyncio.create_task(
                self._tunnels.wait_connected(session.app_name, remaining)
            )
            try:
                done, _ = await asyncio.wait(
                    {log_read, tunnel_wait},
                    timeout=min(_AGENT_LOG_POLL_SECONDS, remaining),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if tunnel_wait in done and tunnel_wait.result():
                    return True
                if log_read not in done:
                    continue
                tail = log_read.result()[-1500:]
            except Exception:  # noqa: BLE001 - best-effort polling
                continue
            finally:
                for task in (log_read, tunnel_wait):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(log_read, tunnel_wait, return_exceptions=True)
            fatal = [line for line in tail.splitlines() if _BOOT_FATAL_SENTINEL in line]
            if fatal:
                reason = fatal[-1].split(_BOOT_FATAL_SENTINEL, 1)[1].strip()
                raise JudgeBootError(f"judge server failed during boot: {reason}")
            # wait_connected normally blocks for the whole slice; pace the
            # loop anyway so a fast-refusing tunnel cannot hot-spin the poll.
            await asyncio.sleep(min(1.0, max(0.0, deadline - time.monotonic())))

    async def _launch_agent_and_wait(
        self, session: JudgeSession, ctrl: Any, cmd: str, ready_timeout: float
    ) -> bool:
        """Wait for the agent independently of its detached launcher's exit.

        A control transport can miss the short-lived shell's exit message
        while the launched agent is healthy. The authenticated agent tunnel
        is sufficient to finish boot; do not make its readiness depend on
        that separate process notification. Both calls are cleaned up on
        readiness, timeout, boot failure, or cancellation.
        """
        launch = asyncio.create_task(ctrl.run(cmd, shell=True, text=True, timeout=30))
        readiness = asyncio.create_task(
            self._wait_tunnel_or_boot_failure(session, ctrl, ready_timeout)
        )
        try:
            done, _ = await asyncio.wait(
                {launch, readiness}, return_when=asyncio.FIRST_COMPLETED
            )
            if readiness in done:
                return readiness.result()
            # Preserve an actual launch failure when readiness has not
            # succeeded. A normal shell exit still waits for the agent.
            launch.result()
            return await readiness
        finally:
            for task in (launch, readiness):
                if not task.done():
                    task.cancel()
            await asyncio.gather(launch, readiness, return_exceptions=True)

    async def _provision(
        self,
        session: JudgeSession,
        image: str,
        payload_files: dict[str, bytes] | None,
        spec: dict[str, int],
        ttl: float,
        ready_timeout: float,
        create_ready_timeout: float | None,
    ) -> None:
        """The background half of session creation: boot the judge worker,
        upload the agent bundle, start the agent, wait for the tunnel, then
        flip the pre-registered session to ``ready``. On failure recycle the
        worker and flip the session to ``failed`` with the wire-contract
        error wording (:func:`_create_failure_message`); the original
        exception is re-raised so singleflight waiters observe it unchanged.
        On cancellation (DELETE mid-provisioning) recycle the worker and
        leave the destroyed session's state untouched.
        """
        sandbox = None
        try:
            create_kwargs: dict[str, Any] = {}
            if create_ready_timeout is not None:
                create_kwargs["ready_timeout_seconds"] = create_ready_timeout
            if session.run_id:
                # Worker tagging: labels for platform-side lookup, and a
                # per-run group_name so the platform can reap exactly one
                # attempt's workers. Without a configured worker_group the
                # group tag is skipped but labels still ride.
                create_kwargs["labels"] = {
                    "run_id": session.run_id,
                    "token_id": session.token_id or "-",
                }
                worker_group = getattr(self._service_config, "worker_group", "") or ""
                if worker_group:
                    create_kwargs["group_name"] = (
                        f"{worker_group}--{run_id_slug(session.run_id)}"
                    )
            creator = getattr(self._executor, "create_sandbox")
            sandbox = await creator(
                self.cfg.profile, image, ttl_seconds=ttl, spec=spec, **create_kwargs
            )
            ctrl = sandbox.ctrl
            await ctrl.write_bytes(
                f"{self.cfg.work_dir}/judge_session_agent.py", _JUDGE_SESSION_AGENT_PY.read_bytes(), parents=True
            )
            await ctrl.write_bytes(
                f"{self.cfg.work_dir}/sandbox_agent.py", _SANDBOX_AGENT_PY.read_bytes(), parents=True
            )
            await ctrl.write_bytes(
                f"{self.cfg.work_dir}/tunnel_protocol.py", _TUNNEL_PROTOCOL_PY.read_bytes(), parents=True
            )
            base = self._service_config.public_url()
            ws_scheme = "wss" if base.startswith("https") else "ws"
            ws_url = f"{ws_scheme}://{base.split('://', 1)[1]}/v1/tunnel/{session.app_name}"
            agent_config = {
                "app_name": session.app_name,
                "run_id": session.run_id,
                "agent_name": session.agent_name,
                "service_ws_url": ws_url,
                "token_id": self._service_config.token_id or "",
                "token_secret": self._service_config.token_secret or "",
                "port": self.cfg.judge_port,
                "command": self.cfg.command,
                "health_path": self.cfg.health_path,
                **self.cfg.agent_timeouts(ready_timeout),
                "ready_label": self.cfg.ready_label,
                "payload_files": {
                    path: base64.b64encode(data).decode()
                    for path, data in (payload_files or {}).items()
                },
            }
            await ctrl.write_bytes(
                f"{self.cfg.work_dir}/agent_config.json",
                json.dumps(agent_config).encode(),
                parents=True,
            )
            # plain python3: the session agent is stdlib-only, no
            # interpreter-version constraint applies. Detached: setsid +
            # background + logfile, so no control-channel exec session is
            # held for the worker's whole lifetime.
            cmd = (
                f"cd {shlex.quote(self.cfg.work_dir)} && "
                f"setsid python3 judge_session_agent.py >> agent.log 2>&1 < /dev/null &"
            )
            connected = await self._launch_agent_and_wait(session, ctrl, cmd, ready_timeout)
            if not connected:
                try:
                    tail = (await asyncio.wait_for(
                        ctrl.read_text(f"{self.cfg.work_dir}/agent.log"),
                        timeout=min(5.0, ready_timeout),
                    ))[-1500:]
                except Exception:  # noqa: BLE001
                    tail = "<no agent.log>"
                raise RuntimeError(
                    f"the judge session agent did not connect within "
                    f"{ready_timeout:g}s: {tail}"
                )
        except asyncio.CancelledError:
            # DELETE mid-provisioning: recycle the worker (best-effort; the
            # delete itself is shielded from the second cancel), never rewrite
            # the destroyed session's state.
            if sandbox is not None:
                try:
                    await asyncio.shield(sandbox.delete())
                except Exception:  # noqa: BLE001 - best-effort teardown
                    LOGGER.warning(
                        "failed to recycle worker of cancelled session %s",
                        session.session_id, exc_info=True,
                    )
            raise
        except Exception as exc:
            if sandbox is not None:
                try:
                    await sandbox.delete()
                except Exception:  # noqa: BLE001
                    pass
            if not session.destroyed:
                session.status = "failed"
                session.error = _create_failure_message(exc)
                session.last_active = time.time()
                if self._journal is not None:
                    self._journal.record_status(session.session_id, "failed", session.error)
            raise

        if session.destroyed:
            # Deleted while provisioning: recycle the worker instead of
            # registering it anywhere.
            try:
                await sandbox.delete()
            except Exception:  # noqa: BLE001
                pass
            return
        session.status = "ready"
        session.last_active = time.time()
        if self._journal is not None:
            self._journal.record_status(session.session_id, "ready")
        # The adapter's long-lived table: the tunnel-close reaper reaps the
        # worker through stop_app when the tunnel drops.
        self._executor.register_long_lived(session.app_name, sandbox)
        if self.cfg.gate_session_tokens:
            # Gate the auth-exempt /apps/<app> relay with a token nobody gets:
            # session traffic goes through /v1/judge/sessions/* (service auth).
            self._tunnels.session_tokens[session.app_name] = secrets.token_hex(16)
        LOGGER.info(
            "judge session %s ready (image %s, ttl %gs, run_id %s)",
            session.session_id,
            image,
            ttl,
            session.run_id or "-",
        )

    async def create_shared(
        self,
        key: tuple[str, str, str],
        image: str,
        payload_files: dict[str, bytes] | None,
        resources: dict[str, int] | None,
        ttl_seconds: float | None,
        *,
        run_id: str = "",
        token_id: str = "",
        attrs: dict[str, str] | None = None,
    ) -> JudgeSession:
        """Singleflight wrapper around the async creation: one shared
        provisioning session per key; this awaits its outcome and returns the
        ready session (the original exception on failure). Retained for
        store-level callers; the HTTP layer uses :meth:`begin_create`
        directly (202 + polling).

        Success: every waiter receives the same session (same session_id /
        base_url). Failure: every waiter receives the same exception object,
        so the error mapping is identical for all of them; the key settles
        out of the table, so the caller's next retry naturally becomes a
        fresh leader. A waiter's own cancellation never cancels the shared
        work (``asyncio.shield``), and neither does the leader's.

        ``cfg.singleflight = False`` degrades to the per-request
        :meth:`create`.
        """
        if not self.cfg.singleflight:
            return await self.create(
                image, payload_files, resources, ttl_seconds,
                run_id=run_id, token_id=token_id, attrs=attrs,
            )
        session = self.begin_create(
            key, image, payload_files, resources, ttl_seconds,
            run_id=run_id, token_id=token_id, attrs=attrs,
        )
        return await self._wait_provision(session)

    async def create(
        self,
        image: str,
        payload_files: dict[str, bytes] | None,
        resources: dict[str, int] | None,
        ttl_seconds: float | None,
        *,
        run_id: str = "",
        token_id: str = "",
        attrs: dict[str, str] | None = None,
    ) -> JudgeSession:
        """Boot a judge worker for one session and wait for its tunnel —
        the synchronous semantics, layered on the async machinery: register
        a provisioning session, await its background creation, return the
        ready session (raise on failure).

        The judge image is expected to be self-contained (the image already
        carries the judge server and its data); ``payload_files`` is the
        inline-override path, written into the worker before the server
        starts.

        ``run_id`` / ``token_id`` tag the worker for per-run attribution:
        with a run-id the creation carries ``labels={run_id, token_id}`` and
        ``group_name = "<worker_group>--<run-id slug>"`` (when configured);
        without one the creation call carries neither. ``attrs`` is the
        middleware's synthesized attribution dict, stored on the session
        only — it never enters the worker tagging.
        """
        session, _task = self._register(
            image, payload_files, resources, ttl_seconds,
            run_id=run_id, token_id=token_id, attrs=attrs,
        )
        return await self._wait_provision(session)

    async def destroy(self, sid: str) -> bool:
        """Destroy a session (idempotent); returns True when it existed.

        The worker and its service-side tunnel are both closed. A
        still-provisioning session is destroyed too: its background creation
        task is cancelled (the task recycles the worker itself) and never
        re-registers anything.
        """
        session = self._sessions.pop(sid, None)
        if session is None:
            return False
        session.destroyed = True
        if self._journal is not None:
            self._journal.record_destroyed(sid)
        # Kept for the list endpoint's destroyed tail; the deque drops the
        # oldest entries beyond DESTROYED_SESSIONS_KEEP.
        self._destroyed.append(session)
        if self._tunnels is not None:
            self._tunnels.session_tokens.pop(session.app_name, None)
        task = self._provision_tasks.pop(sid, None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass  # the task's own cleanup already recycled the worker
        stopper = getattr(self._executor, "stop_app", None)
        if stopper is not None:
            try:
                await stopper(session.app_name)
            except Exception:  # noqa: BLE001 - best-effort teardown
                LOGGER.warning("failed to stop session %s", sid, exc_info=True)
        if self._tunnels is not None:
            await self._tunnels.close(session.app_name)
        LOGGER.info("judge session %s destroyed (image %s)", sid, session.image)
        return True

    def get(self, sid: str) -> JudgeSession | None:
        return self._sessions.get(sid)

    def is_destroyed(self, sid: str) -> bool:
        """Whether sid is in the recent-destroyed tail: the relay and status
        endpoints answer 410 Gone ("judge session destroyed", terminal) for
        these instead of 404, so a polling client learns its session is gone
        for good instead of hanging on an unknown-session error. The tail is
        per-process memory (bounded, best-effort)."""
        return any(s.session_id == sid for s in self._destroyed)

    def live_sessions(self) -> list[JudgeSession]:
        """Undestroyed sessions (the /v1/status data source)."""
        return [s for s in self._sessions.values() if not s.destroyed]

    def provisioning_count(self) -> int:
        """Sessions currently in ``provisioning`` (registered, still booting)."""
        return sum(
            1
            for s in self._sessions.values()
            if not s.destroyed and s.status == "provisioning"
        )

    # ------------------------------------------------------------------ #
    # Submission cap
    # ------------------------------------------------------------------ #
    def cap_for(self, family: str) -> int:
        """The submission cap for one image family (family override > default)."""
        cap = self.cfg.submission_cap
        return cap.overrides.get(family, cap.default)

    def cap_exempt(self, identity: str) -> bool:
        cap = self.cfg.submission_cap
        if identity in set(cap.exempt_identities):
            return True
        # Hot-reload exemption file: re-read on every check so an exemption
        # lands without a restart. Read failure = no file exemptions.
        if cap.exempt_identities_file and identity in read_exempt_identities_file(
            cap.exempt_identities_file
        ):
            return True
        # Grandfather clause: an identity whose first journal footprint
        # (session register or accepted submission, per journal.first_seen)
        # predates effective_at started under the old unlimited rules —
        # in-flight runs must never feel the cap. Exempt means journaled but
        # never counted nor blocked, same as the static exempt list.
        # effective_at == 0 (unset) grandfathers nobody.
        if cap.effective_at > 0 and self._journal is not None:
            first = self._journal.first_seen(identity)
            if first is not None and first < cap.effective_at:
                return True
        return False

    def submission_used(self, identity: str) -> int:
        """Accepted submissions by identity since submission_cap.effective_at."""
        if self._journal is None:
            return 0
        return self._journal.submission_count(
            identity,
            since=self.cfg.submission_cap.effective_at,
            exclude=set(self.cfg.submission_cap.exempt_identities),
        )

    def record_submission_accept(self, sid: str, identity: str) -> None:
        """Count + journal one accepted relay-level submission (never shards)."""
        if self._journal is not None:
            self._journal.record_submit_accept(sid, identity)

    def session_submission_used(self, sid: str) -> int:
        """Cap-counted submissions in ONE session: the accounting key — a
        run's sessions each carry their own counter, so shared-egress clients
        can never merge one run's submissions into another's. Only
        submissions since submission_cap.effective_at count: sessions from
        the unlimited era keep their ledger but start the cap fresh."""
        if self._journal is None:
            return 0
        return self._journal.session_submission_count(
            sid, since=self.cfg.submission_cap.effective_at
        )

    def list_sessions(self, limit: int = SESSION_LIST_LIMIT) -> list[JudgeSession]:
        """Live sessions plus the recent destroyed tail, created-desc.

        The data source of ``GET /v1/judge/sessions``.
        """
        sessions = list(self._sessions.values()) + list(self._destroyed)
        sessions.sort(key=lambda s: s.created, reverse=True)
        return sessions[:limit]

    # ------------------------------------------------------------------ #
    # Reaper
    # ------------------------------------------------------------------ #
    async def _reap_loop(self) -> None:
        while True:
            await asyncio.sleep(self.cfg.reaper_interval_seconds)
            try:
                await self._reap_once()
            except Exception:  # noqa: BLE001 - the reaper must never die
                LOGGER.exception("judge session reaper iteration failed")

    async def _reap_once(self) -> None:
        now = time.time()
        for sid, session in list(self._sessions.items()):
            if (
                session.status == "ready"
                and session.tunnel_down_at
                and self._tunnels is not None
                and self._tunnels.is_connected(session.app_name)
            ):
                LOGGER.info("judge session %s tunnel reconnected; session resumes", sid)
                session.tunnel_down_at = 0.0
            if now >= session.expires:
                LOGGER.info("reaping expired judge session %s (image %s)", sid, session.image)
                await self.destroy(sid)
            elif session.status != "ready":
                # provisioning: its creation task is bounded by the
                # ready_timeout and lands on failed by itself (and the TTL
                # branch above covers the absolute cap). failed: kept in the
                # table for outcome polling up to failed_retention_seconds,
                # then destroyed.
                if (
                    session.status == "failed"
                    and now - session.last_active > self.cfg.failed_retention_seconds
                ):
                    LOGGER.info(
                        "reaping stale failed judge session %s (image %s)", sid, session.image
                    )
                    await self.destroy(sid)
                continue
            elif self._tunnels is not None and not self._tunnels.is_connected(session.app_name):
                # Tunnel down (reconnect grace): hold the session and its
                # worker so the agent can redial and resume; destroy only
                # when the drop outlasts the grace window. The clock normally
                # starts at claim_tunnel_close (close time); a drop observed
                # only here starts it now.
                if not session.tunnel_down_at:
                    session.tunnel_down_at = now
                if now - session.tunnel_down_at < self.cfg.tunnel_reconnect_grace_seconds:
                    continue
                LOGGER.info(
                    "reaping judge session %s: tunnel down beyond the %.0fs reconnect grace",
                    sid,
                    self.cfg.tunnel_reconnect_grace_seconds,
                )
                await self.destroy(sid)
            elif (
                self._tunnels is not None
                and self._tunnels.in_flight(session.app_name) > 0
            ):
                # Judging in flight: never idle. A long evaluation emits no
                # new messages; reaping here would kill the in-flight
                # submission.
                continue
            elif now - session.last_active > (
                session.idle_ttl_seconds or self.cfg.idle_ttl_seconds
            ):
                LOGGER.info("reaping idle judge session %s (image %s)", sid, session.image)
                await self.destroy(sid)


# --------------------------------------------------------------------------- #
# HTTP handlers
# --------------------------------------------------------------------------- #
def _json_error(status: int, message: str, error_class: str | None = None) -> web.Response:
    body: dict[str, Any] = {"error": message}
    if error_class is not None:
        body["error_class"] = error_class
    return web.json_response(body, status=status)


def _session_gone(sid: str) -> web.Response:
    """410 Gone for a destroyed session: a terminal, explicit "your session
    is gone" — polling clients stop immediately instead of hanging on the
    ambiguous 404. The body shape is a WIRE CONTRACT (clients match
    ``"error_class": "terminal"``); never reword."""
    return web.json_response(
        {
            "error": "judge session destroyed",
            "session_id": sid,
            "error_class": "terminal",
        },
        status=410,
    )


def _unknown_or_gone(store: "JudgeSessionStore", sid: str) -> web.Response:
    """404 for never-existed sids; 410 for sids in the destroyed tail."""
    if store.is_destroyed(sid):
        return _session_gone(sid)
    return _json_error(404, f"unknown judge session {sid}")


def _create_failure_message(exc: BaseException) -> str:
    """The wire-contract wording of a failed session creation (stored on the
    session's ``error`` field — task-side retry matchers key on it
    verbatim)."""
    message = f"judge session create failed: {type(exc).__name__}: {exc}"
    if _is_transient_platform_error(exc) and not isinstance(exc, ValueError):
        message += transient_suffix()
    return message


def _parse_resources(raw: Any) -> dict[str, int]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("resources must be an object of integer values")
    spec: dict[str, int] = {}
    for key, value in raw.items():
        mapped = _RESOURCE_KEYS.get(str(key))
        if mapped is None:
            continue  # forward-compatible: unknown knobs are ignored
        spec[mapped] = int(value)
    return spec


async def handle_session_create(request: web.Request) -> web.Response:
    store: JudgeSessionStore = request.app["judge_sessions"]
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _json_error(400, "invalid JSON body")
    image = str(body.get("judge_image") or "")
    if not image:
        return _json_error(400, "missing judge_image")
    try:
        resources = _parse_resources(body.get("resources"))
        ttl_raw = body.get("ttl")
        ttl = float(ttl_raw) if ttl_raw else None
    except (TypeError, ValueError) as exc:
        return _json_error(400, str(exc))
    # Singleflight key: the authenticated token (a constant under today's
    # single-token deployments, kept as a key field for a future multi-token
    # identity layer), the judge image, and a client identifier. The client
    # id is the optional ``X-TCSEXAM-Client-Id`` header ONLY — the one value
    # that actually identifies a logical caller. NO FALLBACK to
    # ``request.remote``: a shared egress IP would merge UNRELATED runs into
    # one provisioning session. No header => no sharing: every create gets
    # its own session; callers that want storm dedup must send the header.
    client_id = request.headers.get("X-TCSEXAM-Client-Id")
    key = None
    if client_id:
        key = (
            request.headers.get("X-TCSEXAM-Token-Id") or "-",
            image,
            client_id,
        )
    # Caller identity: validated into request["run_id"] by the auth
    # middleware ("" when absent/invalid/mode=off); rides to the session and
    # the worker labels/group_name. The attribution attrs (request["attrs"])
    # ride to the session only.
    run_id = request.get("run_id") or ""
    token_id = request.headers.get("X-TCSEXAM-Token-Id") or ""
    attrs = request.get("attrs") or {}
    try:
        session = store.begin_create(
            key, image, None, resources or None, ttl,
            run_id=run_id, token_id=token_id, attrs=attrs,
            identity=request.get("identity") or request.remote or "",
        )
    except SessionsFullError as exc:
        return _json_error(503, str(exc), error_class="transient")
    except Exception as exc:  # noqa: BLE001 - platform failures reach the client
        message = _create_failure_message(exc)
        if _is_transient_platform_error(exc) and not isinstance(exc, ValueError):
            return _json_error(500, message, error_class="transient")
        return _json_error(500, message, error_class="infra_error")
    base_url = f"{request.app['config'].public_url()}/v1/judge/sessions/{session.session_id}"
    # Creation is asynchronous — 202 with the session registered as
    # "provisioning". Clients that submit right away receive the 503
    # provisioning contract on the relay path and retry.
    return web.json_response(
        {
            "session_id": session.session_id,
            "base_url": base_url,
            "url": base_url,
            "image": session.image,
            "expires_at": session.expires,
            "status": session.status,
        },
        status=202,
    )


async def handle_session_list(
    request: web.Request, *, visible: Callable[[Any], bool] | None = None
) -> web.Response:
    """Session listing: live sessions plus the recent destroyed tail.

    Rows: ``{session_id, image, family, created, last_active, destroyed,
    run_id, agent_name, attrs, status, error}``. ``family`` reuses
    ``status.image_family``'s normalization; ``status``/``error`` are the
    async-creation state (``provisioning``/``ready``/``failed``).
    """
    store: JudgeSessionStore = request.app["judge_sessions"]
    # Chain reconciliation query: ?session_ids=a,b,c → per-session
    # hidden-submission counts plus the chain total. This is the verifier's
    # cap-check data source: the run's declared session chain is the
    # accounting unit, so shared-egress clients can never merge a neighbor's
    # submissions into the total. Public-channel counts ride along for the
    # run-level history attribution (never summed into total_submissions).
    session_ids = request.query.get("session_ids")
    if session_ids is not None and store._journal is not None:
        ids = [x for x in (s.strip() for s in session_ids.split(",")) if x]
        rows = []
        total = 0
        for sid in ids:
            js = store._journal.sessions.get(sid)
            hidden = store._journal.session_submission_count(sid)
            total += hidden
            rows.append(
                {
                    "session_id": sid,
                    "submissions": hidden,
                    "public_submissions": (
                        len(js.public_submissions) if js is not None else 0
                    ),
                    "present": js is not None,
                }
            )
        return web.json_response(
            {
                "session_ids": ids,
                "generated_at": time.time(),
                "total_submissions": total,
                "sessions": rows,
            }
        )
    # Reconciliation query: ?client_ip=<identity> or client_ip=self (resolved
    # from this request) returns the sessions that identity has >=1 accepted
    # submissions in, destroyed included, with the relay-level submission
    # counts and total. Driven by the session journal.
    client_ip = request.query.get("client_ip")
    if client_ip is not None and store._journal is not None:
        identity = (
            client_ip
            if client_ip and client_ip != "self"
            else (request.get("identity") or request.remote or "-")
        )
        rows = []
        total = 0
        for s in store._journal.sessions_by_identity(identity):
            if visible is not None and not visible(s):
                continue
            n = sum(1 for _, ident in s.submissions if ident == identity)
            total += n
            rows.append(
                {
                    "session_id": s.session_id,
                    "family": s.family,
                    "image": s.image,
                    "created": s.created,
                    "destroyed": s.destroyed,
                    "status": s.status,
                    "submissions": n,
                    "best": (
                        {"score": s.best_score, "submission_id": s.best_submission_id}
                        if s.best_score is not None
                        else None
                    ),
                }
            )
        return web.json_response(
            {
                "identity": identity,
                "generated_at": time.time(),
                "total_submissions": total,
                "sessions": rows,
                # Per-session counting rules the cap; identity-keyed totals
                # merge every run sharing an egress address and must never
                # be used as a verdict — ops observability only.
                "note": "identity-keyed accounting is unsafe behind shared egress: totals merge every run sharing an egress IP. Ops observability only — use ?session_ids= for run-level accounting and any verdict.",
            }
        )
    return web.json_response(
        [
            {
                "session_id": session.session_id,
                "image": session.image,
                "family": image_family(session.image),
                "created": session.created,
                "last_active": session.last_active,
                "destroyed": session.destroyed,
                "run_id": session.run_id,
                "agent_name": session.agent_name,
                "attrs": session.attrs,
                "status": session.status,
                "error": session.error,
            }
            for session in store.list_sessions()
            if visible is None or visible(session)
        ]
    )


async def handle_session_status(request: web.Request) -> web.Response:
    store: JudgeSessionStore = request.app["judge_sessions"]
    session = store.get(request.match_info["sid"])
    if session is None:
        return _unknown_or_gone(store, request.match_info["sid"])
    connected = store._tunnels is not None and store._tunnels.is_connected(session.app_name)
    return web.json_response(
        {
            "session_id": session.session_id,
            "image": session.image,
            "created": session.created,
            "last_active": session.last_active,
            "expires_at": session.expires,
            "tunnel_connected": connected,
            "run_id": session.run_id,
            "attrs": session.attrs,
            "status": session.status,
            "error": session.error,
        }
    )


async def handle_session_delete(request: web.Request) -> web.Response:
    """Idempotent destroy: unknown sessions still 200."""
    store: JudgeSessionStore = request.app["judge_sessions"]
    stopped = await store.destroy(request.match_info["sid"])
    return web.json_response({"ok": True, "stopped": stopped})


async def handle_session_relay(request: web.Request) -> web.StreamResponse:
    """Relay one HTTP request to the session's in-worker judge server."""
    store: JudgeSessionStore = request.app["judge_sessions"]
    session = store.get(request.match_info["sid"])
    if session is None:
        return _unknown_or_gone(store, request.match_info["sid"])
    if session.status == "provisioning":
        # Async creation: transient by contract — the task-side retry
        # matchers key on the "please try again" substring and keep backing
        # off until the session flips to ready.
        return _json_error(503, PROVISIONING_MESSAGE, error_class="transient")
    session.last_active = time.time()
    # Submission cap: keyed by SESSION, not source identity — clients may
    # share a NAT egress pool, so identity-keyed accounting silently
    # misattributes submissions. Per-session counting needs no identity at
    # all: each judging session accepts at most `cap` hidden submissions,
    # and the run-level rule is enforced by the verifier against the same
    # journal. Counting happens BEFORE forwarding, in the same synchronous
    # block as the check ("counted at accept"); only the short-circuits
    # above (404 unknown / 503 provisioning) and the 429 below skip
    # counting.
    is_submit = request.method == "POST" and request.match_info.get("tail", "").strip("/") == "submit"
    if is_submit and store._journal is not None:
        identity = request.get("identity") or request.remote or "-"
        if store.cfg.submission_cap.enabled:
            family = image_family(session.image)
            cap = store.cap_for(family)
            used = store.session_submission_used(session.session_id)
            if used >= cap:
                return web.json_response(
                    {
                        "error": "submission_cap_exceeded",
                        "cap": cap,
                        "used": used,
                        "identity": identity,
                        "message": f"submission cap reached for this judging session: {used}/{cap} used",
                    },
                    status=429,
                )
        store.record_submission_accept(session.session_id, identity)
    # check_token=False: this path is already gated by the service auth
    # middleware; the per-session token exists only to close the auth-exempt
    # /apps/<app> twin of this tunnel.
    return await store._tunnels.forward(session.app_name, request, check_token=False)


def register_routes(app: web.Application) -> None:
    app.router.add_post("/v1/judge/sessions", handle_session_create)
    app.router.add_get("/v1/judge/sessions", handle_session_list)
    app.router.add_get("/v1/judge/sessions/{sid}", handle_session_status)
    app.router.add_delete("/v1/judge/sessions/{sid}", handle_session_delete)
    app.router.add_route("*", "/v1/judge/sessions/{sid}/{tail:.*}", handle_session_relay)
