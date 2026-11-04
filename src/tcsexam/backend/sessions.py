"""Judge-session endpoints (``/v1/judge/sessions/*``) — one throwaway worker
per shard, created from the task's judge image, running the baked-in judge
worker on localhost, reached from the task container through the reverse
tunnel.

    task client --HTTP-->  /v1/judge/sessions/{sid}/<path>  --frames-->
    tunnel  --HTTP-->  localhost:8082 inside the judge worker

Endpoints:

* ``POST   /v1/judge/sessions``             — create a session from a judge image.
* ``GET    /v1/judge/sessions/{sid}``       — session status.
* ``GET    /v1/judge/sessions/{sid}/archive``— the session's raw-record
  archive, verifier-only (``X-TCSEXAM-Archive-Token`` credential gate; every
  failure mode — wrong/missing/unconfigured token, unknown sid, no archive
  yet — answers 404 so the endpoint's existence is never exposed).
* ``GET    /v1/judge/sessions/{sid}/payload[...]`` — verifier-only
  creation-payload and submission-body downloads (same gate, same 404
  discipline).
* ``ALL    /v1/judge/sessions/{sid}/{tail}``— relay to the in-worker judge
  worker (``/submit``, ``/submissions``, ``/health``).
* ``DELETE /v1/judge/sessions/{sid}``       — destroy (idempotent, 200 for
  known sessions owned by the caller; unknown sessions answer 404).

Run ownership: the effective run-id (``X-TCSEXAM-Run-Id``, validated by the
auth middleware into ``request["run_id"]``) is stored on the session at
create time and journaled, so it survives DELETE and service restarts.
Every session-level endpoint above (status, relay, delete, archive,
payload, and the ``?session_ids=`` reconciliation query) serves only
requests whose run-id matches the session's owner; a mismatch answers
EXACTLY like an unknown sid (the uniform 404, never 410), and the
singleflight dedup key carries the run-id so two runs never share a
provisioning session even with the same client-id. Sessions created
WITHOUT a run-id are unowned and unrestricted (local/legacy callers keep
working). The run-id is a caller-DECLARED label, not a credential: the
check isolates callers acting under their declared identities; resisting
a malicious caller that holds the same shared service token and declares
somebody else's run-id needs per-run credentials or an equivalent
authorization layer (out of scope).

Sharded sessions (``n_shards`` > 1 on create): the service boots N workers
(a "worker group") with ``INSTANCE_SHARD=i/N`` injected into each judge
worker's environment; shard i judges only slice i of the hidden instance
list (slicing happens in the task's judging logic, e.g. the checker).
``POST /submit`` is fanned out to every shard with the same solver tar;
``GET /submissions`` collects the N shard histories, ARCHIVES the raw
per-instance records (state_dir/judge_archive/<sid>.json — the ingredient
layer for the verifier and reconciliation), and aggregates each submission
into the hidden-channel answer of the final feedback form: the FIVE
NUMBERS — ``better``/``equal``/``worse`` (per-instance three-way against
the baseline B), ``delta`` (direction-normalized total improvement),
``failed`` (infrastructure failures only) — PLUS per-instance records
stripped to ``{instance, A, B, status, detail}``. Shard statistics simply
ADD UP (no weighted means); per-shard records concatenate (sorted by
instance name) into one whole-set table, so the caller sees the same
surface as an unsharded session. K is NEVER exposed on the hidden channel:
the K field is dropped structurally and any K value embedded in a record's
free-text detail is scrubbed out (a few judging logics print the anchor in
their status wording) — B stays, K never leaves the service.

SEMANTIC BOUNDARY — which tasks may shard: sharding is only valid for
tasks where every instance has its OWN time budget: the per-instance limit
survives slicing untouched. Tasks whose solver allocates one GLOBAL time
pool across instances must NOT be sharded — slicing would chop the solver's
global time allocation into N pieces and change what is being measured.
Those run as a single big worker with instance-level parallelism inside the
judge image instead.

Asynchronous creation (202 + polling): the POST registers the session as
``status: "provisioning"`` and returns immediately; a background task boots
the whole shard group and flips the session to ``ready`` or ``failed``.
``ready`` means every shard's boot has SETTLED — each shard is either up or
marked failed; a session with ``live >= ceil(min_ready_ratio * n_shards)``
goes ready degraded (``failed_shards`` visible on the status endpoint,
/health, and every merged submission entry), below the floor the whole
session goes ``failed`` with the first failure's wording in ``error``. The
default pins ``min_ready_ratio = 1.0``: partial provisioning NEVER produces
a score — an incomplete shard set is ``failed``, not partial credit; a
retried judging is a NEW session and does not consume a submission of the
caller's cap (the cap counts accepted submissions, and a failed
provisioning never accepted one). Per-shard boot failures are retried
whole-shard (fresh worker, agent re-upload, tunnel wait) up to
``shard_boot_retries`` times, transient errors only. While the session is
provisioning the relay path answers 503 transient.

TTL anchoring: the session TTL budget starts at READY, not at registration
— ``expires`` is recomputed as ``ready + ttl`` on the ready-flip (a
pool-full provisioning queue or shard-boot retries must not eat the
judging-life budget). The provisioning janitor deadline is unchanged —
only the post-ready lifetime is re-anchored.

Lifecycle rules: creation goes through two concurrency gates (the
store-side per-session gate, then the adapter's global creation gate),
plus a global worker-usage pre-check at accept time (long_lived_count +
in-flight provisioning shards + requested n_shards, capped at
max_sandboxes_global — over the cap is a readable 503, never a queue).
Every created worker is destroyed on exactly one path — an explicit
DELETE, the TTL/idle reaper, a tunnel drop, or service shutdown (each
shard's worker lands in the adapter's long-lived table under its own app
name, so the tunnel-close reaper in server.py covers the drop case per
shard; the store's destroy tears down ALL shards of a session — none may
leak). A shard whose tunnel drops is NOT fatal to the session anymore: it
is marked failed after ``shard_down_grace_ticks`` consecutive reaper ticks
and its instances count toward ``failed`` from then on (entries it judged
before dying keep their archived records — merged history is never
rewritten backwards).

Error classification returned to the caller (the task-side script maps these
onto its retry policy): ``transient`` (session cap reached / global worker
cap reached / worker pool full / platform flap — retry with backoff),
``infra_error`` (service-side fault), ``judge_error`` (surfaced by the judge
worker itself, relayed untouched).

The store skeleton (reaper loop, shutdown semantics, the SessionsFullError
contract, the begin_create/_register async-creation bones, the session
journal hooks) comes from :mod:`tcsexam.backend.sessions_base`; the
sharding machinery (worker groups, shard-level retry, the submit fan-out,
the submissions/health merge) lives here. The store drives the adapter ONLY
through the public protocol (``create_sandbox`` / ``register_long_lived`` /
``long_lived_count`` / ``stop_app``) — never through private members.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import io
import json
import logging
import math
import re
import shlex
import tarfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aiohttp import web

from .agent_files import agent_file_path
from .auth import ATTR_AGENT_NAME
from .config import Config, JudgeSessionsConfig
from .errors import (
    PROVISIONING_MESSAGE,
    TRANSIENT_HINT as _TRANSIENT_HINT,
    is_transient_platform_error as _is_transient_platform_error,
)
from .journal import SessionJournal as _BaseSessionJournal
from .sessions_base import (
    JudgeSessionStore as _BaseJudgeSessionStore,
    SessionsFullError,
    run_id_slug,
)
from .status import image_family

LOGGER = logging.getLogger("tcsexam.backend.sessions")

#: The in-worker agent bundle uploaded to every shard: the flat agent files
#: (they import each other by bare top-level name inside the worker). Read
#: as bytes; never imported from here.
_JUDGE_SESSION_AGENT_PY = agent_file_path("judge_session_agent.py")
_SANDBOX_AGENT_PY = agent_file_path("sandbox_agent.py")
_TUNNEL_PROTOCOL_PY = agent_file_path("tunnel_protocol.py")

#: Verifier-only credential header gating hidden/payload creation and reads.
ARCHIVE_TOKEN_HEADER = "X-TCSEXAM-Archive-Token"

#: Accepted resources keys -> worker spec keys (callers may send either
#: cpu/mem or the spec's own cpu_count/memory_mb/storage_mb).
_RESOURCE_KEYS = {
    "cpu": "cpu_count",
    "cpu_count": "cpu_count",
    "mem": "memory_mb",
    "memory_mb": "memory_mb",
    "storage_mb": "storage_mb",
}

#: Shard-boot retry backoff cap (shard_boot_retry_delay_seconds x 2^n).
_SHARD_BOOT_RETRY_MAX_DELAY = 60.0


class GlobalSandboxCapError(Exception):
    """Global worker-usage pre-check rejection (HTTP 503, transient).

    Raised at create accept time when long_lived_count + in-flight
    provisioning shards + the requested n_shards exceeds
    ``max_sandboxes_global`` (or the memory twin). Same wording family as
    SessionsFullError.
    """


@dataclass
class _BootedShard:
    """Result of a successful shard boot: its tunnel identity + worker."""

    shard: "Shard"
    sandbox: Any


@dataclass
class Shard:
    """One member of a session's worker group."""

    index: int
    app_name: str  # tunnel app name (== session id for unsharded sessions)


@dataclass
class JudgeSession:
    """A live judge session: a worker group + one reverse tunnel per shard."""

    session_id: str
    image: str
    created: float
    last_active: float  # relay activity; idleness is measured from this
    expires: float  # created + ttl at registration; re-anchored to ready + ttl on the ready flip
    shards: list[Shard] = field(default_factory=list)
    destroyed: bool = False
    # Which instance set the session judges: "hidden" (default — the
    # cap-counted channel, five numbers + K-stripped per-instance records)
    # or "public" (the self-test channel — public instances, per-instance
    # full detail, exempt from the submission cap).
    instance_set: str = "hidden"
    # Async provisioning: "provisioning" while the background group create
    # runs, then "ready" (every shard settled; the degraded floor allows
    # failed shards) or "failed" (below the floor; ``error`` carries the
    # wire-contract wording). Default "ready" so sessions hand-built outside
    # the store (tests) count as live — same convention as the base store.
    status: str = "ready"
    error: str = ""
    # Creator identity: journaled at register so the reconciliation API's
    # creator_identity is populated.
    identity: str = ""
    # Owning run-id: the caller-declared X-TCSEXAM-Run-Id at create time
    # ("" when the caller sent none). Session-level endpoints (status,
    # relay, delete, archive, payload, the ?session_ids= query) serve only
    # requests whose effective run-id matches — see _owner_mismatch. A
    # caller-declared label, NOT a credential: it isolates callers acting
    # under their declared identities; resisting a malicious caller that
    # holds the same shared service token and declares somebody else's
    # run-id needs per-run credentials (out of scope).
    run_id: str = ""
    # The creating request's auth token id (worker tagging only).
    token_id: str = ""
    # Attribution attrs: the auth middleware's synthesized dict
    # (TCSEXAM_RUN_ID / TCSEXAM_CLIENT_ID / TCSEXAM_AGENT_NAME), stored on
    # the session only — it never enters the worker tagging.
    attrs: dict[str, str] = field(default_factory=dict)
    # Shard index -> failure reason (boot retries exhausted, or the tunnel
    # stayed down past the grace ticks). Failed shards are PERMANENTLY
    # excluded from the live set: a re-joined shard would have missed
    # submissions and its sequence numbers would misalign the merge.
    failed_shards: dict[int, str] = field(default_factory=dict)
    # Per-shard judging-set size (instances in the shard's slice), learned
    # from fetched /submissions payloads (the first entry carrying records
    # fixes it — the slice is constant). Used to fold shard-level failures
    # (a dead shard's missed submissions, submission-level timeout /
    # judge_error) into the five numbers' worse/failed counts.
    shard_sizes: dict[int, int] = field(default_factory=dict)
    # Per-shard most recent successfully fetched /submissions payload: a
    # failed shard keeps the raw records it had judged before dying (merged
    # history is never rewritten backwards) and the archive writes from
    # here.
    shard_payloads: dict[int, dict] = field(default_factory=dict)
    # Consecutive reaper ticks with the tunnel down, per shard (the
    # two-level tunnel-drop judgement; reset when the tunnel reconnects).
    shard_down_ticks: dict[int, int] = field(default_factory=dict)
    # ---- Hibernate state ----
    # Set when the LATEST submission's complete merged result has been
    # served to a client (judging settled, results delivered); cleared on
    # the next accepted submit. The reaper only hibernates sessions whose
    # judging has settled (plus a pre-hibernate probe) — a mid-judging
    # session is never put down.
    delivered: bool = False
    # Wake blueprint: the create-time inputs needed to re-provision the
    # group byte-identically (same image, same deterministic app names).
    payload_files: dict[str, bytes] | None = None
    resources: dict[str, int] | None = None
    ttl: float = 0.0  # the clamped ttl chosen at registration
    # Routed at registration and retained across hibernation. 0 = section default.
    idle_ttl_seconds: float = 0.0
    # Submission-id era offset: shards assign submission ids per-worker
    # sequentially from 0; a wake re-created worker restarts at 0 and would
    # collide with the archived pre-hibernate numbering. On wake this is set
    # to the archived max id + 1; post-wake fresh entries and the submit 202
    # response are reported as (shard-local id + submit_era_base).
    submit_era_base: int = 0
    # When the session last flipped ready (first create AND every wake
    # re-create). The fan-out treats transport failures within the boot
    # grace after this moment as cold-worker, never as shard failure.
    ready_at: float = 0.0
    # Per-image-family routed readiness budgets (resolve_readiness at
    # registration): the tunnel-wait/agent boot budget and the adapter-side
    # worker-creation budget (None = the adapter's own default). Retained
    # for the wake blueprint — a wake re-provision routes identically.
    ready_timeout_seconds: float = 0.0
    create_ready_timeout_seconds: float | None = None

    @property
    def n_shards(self) -> int:
        return len(self.shards)

    @property
    def agent_name(self) -> str:
        """Caller-declared agent name ("" when not forwarded)."""
        return self.attrs.get(ATTR_AGENT_NAME) or ""


class _BackendSessionJournal(_BaseSessionJournal):
    """The backend's journal adds the public-channel ledger event.

    ``submit_accept_public`` events append to the JSONL ledger and replay
    into the per-session ``public_submissions`` list for run-level history
    attribution — they never enter ``submissions``, so the cap counter and
    chain reconciliation stay hidden-only. The append reuses the base's
    private ``_append`` (single-writer discipline: one writer per ledger
    file, in-memory index kept in sync).
    """

    def record_submit_accept_public(self, sid: str, identity: str) -> None:
        self._append(
            {"t": time.time(), "type": "submit_accept_public", "sid": sid, "identity": identity}
        )


class JudgeSessionStore(_BaseJudgeSessionStore):
    """In-memory table of live judge sessions plus their reaper.

    In-memory by design: a service restart loses the table, and the workers'
    platform-side TTL reaps the orphans. The reaper loop and shutdown
    semantics are the base store's; creation/teardown are the sharded
    variants.
    """

    def __init__(self, executor: Any, config: Config) -> None:
        # Session journal: drives the submission-cap counter and the
        # client_ip reconciliation query; wired here as the subclass that
        # also carries the public-channel event.
        journal = (
            _BackendSessionJournal(str(Path(config.state_dir) / "judge_session_journal.jsonl"))
            if config.state_dir
            else None
        )
        super().__init__(executor, config.backend.judge_sessions, config, journal=journal)
        self._config = config
        self.cfg: JudgeSessionsConfig = config.backend.judge_sessions
        # Store-wide fan-out bound (relay legs to the shards) and teardown
        # bound (destroy's stop_app calls) — see the config comments.
        self._fanout_sem = asyncio.Semaphore(self.cfg.fanout_concurrency)
        self._destroy_sem = asyncio.Semaphore(self.cfg.destroy_concurrency)
        # In-flight provisioning shards across all group creates: += n_shards
        # when a group registers, -= 1 as each shard settles. Read by the
        # global usage pre-check.
        self._inflight_shards = 0
        # Same counter on the memory dimension: += n_shards x
        # spec.memory_mb at register, -= spec.memory_mb per settled shard.
        self._inflight_memory_mb = 0

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def begin_create_group(
        self,
        key: tuple | None,
        image: str,
        payload_files: dict[str, bytes] | None,
        resources: dict[str, int] | None,
        ttl_seconds: float | None,
        n_shards: int,
        *,
        identity: str = "",
        instance_set: str = "hidden",
        run_id: str = "",
        token_id: str = "",
        attrs: dict[str, str] | None = None,
    ) -> JudgeSession:
        """Register a provisioning session for a shard group and kick off
        its creation in the background. Returns immediately.

        Mirrors the base store's ``begin_create`` (singleflight included;
        this key carries run_id, n_shards and instance_set on top of the
        base three so a same-image retry from another run, with a different
        shard count or a different instance set, never shares a group),
        with the group-level ``_register_group`` underneath. Journal
        single-writer invariant: register/ready/failed are each written
        exactly once per session — register here, the ready/failed flip
        inside ``_provision_group``; the HTTP layer adds no journal hooks
        of its own.

        ``run_id`` is the owning run of the session: stored on the session
        and journaled at register so the ownership check (every
        session-level endpoint) survives DELETE and service restarts.
        """
        if key is not None and self.cfg.singleflight:
            key = (*self._creation_key(
                key, image, payload_files, resources, ttl_seconds,
                run_id=run_id, token_id=token_id,
                default_ttl=self.cfg.resolve_lifecycle(image)[1],
            ), n_shards, instance_set)
            shared = self._inflight.get(key)
            if shared is not None:
                LOGGER.info(
                    "judge session create shares provisioning session for key %s (image %s)",
                    key[:1], image,
                )
                return shared
        session, task = self._register_group(
            image, payload_files, resources, ttl_seconds, n_shards,
            identity=identity, instance_set=instance_set,
            run_id=run_id, token_id=token_id, attrs=attrs,
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

    def _register_group(
        self,
        image: str,
        payload_files: dict[str, bytes] | None,
        resources: dict[str, int] | None,
        ttl_seconds: float | None,
        n_shards: int,
        *,
        identity: str = "",
        instance_set: str = "hidden",
        run_id: str = "",
        token_id: str = "",
        attrs: dict[str, str] | None = None,
    ) -> tuple[JudgeSession, asyncio.Task]:
        """Allocate and register the provisioning session for a shard group,
        spawn its group-creation task. All accept-time validation runs here,
        synchronously, before registration: n_shards range (store-side
        backstop for the handler's 400), the session-level resource quotas
        (400 family), the session cap and the global worker-usage pre-check
        (503 family)."""
        if n_shards < 1 or n_shards > self.cfg.max_shards:
            raise ValueError(f"n_shards must be in [1, {self.cfg.max_shards}], got {n_shards}")
        # Session-level quotas: n_shards x the merged per-worker spec, same
        # 400 wording shape as n_shards' (cfg.spec always carries defaults,
        # so a missing key can never produce an empty total).
        spec = {**self.cfg.spec, **(resources or {})}
        cpu = int(spec.get("cpu_count") or 0)
        mem = int(spec.get("memory_mb") or 0)
        total_cpu = n_shards * cpu
        total_mem = n_shards * mem
        # Session-level quotas: DISABLED when the cap is 0 (the default) —
        # the dual-dimension global pre-check below subsumes them; set a
        # positive cap to re-enable the static per-session bound.
        if self.cfg.max_session_cpu_count > 0 and total_cpu > self.cfg.max_session_cpu_count:
            raise ValueError(
                f"session cpu total must be in [0, {self.cfg.max_session_cpu_count}] cores, "
                f"got {total_cpu} (n_shards={n_shards} x cpu_count={cpu})"
            )
        if self.cfg.max_session_memory_mb > 0 and total_mem > self.cfg.max_session_memory_mb:
            raise ValueError(
                f"session memory total must be in [0, {self.cfg.max_session_memory_mb}] MB, "
                f"got {total_mem} (n_shards={n_shards} x memory_mb={mem})"
            )
        # Live-session cap (same counting as the base store: failed sessions
        # excluded).
        live = sum(
            1 for s in self._sessions.values() if not s.destroyed and s.status != "failed"
        )
        if live >= self.cfg.max_sessions:
            raise SessionsFullError(
                f"judge session cap reached ({self.cfg.max_sessions}); {_TRANSIENT_HINT}"
            )
        if getattr(self._executor, "create_sandbox", None) is None:
            raise RuntimeError("judge sessions require a platform adapter")
        # Global usage pre-check: REAL-TIME accounting on BOTH quota
        # dimensions — instances AND memory — estimated as live + in-flight +
        # requested. Approximate by design (concurrent accepts race, and it
        # only sees THIS service's registry; the platform quota stays the
        # final constraint), never queueing — the caller gets a readable 503
        # and backs off. Memory binds first at the 8 GiB/worker default.
        counter = getattr(self._executor, "long_lived_count", None)
        long_lived = counter() if callable(counter) else 0
        mem_counter = getattr(self._executor, "long_lived_memory_mb", None)
        long_lived_mem = mem_counter() if callable(mem_counter) else 0
        global_cap = self._config.backend.max_sandboxes_global
        mem_cap = self._config.backend.max_sandbox_memory_mb
        proj_instances = long_lived + self._inflight_shards + n_shards
        proj_memory_mb = long_lived_mem + self._inflight_memory_mb + n_shards * mem
        if proj_instances > global_cap or proj_memory_mb > mem_cap:
            raise GlobalSandboxCapError(
                f"global worker cap reached ({global_cap} instances / {mem_cap} MB memory; "
                f"projected {proj_instances} instances / {proj_memory_mb} MB); {_TRANSIENT_HINT}"
            )

        idle_ttl, route_ttl = self.cfg.resolve_lifecycle(image)
        ttl = ttl_seconds if ttl_seconds else route_ttl
        ttl = max(60.0, min(ttl, self.cfg.max_ttl_seconds))
        # Per-image-family readiness budgets (the routes' ready timeout and
        # the adapter-side create_ready_timeout the base store already
        # routes for single-worker sessions). Stored on the session so the
        # hibernate wake re-provision uses the same routed values.
        ready_timeout, create_ready_timeout = self.cfg.resolve_readiness(image)

        now = time.time()
        session_id = "jsess-" + uuid.uuid4().hex[:12]
        # App names are deterministic from the session id, so every Shard
        # exists from registration time; workers attach as they boot.
        shards = [
            Shard(index=i, app_name=session_id if n_shards == 1 else f"{session_id}-s{i}")
            for i in range(n_shards)
        ]
        session = JudgeSession(
            session_id=session_id,
            image=image,
            created=now,
            last_active=now,
            expires=now + ttl,
            shards=shards,
            status="provisioning",
            identity=identity,
            run_id=run_id,
            token_id=token_id,
            attrs=dict(attrs or {}),
            instance_set=instance_set,
            payload_files=payload_files,
            resources=resources,
            ttl=ttl,
            idle_ttl_seconds=idle_ttl,
            ready_timeout_seconds=ready_timeout,
            create_ready_timeout_seconds=create_ready_timeout,
        )
        self._sessions[session_id] = session
        # Journal register event, written the way the base store's _register
        # writes it (single-writer invariant: the HTTP layer adds no
        # register/ready hooks of its own). run_id rides along so the
        # ownership check survives restarts.
        if self._journal is not None:
            self._journal.record_register(
                session_id, image, image_family(image), identity, created=now, run_id=run_id
            )
        self._inflight_shards += n_shards
        self._inflight_memory_mb += n_shards * mem

        task = self._spawn_provision(session, image, payload_files, spec, ttl)
        return session, task

    def _spawn_provision(
        self,
        session: JudgeSession,
        image: str,
        payload_files: dict[str, bytes] | None,
        spec: dict[str, int],
        ttl: float,
    ) -> asyncio.Task:
        """Spawn the janitor-wrapped group create for a session — used by
        both _register_group (first create) and _wake_session (hibernate
        wake re-create; the in-flight accounting there mirrors the
        registration one)."""
        session_id = session.session_id
        n_shards = session.n_shards
        # Provisioning janitor (same shape as the base store's): wall-clock
        # deadline for the WHOLE group create. The per-shard create budget
        # scales with the number of gate waves (n_shards through the
        # narrower of the two creation gates), then one tunnel-wait budget
        # plus the margin. Both budgets honor the session's routed
        # per-image-family values (resolve_readiness at registration).
        if session.create_ready_timeout_seconds is not None:
            create_budget = session.create_ready_timeout_seconds
        else:
            create_budget = float(getattr(self._executor, "ready_timeout_seconds", 2400.0))
        ready_budget = session.ready_timeout_seconds or self.cfg.ready_timeout_seconds
        gate = max(
            1,
            min(
                self._config.backend.session_create_concurrency,
                self._config.backend.create_concurrency,
            ),
        )
        waves = max(1, math.ceil(n_shards / gate))
        provision_deadline = (
            create_budget * waves
            + ready_budget
            + self.cfg.provision_janitor_margin_seconds
        )

        async def _provision_with_deadline() -> None:
            try:
                await asyncio.wait_for(
                    self._provision_group(session, image, payload_files, spec, ttl),
                    timeout=provision_deadline,
                )
            except asyncio.TimeoutError:
                # wait_for cancels _provision_group; the per-shard cancel
                # paths already recycled boot-midway workers. Here we settle
                # the session state and recycle the settled live shards'
                # workers.
                if not session.destroyed and session.status == "provisioning":
                    session.status = "failed"
                    session.error = (
                        "judge session create failed: RuntimeError: "
                        f"provisioning deadline exceeded ({provision_deadline:.0f}s)"
                        f" (transient platform error, {_TRANSIENT_HINT})"
                    )
                    session.last_active = time.time()
                    if self._journal is not None:
                        self._journal.record_status(session.session_id, "failed", session.error)
                    await self._recycle_live_shards(session)
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
        return task

    def _wake_session(self, session: JudgeSession) -> asyncio.Task:
        """Flip a hibernated session back to provisioning and spawn the group
        re-create from the retained wake blueprint (same image, same
        deterministic app names, fresh workers). failed_shards and
        down-ticks reset — a shard that died pre-hibernate gets a fresh
        boot attempt. Shard-local judging state does NOT survive: the new
        workers start empty, so the merge path unions each shard's archived
        pre-hibernate payload with its fresh post-wake one (pre-hibernate
        submissions stay in the history; nothing needs re-submission — the
        pre-hibernate probe guaranteed a settled state). submit_era_base
        offsets the fresh workers' restarted submission ids back onto the
        continuous sequence. The numbering splits at that base: at/above it
        the fresh worker is authoritative (same-id entries replace); below
        it the archived payload is frozen (the base is a merge boundary,
        not merely an anti-collision offset)."""
        # Worker submission ids are 0-BASED: the offset past an archived
        # max id M is M+1, not M (max alone would make the first post-wake
        # submission land on the pre-hibernate last id — the reported id
        # collides, and the era union's >seen filter would drop the fresh
        # entry forever).
        era_base = 0
        for payload in session.shard_payloads.values():
            for entry in payload.get("submissions", []):
                era_base = max(era_base, int(entry.get("submission") or 0) + 1)
        session.submit_era_base = era_base
        session.status = "provisioning"
        session.error = ""
        session.failed_shards = {}
        session.shard_down_ticks = {}
        spec = {**self.cfg.spec, **(session.resources or {})}
        mem = int(spec.get("memory_mb") or 0)
        self._inflight_shards += session.n_shards
        self._inflight_memory_mb += session.n_shards * mem
        session.last_active = time.time()
        return self._spawn_provision(
            session, session.image, session.payload_files, spec,
            session.ttl or self.cfg.ttl_seconds,
        )

    async def _provision_group(
        self,
        session: JudgeSession,
        image: str,
        payload_files: dict[str, bytes] | None,
        spec: dict[str, int],
        ttl: float,
    ) -> None:
        """The background half of group creation: boot every shard
        concurrently (per-shard whole-boot retries), then flip the
        pre-registered session ready (degraded allowed) or failed. On
        cancellation (DELETE mid-provisioning / janitor) the per-shard
        cancel paths recycle boot-midway workers; settled live shards are
        recycled by destroy() resp. the janitor branch.
        """
        n_shards = session.n_shards
        session_gate = asyncio.Semaphore(self._config.backend.session_create_concurrency)
        await asyncio.gather(
            *(
                self._boot_shard_with_retry(
                    session, shard, image, payload_files, spec, ttl, session_gate
                )
                for shard in session.shards
            )
        )
        if session.destroyed:
            return
        live = n_shards - len(session.failed_shards)
        floor = math.ceil(self.cfg.min_ready_ratio * n_shards)
        session.last_active = time.time()
        if live >= floor:
            session.status = "ready"
            session.ready_at = session.last_active
            # Re-anchor the TTL at READY: the session's life budget covers
            # its JUDGING life, not the provisioning queue — pool-full waits
            # and shard-boot retries must never eat the TTL. `expires` was
            # created+ttl at registration; recompute it as ready+ttl on
            # this flip.
            # The explicit budget is stable across hibernation. Deriving it
            # from expires-created would add past startup/idle time on wake.
            session.expires = session.last_active + ttl
            if self._journal is not None:
                self._journal.record_status(session.session_id, "ready")
            LOGGER.info(
                "judge session %s ready (image %s, shards %d, failed %d, ttl %gs)",
                session.session_id, image, n_shards, n_shards - live, ttl,
            )
            return
        # Below the degraded floor: the whole session fails with the FIRST
        # failure's reason (deterministic: lowest shard index), in the base
        # store's _create_failure_message wording family — task-side retry
        # matchers key on the same substrings.
        first_index = min(session.failed_shards)
        session.status = "failed"
        session.error = (
            f"judge session create failed: {session.failed_shards[first_index]}"
        )
        if self._journal is not None:
            self._journal.record_status(session.session_id, "failed", session.error)
        LOGGER.warning(
            "judge session %s failed: only %d/%d shards booted (floor %d): %s",
            session.session_id, live, n_shards, floor, session.error,
        )
        await self._recycle_live_shards(session)

    async def _boot_shard_with_retry(
        self,
        session: JudgeSession,
        shard: Shard,
        image: str,
        payload_files: dict[str, bytes] | None,
        spec: dict[str, int],
        ttl: float,
        session_gate: asyncio.Semaphore,
    ) -> None:
        """Boot one shard with whole-boot retries (fresh worker every
        attempt — an upload/launch failure leaves the control channel
        untrustworthy, and a new worker is the most predictable recovery).
        Transient failures only, exponential backoff capped at 60s. A shard
        whose retries run out is marked failed on the session; the shard is
        registered on the adapter's long-lived table the moment it is up.
        """
        attempts = self.cfg.shard_boot_retries + 1
        try:
            for attempt in range(1, attempts + 1):
                try:
                    booted = await self._boot_shard(
                        session.session_id, shard.index, session.n_shards,
                        image, payload_files, spec, ttl, session_gate,
                        instance_set=session.instance_set,
                        run_id=session.run_id,
                        token_id=session.token_id,
                        agent_name=session.agent_name,
                        ready_timeout_seconds=(
                            session.ready_timeout_seconds or self.cfg.ready_timeout_seconds
                        ),
                        create_ready_timeout_seconds=session.create_ready_timeout_seconds,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001 - classified below
                    transient = _is_transient_platform_error(exc) and not isinstance(
                        exc, ValueError
                    )
                    if attempt >= attempts or not transient:
                        reason = f"{type(exc).__name__}: {exc}"
                        if transient:
                            reason += f" (transient platform error, {_TRANSIENT_HINT})"
                        session.failed_shards[shard.index] = reason
                        LOGGER.warning(
                            "judge session %s shard %d boot failed after %d/%d attempts: %s",
                            session.session_id, shard.index, attempt, attempts, reason,
                        )
                        self._fail_session_if_all_shards_dead(session)
                        return
                    delay = min(
                        self.cfg.shard_boot_retry_delay_seconds * (2 ** (attempt - 1)),
                        _SHARD_BOOT_RETRY_MAX_DELAY,
                    )
                    LOGGER.info(
                        "judge session %s shard %d boot attempt %d/%d failed (%s: %s); "
                        "retrying the whole boot in %gs",
                        session.session_id, shard.index, attempt, attempts,
                        type(exc).__name__, exc, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                self._executor.register_long_lived(shard.app_name, booted.sandbox)
                return
        finally:
            self._inflight_shards -= 1
            self._inflight_memory_mb -= int(spec.get("memory_mb") or 0)

    async def _boot_shard(
        self,
        session_id: str,
        index: int,
        n_shards: int,
        image: str,
        payload_files: dict[str, bytes] | None,
        spec: dict[str, int],
        ttl: float,
        session_gate: asyncio.Semaphore,
        *,
        instance_set: str = "hidden",
        run_id: str = "",
        token_id: str = "",
        agent_name: str = "",
        ready_timeout_seconds: float | None = None,
        create_ready_timeout_seconds: float | None = None,
    ) -> "_BootedShard":
        """Boot one shard's worker: create, upload the agent, launch it,
        wait for its reverse tunnel. The worker is destroyed on any
        failure; on success ownership passes to the caller.

        The per-session creation gate is taken before ``create_sandbox``
        (which then takes the adapter's global gate) — always session gate
        first, global gate second, so the two never cross-hold. The gate is
        released right after create returns: the upload/launch/tunnel-wait
        stages are waiting-type work that barely pressures the platform.

        ``run_id`` tags the worker the way the base store's single-worker
        creation does: ``labels = {run_id, token_id}`` and, when
        ``config.worker_group`` is set, ``group_name =
        "<worker_group>--<run-id slug>"`` so the platform can reap exactly
        one attempt's workers. ``ready_timeout_seconds`` /
        ``create_ready_timeout_seconds`` are the routed per-image-family
        budgets (None -> the config section default / the adapter's own
        budget).
        """
        creator = self._executor.create_sandbox
        ready_timeout = ready_timeout_seconds or self.cfg.ready_timeout_seconds
        # Unsharded sessions keep the historical app name (session id); a
        # sharded session's members are suffixed -s<i>.
        app_name = session_id if n_shards == 1 else f"{session_id}-s{index}"
        base = self._config.public_url()
        ws_scheme = "wss" if base.startswith("https") else "ws"
        ws_url = f"{ws_scheme}://{base.split('://', 1)[1]}/v1/tunnel/{app_name}"
        work_dir = self.cfg.work_dir

        sandbox = None
        try:
            create_kwargs: dict[str, Any] = {}
            if create_ready_timeout_seconds is not None:
                create_kwargs["ready_timeout_seconds"] = create_ready_timeout_seconds
            if run_id:
                # Worker tagging (same shape as the base store's): labels
                # for platform-side lookup, and a per-run group_name so the
                # platform can reap exactly one attempt's workers. Without
                # a configured worker_group the group tag is skipped but
                # labels still ride.
                create_kwargs["labels"] = {
                    "run_id": run_id,
                    "token_id": token_id or "-",
                }
                worker_group = getattr(self._service_config, "worker_group", "") or ""
                if worker_group:
                    create_kwargs["group_name"] = (
                        f"{worker_group}--{run_id_slug(run_id)}"
                    )
            async with session_gate:
                sandbox = await creator(
                    self.cfg.profile, image, ttl_seconds=ttl, spec=spec, **create_kwargs
                )
            ctrl = sandbox.ctrl
            await ctrl.write_bytes(
                f"{work_dir}/judge_session_agent.py", _JUDGE_SESSION_AGENT_PY.read_bytes(), parents=True
            )
            await ctrl.write_bytes(
                f"{work_dir}/sandbox_agent.py", _SANDBOX_AGENT_PY.read_bytes(), parents=True
            )
            await ctrl.write_bytes(
                f"{work_dir}/tunnel_protocol.py", _TUNNEL_PROTOCOL_PY.read_bytes(), parents=True
            )
            # Test-double workers carry their own judge_port (one local
            # worker per shard); real isolated workers each have their own
            # localhost and all use the configured port.
            judge_port = int(getattr(sandbox, "judge_port", self.cfg.judge_port))
            agent_config = {
                "app_name": app_name,
                "run_id": run_id,
                "agent_name": agent_name,
                "service_ws_url": ws_url,
                "token_id": self._config.token_id or "",
                "token_secret": self._config.token_secret or "",
                "port": judge_port,
                "command": self.cfg.command,
                "health_path": self.cfg.health_path,
                **self.cfg.agent_timeouts(ready_timeout),
                "ready_label": self.cfg.ready_label,
                "env": {
                    # Sharded sessions: the slice selector for the judging
                    # logic. Public sessions: the judge worker redirects
                    # judging to the image's public instance set
                    # (INSTANCES_DIR export); hidden stays the default.
                    **({"INSTANCE_SHARD": f"{index}/{n_shards}"} if n_shards > 1 else {}),
                    **({"INSTANCE_SET": "public"} if instance_set == "public" else {}),
                },
                "payload_files": {
                    path: base64.b64encode(data).decode()
                    for path, data in (payload_files or {}).items()
                },
            }
            await ctrl.write_bytes(
                f"{work_dir}/agent_config.json",
                json.dumps(agent_config).encode(),
                parents=True,
            )
            # plain python3: the session agent is stdlib-only, no interpreter
            # constraint applies. Detached: setsid + background + logfile, so
            # no control-channel exec session is held for the worker's
            # lifetime.
            cmd = (
                f"cd {shlex.quote(work_dir)} && "
                f"setsid python3 judge_session_agent.py >> agent.log 2>&1 < /dev/null &"
            )
            connected = await self._launch_agent_and_wait(
                Shard(index=index, app_name=app_name), ctrl, cmd, ready_timeout
            )
            if not connected:
                try:
                    tail = (await asyncio.wait_for(
                        ctrl.read_text(f"{work_dir}/agent.log"),
                        timeout=min(5.0, ready_timeout),
                    ))[-1500:]
                except Exception:  # noqa: BLE001
                    tail = "<no agent.log>"
                raise RuntimeError(
                    f"the judge session agent did not connect within "
                    f"{ready_timeout:g}s: {tail}"
                )
        except asyncio.CancelledError:
            # DELETE / janitor mid-boot: recycle the worker (shielded from a
            # second cancel), then propagate.
            if sandbox is not None:
                try:
                    await asyncio.shield(sandbox.delete())
                except Exception:  # noqa: BLE001 - best-effort teardown
                    pass
            raise
        except Exception:
            if sandbox is not None:
                try:
                    await sandbox.delete()
                except Exception:  # noqa: BLE001
                    pass
            raise
        return _BootedShard(Shard(index=index, app_name=app_name), sandbox)

    async def _recycle_live_shards(self, session: JudgeSession) -> None:
        """stop_app every non-failed shard's worker (bounded by the
        store-wide destroy semaphore). Used when the session itself fails:
        the group may not leak its live members. stop_app is a no-op for
        app names that never registered.
        """
        stopper = getattr(self._executor, "stop_app", None)
        if stopper is None:
            return

        async def _stop(shard: Shard) -> None:
            async with self._destroy_sem:
                try:
                    await stopper(shard.app_name)
                except Exception:  # noqa: BLE001 - best-effort teardown
                    LOGGER.warning(
                        "failed to stop session %s shard %s",
                        session.session_id, shard.app_name, exc_info=True,
                    )

        await asyncio.gather(
            *(
                _stop(shard)
                for shard in session.shards
                if shard.index not in session.failed_shards
            )
        )

    async def _hibernate_if_settled(self, session: JudgeSession) -> None:
        """Probe, then hibernate.

        The probe is the load-bearing guard: fetch /submissions from every
        live shard and only proceed when judging has SETTLED (the delivered
        flag alone is racy — a submit can land between the reaper's check
        and the teardown). An incomplete probe (any live shard unreachable
        or mid-judging) skips this tick; the next reaper tick retries. On
        success the shard payloads + archive are refreshed one last time —
        through the SAME era union the client fetch uses
        (:func:`_era_union_payloads`), never a raw overwrite: a post-wake
        payload alone carries only the current era under restarted local
        ids, and writing it straight over the archive would truncate the
        session's history to that era on every wake+re-hibernate cycle. The
        whole group is then stopped (metadata, cap ledger, archive and
        persisted submission bodies all kept), and the expiry clock
        restarts at now + ttl — a hibernated session costs nothing, so it
        should not die earlier than the ready one it replaces. The wake
        path is handle_session_relay's hibernated branch.
        """
        results = await _call_shards(
            self, session, "GET", "/submissions",
            timeout=self.cfg.shard_call_timeout_seconds,
        )
        probe: dict[int, dict] = {}
        for idx, (status, _headers, body) in results.items():
            if status != 200:
                return  # a live shard unreachable: judging state unknown, retry next tick
            try:
                probe[idx] = json.loads(body.decode())
            except Exception:  # noqa: BLE001
                return
        if not _latest_submission_complete(session, probe):
            return  # mid-judging after all — the delivered flag was optimistic
        _era_union_payloads(session, probe)
        for idx, payload in probe.items():
            session.shard_payloads[idx] = payload
        _write_archive(self, session)
        stopper = getattr(self._executor, "stop_app", None)
        if stopper is not None:

            async def _stop(shard: Shard) -> None:
                async with self._destroy_sem:
                    try:
                        await stopper(shard.app_name)
                    except Exception:  # noqa: BLE001 - best-effort teardown
                        LOGGER.warning(
                            "hibernate: failed to stop session %s shard %s",
                            session.session_id, shard.app_name, exc_info=True,
                        )

            await asyncio.gather(*(_stop(shard) for shard in session.shards))
        session.status = "hibernated"
        session.delivered = False
        session.expires = time.time() + session.ttl
        LOGGER.info(
            "judge session %s hibernated (%d workers recycled, metadata + archive kept)",
            session.session_id, len(session.shards),
        )

    async def destroy(self, sid: str) -> bool:
        """Destroy a session (idempotent); returns True when it existed.

        Tears down EVERY shard's worker and service-side tunnel — the group
        leaves no member behind. A still-provisioning session's background
        create is cancelled first (per-shard cancel paths recycle boot-midway
        workers); the settled teardown fans out under the store-wide
        destroy semaphore.
        """
        session = self._sessions.pop(sid, None)
        if session is None:
            return False
        session.destroyed = True
        if self._journal is not None:
            self._journal.record_destroyed(sid)
        # Kept for the list endpoint's destroyed tail.
        self._destroyed.append(session)
        task = self._provision_tasks.pop(sid, None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass  # the task's own cleanup already recycled the workers
        stopper = getattr(self._executor, "stop_app", None)
        if session.shards:

            async def _stop(shard: Shard) -> None:
                async with self._destroy_sem:
                    if stopper is not None:
                        try:
                            await stopper(shard.app_name)
                        except Exception:  # noqa: BLE001 - best-effort teardown
                            LOGGER.warning(
                                "failed to stop session %s shard %s", sid, shard.app_name, exc_info=True
                            )
                    if self._tunnels is not None:
                        await self._tunnels.close(shard.app_name)

            await asyncio.gather(*(_stop(shard) for shard in session.shards))
        LOGGER.info(
            "judge session %s destroyed (image %s, shards %d)", sid, session.image, session.n_shards
        )
        return True

    def record_submission_accept_public(self, sid: str, identity: str) -> None:
        """Journal one accepted PUBLIC submission — ledger only, never
        counted against the submission cap (the cap counts only
        ``instance_set == hidden`` submissions)."""
        rec = getattr(self._journal, "record_submit_accept_public", None)
        if rec is not None:
            rec(sid, identity)

    # ------------------------------------------------------------------ #
    # Reaper (the loop itself is the base store's; the per-session rules
    # are the sharded variants)
    # ------------------------------------------------------------------ #
    async def _reap_once(self) -> None:
        now = time.time()
        for sid, session in list(self._sessions.items()):
            if self._tunnels is not None:
                # Tunnel reconnect recovery: a reconnected shard's down-tick
                # counter resets (the shard was never marked failed).
                for shard in session.shards:
                    if shard.index in session.shard_down_ticks and self._tunnels.is_connected(
                        shard.app_name
                    ):
                        session.shard_down_ticks.pop(shard.index, None)
            if now >= session.expires:
                LOGGER.info("reaping expired judge session %s (image %s)", sid, session.image)
                await self.destroy(sid)
            elif session.status != "ready":
                # provisioning: its creation task is bounded by the janitor
                # deadline and lands on failed by itself. failed: kept for
                # outcome polling up to failed_retention_seconds, then
                # destroyed (the base retention rule).
                if (
                    session.status == "failed"
                    and now - session.last_active > self.cfg.failed_retention_seconds
                ):
                    LOGGER.info(
                        "reaping stale failed judge session %s (image %s)", sid, session.image
                    )
                    await self.destroy(sid)
                continue
            elif self._tunnels is not None and await self._mark_down_shards(session):
                # A shard's tunnel stayed down past the grace ticks: mark it
                # failed and reap its worker (the worker reap happens inside
                # _mark_down_shards; the tunnel-close callback never deletes
                # on close). Entries it judged before dying keep their
                # archived records.
                LOGGER.info(
                    "judge session %s: %d/%d shards failed (tunnel down)",
                    sid, len(session.failed_shards), session.n_shards,
                )
            elif (
                self._tunnels is not None
                and any(
                    self._tunnels.in_flight(shard.app_name) > 0 for shard in session.shards
                )
            ):
                # Judging in flight on any shard: never idle (a long
                # evaluation emits no new messages).
                continue
            elif (
                self.cfg.hibernate_enabled
                and session.delivered
                and now - session.last_active > self.cfg.hibernate_grace_seconds
            ):
                # Delivered + quiet past grace: recycle the whole group,
                # keep metadata — the recoverable form of idle collection.
                # The probe inside re-confirms settled.
                await self._hibernate_if_settled(session)
            elif now - session.last_active > (
                session.idle_ttl_seconds or self.cfg.idle_ttl_seconds
            ):
                if self.cfg.hibernate_enabled:
                    # The idle destroy becomes hibernate: same lifetime
                    # semantics, recoverable outcome (the pre-hibernate
                    # probe still guards mid-judging edge cases).
                    await self._hibernate_if_settled(session)
                else:
                    LOGGER.info("reaping idle judge session %s (image %s)", sid, session.image)
                    await self.destroy(sid)

    def _session_for_app(self, app_name: str) -> JudgeSession | None:
        """Map a shard app name to its session (single-shard sessions use the
        bare session id as the app name; sharded ones use ``<sid>-s<i>``)."""
        session = self._sessions.get(app_name)
        if session is not None:
            return session
        sid, sep, idx = app_name.rpartition("-s")
        if sep and idx.isdigit():
            return self._sessions.get(sid)
        return None

    def claim_shard_tunnel_close(self, app_name: str) -> bool:
        """Claim a shard tunnel drop for the shard-level down-grace: returns
        True when the app belongs to a live ready/provisioning session — the
        caller must NOT tear the worker down. The drop is then owned by the
        shard down-grace (``shard_down_grace_ticks`` reaper ticks): a
        reconnect within the grace resets the down-ticks and the shard
        carries on untouched; only a shard still down past the grace is
        marked failed and its worker reaped. Unknown apps and non-ready
        sessions return False (the immediate-teardown path)."""
        session = self._session_for_app(app_name)
        if session is None or session.destroyed or session.status not in ("ready", "provisioning"):
            return False
        LOGGER.info(
            "judge session %s shard tunnel down; holding the worker for the %d-tick down-grace",
            session.session_id, self.cfg.shard_down_grace_ticks,
        )
        return True

    async def _mark_down_shards(self, session: JudgeSession) -> bool:
        """Two-level tunnel-drop judgement: increment each live shard's
        consecutive down-tick counter; at ``shard_down_grace_ticks`` mark
        the shard failed AND reap its worker. Returns True when any shard
        is newly failed (so the reaper logs and moves on to the next
        session)."""
        newly_failed = False
        for shard in session.shards:
            if shard.index in session.failed_shards:
                continue
            if self._tunnels.is_connected(shard.app_name):
                continue
            ticks = session.shard_down_ticks.get(shard.index, 0) + 1
            session.shard_down_ticks[shard.index] = ticks
            if ticks >= self.cfg.shard_down_grace_ticks:
                session.shard_down_ticks.pop(shard.index, None)
                session.failed_shards[shard.index] = (
                    f"shard tunnel down beyond {self.cfg.shard_down_grace_ticks} reaper ticks"
                )
                newly_failed = True
                LOGGER.info(
                    "judge session %s shard %d marked failed: tunnel down for %d ticks",
                    session.session_id, shard.index, ticks,
                )
                await _stop_sandbox_best_effort(self._executor, shard.app_name)
                self._fail_session_if_all_shards_dead(session)
        return newly_failed

    def _fail_session_if_all_shards_dead(self, session: JudgeSession) -> None:
        """When every shard is dead the session flips to failed: it must not
        sit ready answering 502 transient forever — the client's retry
        matchers treat 502 as transient and retry indefinitely without ever
        learning the session is dead. On the last shard's failure the
        session goes failed: the status endpoint answers truthfully and the
        client creates a fresh session on its chain; the reaper collects
        the session after the failed-retention window. The archive stays
        readable throughout (verifier pulls are unaffected)."""
        if session.destroyed or session.status != "ready":
            return
        if session.n_shards == 0 or len(session.failed_shards) < session.n_shards:
            return
        session.status = "failed"
        session.error = (
            f"judge session failed: all {session.n_shards} shards are dead; "
            "create a new judge session"
        )
        session.last_active = time.time()
        if self._journal is not None:
            self._journal.record_status(session.session_id, "failed", session.error)
        LOGGER.warning(
            "judge session %s failed: all %d shards are dead",
            session.session_id, session.n_shards,
        )


# --------------------------------------------------------------------------- #
# HTTP handlers
# --------------------------------------------------------------------------- #
def _json_error(status: int, message: str, error_class: str | None = None) -> web.Response:
    body: dict[str, Any] = {"error": message}
    if error_class is not None:
        body["error_class"] = error_class
    return web.json_response(body, status=status)


def _valid_archive_token(request: web.Request, store: "JudgeSessionStore") -> bool:
    token = getattr(store._config, "archive_token", "")
    return bool(token) and request.headers.get(ARCHIVE_TOKEN_HEADER, "") == token


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
        spec[mapped] = None if mapped == "storage_mb" and value is None else int(value)
    return spec


def _parse_payload(raw: Any) -> dict[str, bytes]:
    """judge_payload: inline override files, path -> base64 content."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("judge_payload must be an object mapping in-worker paths to base64 content")
    files: dict[str, bytes] = {}
    for path, content in raw.items():
        path = str(path)
        if not path.startswith("/"):
            raise ValueError(f"judge_payload path must be absolute: {path!r}")
        try:
            files[path] = base64.b64decode(str(content), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"judge_payload[{path!r}] is not valid base64: {exc}") from exc
    return files


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
        payload_files = _parse_payload(body.get("judge_payload"))
        ttl_raw = body.get("ttl")
        ttl = float(ttl_raw) if ttl_raw else None
        n_shards = int(body.get("n_shards") or 1)
        if n_shards < 1 or n_shards > store.cfg.max_shards:
            return _json_error(400, f"n_shards must be in [1, {store.cfg.max_shards}], got {n_shards}")
        # Which instance set the session judges: hidden (default, the
        # cap-counted channel) or public (the self-test channel, exempt from
        # the cap, per-instance full detail).
        instance_set = str(body.get("instance_set") or "hidden")
        if instance_set not in ("hidden", "public"):
            return _json_error(400, f"instance_set must be hidden or public, got {instance_set!r}")
    except (TypeError, ValueError) as exc:
        return _json_error(400, str(exc))
    if (instance_set == "hidden" or body.get("judge_payload") is not None) and not _valid_archive_token(
        request, store
    ):
        return _json_error(403, "valid archive token required")
    if instance_set == "public":
        public_image = (getattr(store._config, "public_image_map", {}) or {}).get(image)
        if not public_image:
            return _json_error(403, "public judge image is not allowed")
        image = public_image
    # Singleflight key: the base store's three elements plus the effective
    # run-id, n_shards and instance_set — a retry that changed the shard
    # count must NOT share an in-flight group, and neither may a hidden
    # retry share a public one (the two judge different instance sets) or
    # another run's retry share this run's (run ownership below would then
    # lock the retrying caller out of its "own" session). SHARING REQUIRES
    # an explicit X-TCSEXAM-Client-Id: without one the key would fall back
    # to a shared egress address and merge UNRELATED runs into one
    # provisioning session. No header => no sharing: every create gets its
    # own session (the churn-dedup only ever fires for clients that
    # deliberately identify themselves).
    client_id = request.headers.get("X-TCSEXAM-Client-Id")
    # Effective run-id, validated into request["run_id"] by the auth
    # middleware ("" when absent/invalid/mode=off): the session's owner.
    run_id = request.get("run_id") or ""
    token_id = request.headers.get("X-TCSEXAM-Token-Id") or ""
    key = None
    if client_id:
        key = (
            token_id or "-",
            image,
            client_id,
            run_id,
            n_shards,
            instance_set,
        )
    try:
        session = store.begin_create_group(
            key, image, payload_files, resources or None, ttl, n_shards,
            # Creator identity: rides begin_create_group's identity parameter
            # into the journal's register event, so the reconciliation API's
            # creator_identity is set.
            identity=request.get("identity") or request.remote or "",
            instance_set=instance_set,
            run_id=run_id,
            token_id=token_id,
            attrs=request.get("attrs") or {},
        )
    except SessionsFullError as exc:
        return _json_error(503, str(exc), error_class="transient")
    except GlobalSandboxCapError as exc:
        return _json_error(503, str(exc), error_class="transient")
    except ValueError as exc:
        # Store-side validation (n_shards backstop, session-level quotas):
        # 400 with the same wording shape as the handler's own checks.
        return _json_error(400, str(exc))
    except Exception as exc:  # noqa: BLE001 - platform failures reach the client
        message = f"judge session create failed: {type(exc).__name__}: {exc}"
        if _is_transient_platform_error(exc) and not isinstance(exc, ValueError):
            message += f" (transient platform error, {_TRANSIENT_HINT})"
            return _json_error(500, message, error_class="transient")
        return _json_error(500, message, error_class="infra_error")
    base_url = f"{request.app['config'].public_url()}/v1/judge/sessions/{session.session_id}"
    # Persist the creation-time judge_payload verbatim (best-effort;
    # oversized skips with a WARN inside).
    _persist_creation_payload(store, session.session_id, payload_files)
    # Creation is asynchronous: 202 with the session registered as
    # "provisioning". Journal single-writer invariant: NO register/ready
    # hooks here — _register_group wrote register, _provision_group writes
    # the ready/failed flip.
    return web.json_response(
        {
            "session_id": session.session_id,
            "base_url": base_url,
            "url": base_url,
            "image": session.image,
            "n_shards": session.n_shards,
            "instance_set": session.instance_set,
            "expires_at": session.expires,
            "status": session.status,
        },
        status=202,
    )


def _owner_mismatch(owner: str, request: web.Request) -> bool:
    """Run-ownership verdict for one request.

    ``owner`` non-empty and the request's effective run-id differs -> deny.
    ``owner`` empty (the session was created without a run-id) ->
    unrestricted: local and legacy callers that never send run-ids keep
    working. Run-id is a caller-DECLARED label, not a credential: the check
    isolates callers acting under their declared identities (and keeps one
    attempt's session/archive/payload access scoped to its own run); a
    malicious caller holding the same shared service token can declare any
    run-id — resisting that needs per-run credentials or an equivalent
    authorization layer (out of scope).
    """
    return bool(owner) and (request.get("run_id") or "") != owner


def _session_owner(store: "JudgeSessionStore", sid: str) -> str | None:
    """The owning run-id of sid, or None when sid is unknown everywhere.

    Resolution order: the live table, the recent destroyed tail (the tail
    record keeps its run_id, so a post-DELETE read still checks ownership),
    then the replayed journal (service restarts). "" means the session
    exists but is unowned (created without a run-id).
    """
    session = store.get(sid)
    if session is not None:
        return getattr(session, "run_id", "") or ""
    for destroyed in getattr(store, "_destroyed", ()):
        if destroyed.session_id == sid:
            return getattr(destroyed, "run_id", "") or ""
    journal = getattr(store, "_journal", None)
    sessions = getattr(journal, "sessions", None)
    if isinstance(sessions, dict) and sid in sessions:
        return getattr(sessions[sid], "run_id", "") or ""
    return None


def _deny_wrong_owner(
    store: "JudgeSessionStore", sid: str, request: web.Request
) -> web.Response | None:
    """The ownership gate shared by every session-level endpoint: a wrong
    run-id answers EXACTLY like an unknown sid — the same 404 with the
    ``unknown judge session {sid}`` body — so the check never leaks whether
    the session exists. Returns the denial response, or None when the
    request may proceed."""
    owner = _session_owner(store, sid)
    if owner is not None and _owner_mismatch(owner, request):
        return _json_error(404, f"unknown judge session {sid}")
    return None


def _handle_session_ids_query(request: web.Request, store: "JudgeSessionStore") -> web.Response:
    """The verifier's chain cap-check (``?session_ids=a,b,c``) with run
    ownership applied: a sid owned by a different run-id reports
    ``present=false`` with its counts withheld and never enters the chain
    total — indistinguishable from an unknown sid. Requires store._journal
    (the caller checks)."""
    ids = [x for x in (s.strip() for s in request.query["session_ids"].split(",")) if x]
    rows = []
    total = 0
    for sid in ids:
        js = store._journal.sessions.get(sid)
        visible = js is not None and not _owner_mismatch(
            _session_owner(store, sid) or "", request
        )
        hidden = store._journal.session_submission_count(sid) if visible else 0
        total += hidden
        rows.append(
            {
                "session_id": sid,
                "submissions": hidden,
                "public_submissions": (
                    len(js.public_submissions) if visible and js is not None else 0
                ),
                "present": visible,
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


async def handle_session_status(request: web.Request) -> web.Response:
    from .sessions_base import _unknown_or_gone

    store: JudgeSessionStore = request.app["judge_sessions"]
    denied = _deny_wrong_owner(store, request.match_info["sid"], request)
    if denied is not None:
        return denied
    session = store.get(request.match_info["sid"])
    if session is None:
        return _unknown_or_gone(store, request.match_info["sid"])
    live = [s for s in session.shards if s.index not in session.failed_shards]
    return web.json_response(
        {
            "session_id": session.session_id,
            "image": session.image,
            "instance_set": session.instance_set,
            "created": session.created,
            "last_active": session.last_active,
            "expires_at": session.expires,
            "n_shards": session.n_shards,
            "status": session.status,
            "error": session.error,
            "failed_shards": len(session.failed_shards),
            "live_shards": len(live),
            "tunnel_connected": store._tunnels is not None
            and bool(live)
            and all(store._tunnels.is_connected(shard.app_name) for shard in live),
        }
    )


async def handle_session_list(request: web.Request) -> web.Response:
    """Verifier-only session listing: live sessions plus the recent destroyed
    tail, created-desc. Rows carry ``status``/``error`` (the async-creation
    state) and the shard count (for cleanup/reconciliation). All listing modes
    exclude sessions owned by another run, including the destroyed tail.
    """
    store: JudgeSessionStore = request.app["judge_sessions"]
    if not _valid_archive_token(request, store):
        return _json_error(403, "valid archive token required")
    # Reconciliation queries: ?client_ip=<identity|self> (per-identity
    # accounting — unsafe behind shared egress, ops observability only) and
    # ?session_ids=a,b,c (the verifier's chain cap-check — the run's
    # declared session chain is the accounting unit). The chain query is
    # answered here with run ownership applied; the client_ip query is
    # delegated to the base handler, which only touches store._journal
    # (the sharded sessions lack the caller fields the base listing branch
    # reads).
    if "session_ids" in request.query and store._journal is not None:
        return _handle_session_ids_query(request, store)
    if "client_ip" in request.query or "session_ids" in request.query:
        from .sessions_base import handle_session_list as _base_handle_session_list

        return await _base_handle_session_list(
            request,
            visible=lambda session: not _owner_mismatch(
                getattr(session, "run_id", "") or "", request
            ),
        )
    return web.json_response(
        [
            {
                "session_id": session.session_id,
                "image": session.image,
                "family": image_family(session.image),
                "instance_set": getattr(session, "instance_set", "hidden"),
                "n_shards": session.n_shards,
                "created": session.created,
                "last_active": session.last_active,
                "destroyed": session.destroyed,
                "run_id": getattr(session, "run_id", "") or "",
                "agent_name": getattr(session, "agent_name", "") or "",
                "attrs": getattr(session, "attrs", None) or {},
                "status": session.status,
                "error": session.error,
            }
            for session in store.list_sessions()
            if not _owner_mismatch(getattr(session, "run_id", "") or "", request)
        ]
    )


async def handle_session_delete(request: web.Request) -> web.Response:
    """Destroy known sessions idempotently. Unknown sessions and a wrong
    run-id answer the same 404; an owner can repeat DELETE after release
    while the session remains known in the tail or journal."""
    store: JudgeSessionStore = request.app["judge_sessions"]
    sid = request.match_info["sid"]
    if _session_owner(store, sid) is None:
        return _json_error(404, f"unknown judge session {sid}")
    denied = _deny_wrong_owner(store, sid, request)
    if denied is not None:
        return denied
    stopped = await store.destroy(sid)
    return web.json_response({"ok": True, "stopped": stopped})


def _session_known_for_reads(store: "JudgeSessionStore", sid: str) -> bool:
    """Whether sid may have readable records: live, in the recent destroyed
    tail, or journaled. The archive/payload persistence layers survive
    destroy, reap AND service restarts BY DESIGN (the journal is replayed at
    startup; the verifier pulls records after the session is released), so a
    destroyed-but-known session must not collapse into the "unknown sid" 404
    family. Stores without a destroyed tail / journal (test fakes) answer
    False for unknown sids."""
    if store.get(sid) is not None:
        return True
    checker = getattr(store, "is_destroyed", None)
    if callable(checker) and checker(sid):
        return True
    journal = getattr(store, "_journal", None)
    sessions = getattr(journal, "sessions", None)
    return isinstance(sessions, dict) and sid in sessions


async def handle_session_archive(request: web.Request) -> web.Response:
    """Verifier-only raw-record archive (written by ``_write_archive``).

    Credential-gated, not network-gated: the agent and the verifier share
    the task container, so the ONLY thing telling them apart is the
    ``X-TCSEXAM-Archive-Token`` header baked into the task package's tests/
    (mounted at verify time only — the agent phase can never read it). Every
    failure mode answers 404, never 401/403: a wrong or missing token, an
    unconfigured token (endpoint disabled), an unknown sid, and a session
    with no archive yet are all indistinguishable from an unknown path.
    Purely read-only: no cap counting (a GET never matches the is_submit
    predicate anyway), no last_active touch, no journal write — a verifier
    pull is not agent behavior.
    """
    store: JudgeSessionStore = request.app["judge_sessions"]
    sid = request.match_info["sid"]
    token = getattr(store._config, "archive_token", "")
    if not token or request.headers.get(ARCHIVE_TOKEN_HEADER, "") != token:
        return _json_error(404, f"unknown judge session {sid}")
    if not _session_known_for_reads(store, sid):
        return _json_error(404, f"unknown judge session {sid}")
    # Run ownership: same uniform 404 — a wrong run-id with a VALID archive
    # credential is indistinguishable from an unknown sid (the verifier of
    # one attempt cannot pull another attempt's records).
    denied = _deny_wrong_owner(store, sid, request)
    if denied is not None:
        return denied
    # Path safety: only service-generated sids (jsess-<uuid>) pass the
    # store.get check above, so the f-string cannot traverse.
    state_dir = getattr(store._config, "state_dir", None)
    try:
        if not state_dir:
            raise FileNotFoundError
        body = (Path(state_dir) / "judge_archive" / f"{sid}.json").read_bytes()
    except FileNotFoundError:
        return _json_error(
            404,
            f"judge session {sid} has no archive yet "
            "(no /submissions fetch has been aggregated for it)",
        )
    except OSError:  # unreadable archive: the endpoint face stays clean (no 500)
        return _json_error(404, f"judge archive for session {sid} is unreadable")
    return web.Response(body=body, content_type="application/json")


def _payload_gate(request: web.Request, store: "JudgeSessionStore", sid: str) -> web.Response | None:
    """The payload endpoints' gate — identical discipline to the archive
    endpoint above: X-TCSEXAM-Archive-Token (missing/wrong/unconfigured),
    an unknown/destroyed session, and a wrong run-id all collapse into the
    SAME 404, so the persistence layer's existence is indistinguishable
    from an unknown path. Returns the error response, or None when the
    gate passes."""
    token = getattr(store._config, "archive_token", "")
    if not token or request.headers.get(ARCHIVE_TOKEN_HEADER, "") != token:
        return _json_error(404, f"unknown judge session {sid}")
    if not _session_known_for_reads(store, sid):
        return _json_error(404, f"unknown judge session {sid}")
    return _deny_wrong_owner(store, sid, request)


async def handle_session_payload(request: web.Request) -> web.Response:
    """Verifier-only creation-payload download: the session's judge_payload
    repacked as tar.gz. Read-only like the archive endpoint — no last_active
    touch, no journal write."""
    store: JudgeSessionStore = request.app["judge_sessions"]
    sid = request.match_info["sid"]
    denied = _payload_gate(request, store, sid)
    if denied is not None:
        return denied
    state_dir = getattr(store._config, "state_dir", None)
    root = Path(state_dir) / "judge_payload" / sid if state_dir else None
    try:
        if root is None or not root.is_dir():
            raise FileNotFoundError
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    tf.add(p, arcname=str(p.relative_to(root)))
    except FileNotFoundError:
        return _json_error(
            404,
            f"judge session {sid} has no creation payload persisted "
            "(the client sent no judge_payload at create, or it exceeded the persist cap)",
        )
    except OSError:
        return _json_error(404, f"judge payload for session {sid} is unreadable")
    return web.Response(body=buf.getvalue(), content_type="application/gzip")


def _submission_payload_dir(store: "JudgeSessionStore", sid: str) -> Path | None:
    state_dir = getattr(store._config, "state_dir", None)
    if not state_dir:
        return None
    return Path(state_dir) / "judge_submissions" / sid


async def handle_session_payload_submissions(request: web.Request) -> web.Response:
    """Index of a session's persisted submission bodies:
    ``{"session_id": ..., "submissions": [1, 2, ...]}``. Same gate and 404
    discipline as the archive endpoint."""
    store: JudgeSessionStore = request.app["judge_sessions"]
    sid = request.match_info["sid"]
    denied = _payload_gate(request, store, sid)
    if denied is not None:
        return denied
    root = _submission_payload_dir(store, sid)
    try:
        if root is None or not root.is_dir():
            raise FileNotFoundError
        seqs = sorted(
            int(p.name[: -len(".tar.gz")]) for p in root.iterdir() if p.name.endswith(".tar.gz")
        )
    except FileNotFoundError:
        return _json_error(
            404,
            f"judge session {sid} has no submission payload persisted "
            "(no accepted submission since the persistence layer went live)",
        )
    return web.json_response({"session_id": sid, "submissions": seqs})


async def handle_session_payload_submission(request: web.Request) -> web.Response:
    """One persisted submission body verbatim — the exact bytes the client
    POSTed to {sid}/submit. Same gate and 404 discipline as the archive
    endpoint."""
    store: JudgeSessionStore = request.app["judge_sessions"]
    sid = request.match_info["sid"]
    denied = _payload_gate(request, store, sid)
    if denied is not None:
        return denied
    try:
        seq = int(request.match_info["seq"])  # digits-only: no traversal
    except (TypeError, ValueError):
        return _json_error(404, f"unknown submission {request.match_info['seq']!r}")
    root = _submission_payload_dir(store, sid)
    try:
        if root is None:
            raise FileNotFoundError
        body = (root / f"{seq:03d}.tar.gz").read_bytes()
    except FileNotFoundError:
        return _json_error(404, f"judge session {sid} has no persisted submission {seq}")
    except OSError:
        return _json_error(404, f"submission payload {seq} for session {sid} is unreadable")
    return web.Response(body=body, content_type="application/gzip")



# --------------------------------------------------------------------------- #
# Sharded-session fan-out and merge
# --------------------------------------------------------------------------- #
async def _stop_sandbox_best_effort(executor: Any, app_name: str) -> None:
    """stop_app with best-effort error swallowing (worker recycle helper for
    the shard-failure paths; failures are logged, never raised)."""
    stopper = getattr(executor, "stop_app", None)
    if stopper is None:
        return
    try:
        await stopper(app_name)
    except Exception:  # noqa: BLE001
        LOGGER.exception("failed to reap the worker of %s", app_name)


def _mark_shard_failed(
    store: "JudgeSessionStore", session: JudgeSession, index: int, reason: str
) -> None:
    """Mark a shard failed mid-judging: permanent exclusion from the live
    set (a re-joined shard would have missed submissions and its sequence
    numbers would misalign the merge). Idempotent; logged once. When this
    was the LAST live shard, the whole session flips to failed. The failed
    shard's worker is reaped."""
    if index in session.failed_shards:
        return
    session.shard_down_ticks.pop(index, None)
    session.failed_shards[index] = reason
    LOGGER.warning(
        "judge session %s shard %d marked failed: %s", session.session_id, index, reason
    )
    store._fail_session_if_all_shards_dead(session)
    shard_app = next((s.app_name for s in session.shards if s.index == index), None)
    executor = getattr(store, "_executor", None)
    if shard_app is not None and executor is not None:
        asyncio.ensure_future(_stop_sandbox_best_effort(executor, shard_app))


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _align_entries(
    shard_payloads: list[dict[str, Any] | None],
    n: int,
    failed: dict[int, str],
    k: int,
) -> tuple[list[tuple[int, dict[str, Any]]], list[int], bool]:
    """Collect the shards' k-th submission entries: a failed shard
    contributes its archived entry when it judged the submission before
    dying, and counts as absent otherwise. Returns ``(entries, absent,
    live_missing)`` — the shared alignment spine of both aggregations."""
    entries: list[tuple[int, dict[str, Any]]] = []
    absent: list[int] = []  # shards absent from THIS entry due to failure
    live_missing = False  # a live shard has not received this entry yet
    for i in range(n):
        p = shard_payloads[i] if i < len(shard_payloads) else None
        subs = (p.get("submissions") or []) if p else []
        if i in failed:
            cand = subs[k] if k < len(subs) else None
            if cand is not None and str(cand.get("status")) != "running":
                # Judged before the shard died: keep the archived records.
                entries.append((i, cand))
            else:
                absent.append(i)
        elif k < len(subs):
            entries.append((i, subs[k]))
        else:
            live_missing = True
    return entries, absent, live_missing


def _merged_status(entries: list[tuple[int, dict[str, Any]]], live_missing: bool) -> str:
    """One submission's status across shards: running propagates; ok only
    when EVERY shard is ok; otherwise the first non-ok, non-running status
    surfaces (timeout/judge_error — the historical precedence)."""
    statuses = {str(e.get("status")) for _, e in entries}
    if "running" in statuses or live_missing:
        return "running"
    if statuses == {"ok"}:
        return "ok"
    return next(
        (s for s in (e.get("status") for _, e in entries) if s not in ("ok", "running")),
        "judge_error",
    )


def five_numbers(records: list[Any]) -> dict[str, Any]:
    """Aggregate one shard's raw per-instance records into the five numbers.

    Three-way per instance, with the direction read off the anchors. B == K
    instances provide no direction and are excluded from these statistics;
    their raw outcomes remain in the archive, including older workers' records.
    K > B → a MAX problem (bigger A is better); K < B → MIN. Objective
    problems compare A vs B by that direction; solve-type problems carry
    A, B ∈ {0, 1}, so the same comparison IS the solve-type rule — "I
    solved and the baseline didn't" (better), "both solved or neither did"
    (equal), "the baseline solved and I didn't" (worse). ``delta`` is the
    direction-normalized total improvement: Σ(A−B) for max problems,
    Σ(B−A) for min (positive = better). ``invalid`` records (the model's
    own invalid solution / timeout / crash) count as ``worse``; only
    ``error`` records (the judging pipeline's own fault) count as
    ``failed`` — the model is never blamed for infrastructure.
    """
    better = equal = worse = failed = 0
    delta = 0.0
    for rec in records:
        # An explicitly unmeasured baseline stays outside these statistics,
        # including invalid/unknown solver outcomes. Preserve their true status
        # in feedback instead of treating missing reference data as validity.
        if (isinstance(rec, dict) and rec.get("B") is None
                and _is_num(rec.get("K"))
                and rec.get("anchor_baseline_unsolved") is True):
            continue
        if not isinstance(rec, dict) or rec.get("status") == "error":
            failed += 1
            continue
        a, b, k = rec.get("A"), rec.get("B"), rec.get("K")
        if _is_num(b) and _is_num(k) and b == k:
            continue
        if b is None and rec.get("status") == "ok":
            # B=null (the shipped baseline did not solve this instance under
            # judging conditions): excluded from the five-numbers
            # aggregation; the record's A is retained in the archive layer
            # and counted when the final scoring framework replays it.
            continue
        if rec.get("status") != "ok" or not (_is_num(a) and _is_num(b) and _is_num(k)):
            worse += 1  # invalid: the model's own fault
            continue
        d = (a - b) if float(k) > float(b) else (b - a)
        if d > 0:
            better += 1
        elif d < 0:
            worse += 1
        else:
            equal += 1
        delta += d
    if float(delta).is_integer():
        delta = int(delta)
    return {"better": better, "equal": equal, "worse": worse, "delta": delta, "failed": failed}


#: Parenthetical containing a numeric comparison ("(15 > 12)", "(11 < 12)")
#: — the shape judging logics use when their status wording embeds the
#: anchor; see :func:`_scrub_k`.
_CMP_PAREN = re.compile(r"\([^()]*\d\s*(?:<=|>=|<|>)\s*\d[^()]*\)")


def _scrub_k(detail: str, k: Any) -> str:
    """Redact K from a record's detail (hidden channel: K never leaves the
    service). The K FIELD is dropped structurally by :func:`_hidden_record`;
    this is the second line for the free-text detail. Two layers:

    * Comparison parentheticals — a few judging logics embed the anchor in
      their status wording ("valid but above optimum (15 > 12)"). The
      numeric content of any ``(… < …)``/``(… > …)`` parenthetical is
      blanked outright. Arrows ("a -> b") don't match; a group without
      digits blanks nothing.
    * The record's own K value, token-bounded — a safety net for judging
      logics that carry the true anchor in the record (objective
      problems). Skipped for flag values K ∈ {0, 1}: there the record's K
      is not the anchor (the comparison layer above owns that case) and
      scrubbing "1" would mangle ordinary wording ("solver exited with
      code 1"). Token bounds (no digit/dot on either side) keep a budget
      like 1200s safe from K=12.
    """
    if not detail:
        return detail
    detail = _CMP_PAREN.sub(
        lambda m: re.sub(r"\d+(?:\.\d+)?", "?", m.group(0)), detail
    )
    if not _is_num(k):
        return detail
    fk = float(k)
    if fk in (0.0, 1.0):
        return detail
    forms = {str(fk)}  # float rendering, e.g. "12.0"
    if fk.is_integer():
        forms.add(str(int(fk)))  # integral rendering, e.g. "12"
    else:
        forms.add(repr(fk))  # shortest round-trip, e.g. "12.5"
    for form in sorted(forms, key=len, reverse=True):
        detail = re.sub(r"(?<![\d.])" + re.escape(form) + r"(?![\d.])", "?", detail)
    return detail


def _hidden_record(rec: dict[str, Any]) -> dict[str, Any]:
    """One raw per-instance record stripped for the HIDDEN channel (final
    feedback form): exactly ``{instance, A, B, status, detail}`` — the
    baseline B stays (the model ships the same baseline locally), K is
    dropped and scrubbed (see :func:`_scrub_k`).
    """
    return {
        "instance": rec.get("instance"),
        "A": rec.get("A"),
        "B": rec.get("B"),
        "status": rec.get("status"),
        "detail": _scrub_k(str(rec.get("detail") or ""), rec.get("K")),
    }



def aggregate_submissions(
    shard_payloads: list[dict[str, Any] | None],
    *,
    n_shards: int | None = None,
    failed: dict[int, str] | None = None,
    size_cache: dict[int, int] | None = None,
) -> dict[str, Any]:
    """Aggregate N shard ``/submissions`` payloads into one caller-facing
    hidden-channel history: five numbers PLUS per-instance records stripped
    of K (the final feedback form).

    The shards received the same submissions in the same order, so entries
    align by index. A merged submission is ``ok`` only when EVERY shard is
    ``ok``; its five numbers are the plain SUM over shards (each shard
    aggregates its own slice with :func:`five_numbers`; no weights —
    sharding just partitions the judging set). ``best`` is the submission id
    with the best (better, delta) lexicographic key among ok entries (the
    presentation-layer best; ``None`` while nothing has finished ok).

    Every non-running entry also carries ``records``: the whole-set
    per-instance table — each contributing shard's raw records stripped by
    :func:`_hidden_record` (K dropped AND scrubbed from detail text; B
    stays), concatenated and sorted by instance name. A shard absent from
    the entry (failed before judging it) simply contributes no records —
    its slice shows up in the entry's ``failed``/``failed_shards`` counts;
    a shard whose entry produced no per-instance records (timeout /
    judge_error / build_error / pipeline regression) contributes none
    either (the five numbers fold that slice in). ``records`` is ``None``
    while the merged entry is still ``running``, else a list (empty when
    no shard produced per-instance records for it).

    Failed shards (``failed``: index -> reason, empty/None = no failures):
    an entry the shard had already judged before dying keeps its ARCHIVED
    records (history is never rewritten backwards); an entry it never judged
    counts fully toward ``failed``, sized by the learned per-shard judging-
    set size (``size_cache``, updated in place from every fetched payload —
    the first entry carrying records fixes a shard's size; a shard that
    never reported is ESTIMATED from the known shards' mean — modulo slicing
    keeps shard sizes within 1 instance of each other, so the estimate is
    off by at most one instance; with nothing known at all, 0). Submission-level fold-ins for
    entries without per-instance records: ``timeout`` (the solver's own
    overrun) and ``build_error`` count the shard's size toward ``worse``;
    ``judge_error`` and a records-less ``ok`` that is not a build error (a
    judging-pipeline regression) count toward ``failed``. With ``n_shards``
    > 1 every merged entry carries a numeric ``failed_shards`` key = the
    number of shards ABSENT from that entry because they failed (0 for
    entries a failed shard had judged before dying); n_shards == 1 omits the
    key (≡ 0).
    """
    failed = failed or {}
    n = n_shards if n_shards is not None else len(shard_payloads)
    # Size learning: the first entry carrying records fixes the shard's
    # judging-set size (the slice is constant per shard).
    cache = size_cache if size_cache is not None else {}
    for i, p in enumerate(shard_payloads):
        if not p:
            continue
        for e in p.get("submissions") or []:
            recs = e.get("records")
            if isinstance(recs, list):
                cache[i] = len(recs)
                break

    def _size(index: int) -> int:
        if index in cache:
            return cache[index]
        known = list(cache.values())
        if known:
            # Never-reported shard: estimate from the known shards' mean
            # (modulo slicing keeps shard sizes within 1 instance of each
            # other, so this is off by at most one instance).
            return max(1, round(sum(known) / len(known)))
        return 0  # nothing known at all: under-count, never mis-count

    count = max((len(p.get("submissions") or []) for p in shard_payloads if p), default=0)
    merged: list[dict[str, Any]] = []
    best_id: int | None = None
    best_key: tuple[float, float] | None = None
    for k in range(count):
        entries, absent, live_missing = _align_entries(shard_payloads, n, failed, k)
        status = _merged_status(entries, live_missing)
        details = [str(e.get("detail") or "") for _, e in entries]
        entry: dict[str, Any] = {
            "submission": int(entries[0][1].get("submission", k)) if entries else k,
            "ts": max((float(e.get("ts") or 0.0) for _, e in entries), default=0.0),
            "status": status,
            "detail": "; ".join(d for d in details if d),
        }
        if status == "running":
            entry.update(better=None, equal=None, worse=None, delta=None, failed=None,
                         records=None)
        else:
            five = {"better": 0, "equal": 0, "worse": 0, "delta": 0, "failed": 0}
            for i, e in entries:
                est = str(e.get("status"))
                recs = e.get("records")
                if est == "ok" and isinstance(recs, list):
                    f = five_numbers(recs)
                    for key in five:
                        five[key] += f[key]
                elif est == "timeout" or (est == "ok" and str(e.get("detail") or "") == "build_error"):
                    # The model's own overrun / build crash: the whole slice
                    # counts as worse (sized from the learned cache).
                    five["worse"] += _size(i)
                elif est != "running":
                    # judge_error, or an ok entry without records that is not
                    # a build error (judging-pipeline regression): infra —
                    # the whole slice counts as failed, never worse.
                    five["failed"] += _size(i)
            five["failed"] += sum(_size(i) for i in absent)
            if float(five["delta"]).is_integer():
                five["delta"] = int(five["delta"])
            entry.update(five)
            # Per-instance table (final feedback form): concatenate every
            # contributing shard's records, K stripped + scrubbed, sorted by
            # instance name. Shards without per-instance records for this
            # entry (absent after failing, or timeout/judge_error/
            # build_error/regression) contribute nothing — their slices are
            # already folded into the five numbers above.
            records: list[dict[str, Any]] = []
            for _i, e in entries:
                recs = e.get("records")
                if not isinstance(recs, list):
                    continue
                for rec in recs:
                    if isinstance(rec, dict):
                        records.append(_hidden_record(rec))
            records.sort(key=lambda r: str(r.get("instance")))
            entry["records"] = records
            if status == "ok":
                key = (five["better"], five["delta"])
                if best_key is None or key > best_key:
                    best_key = key
                    best_id = entry["submission"]
        if n > 1:
            entry["failed_shards"] = len(absent)
        merged.append(entry)
    result: dict[str, Any] = {
        "submissions": merged,
        "best": best_id,
        "count": len(merged),
        "shards": n,
    }
    if n > 1:
        result["failed_shards"] = len(failed)
    return result


def aggregate_public(
    shard_payloads: list[dict[str, Any] | None],
    *,
    n_shards: int | None = None,
    failed: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Public-channel variant of :func:`aggregate_submissions`: per-instance
    FULL DETAIL instead of the five numbers.

    The public instances are the caller's own — returning instance names,
    A values and validity leaks nothing. The anchors (B/K) are stripped
    here all the same: detail records carry exactly ``{instance, A, status,
    detail}``. Shards simply concatenate (their union IS the whole public
    set; sorted by instance name for determinism); a shard absent from an
    entry (failed before judging it) leaves its slice out and shows up in
    the entry's ``failed_shards`` count. Entries whose judging produced no
    per-instance records (running / timeout / judge_error / build_error /
    pipeline regression) carry ``records: null``.

    Side channel (every public instance the model can see must be run AND
    reported): a shard entry's ``excluded_records`` — the full records of
    B==K keys (reason ``b_equals_k``) and marked no-anchor practice keys
    (reason ``practice_no_anchors``) that the worker diverted out of
    ``records`` to keep the hidden five numbers untouched — are appended to
    the same reply array, stripped of B/K but keeping ``reason``/``detail``,
    and merged into the by-instance sort. Payloads without the field (older
    workers) are treated as empty — old and new workers mix freely.

    Submission-level passthrough: the worker stamps each entry with
    ``pack_sha256`` (the submitted tar's sha256); it is forwarded on the
    merged outer entry so the caller can verify the judging saw exactly the
    pack it sent. Entries from workers without the field simply omit the
    key.
    """
    failed = failed or {}
    n = n_shards if n_shards is not None else len(shard_payloads)
    count = max((len(p.get("submissions") or []) for p in shard_payloads if p), default=0)
    merged: list[dict[str, Any]] = []
    for k in range(count):
        entries, absent, live_missing = _align_entries(shard_payloads, n, failed, k)
        status = _merged_status(entries, live_missing)
        details = [str(e.get("detail") or "") for _, e in entries]
        entry: dict[str, Any] = {
            "submission": int(entries[0][1].get("submission", k)) if entries else k,
            "ts": max((float(e.get("ts") or 0.0) for _, e in entries), default=0.0),
            "status": status,
            "detail": "; ".join(d for d in details if d),
        }
        # pack_sha256 passthrough: the same tar fans out to every shard, so
        # any shard's value is correct; workers without the field omit the
        # key.
        pack = next(
            (e.get("pack_sha256") for _, e in entries if e.get("pack_sha256")),
            None,
        )
        if pack is not None:
            entry["pack_sha256"] = pack
        records: list[dict[str, Any]] | None = [] if status != "running" else None
        if records is not None:
            for _i, e in entries:
                recs = e.get("records")
                if not isinstance(recs, list):
                    # timeout / judge_error / build_error / regression: no
                    # per-instance detail exists for this shard's slice.
                    records = None
                    break
                for rec in recs:
                    if not isinstance(rec, dict):
                        continue
                    records.append(
                        {
                            "instance": rec.get("instance"),
                            "A": rec.get("A"),
                            "status": rec.get("status"),
                            "detail": str(rec.get("detail") or ""),
                        }
                    )
                # Side channel: B==K / no-anchor practice keys still report A
                # (B/K stripped, reason/detail kept); workers without the
                # field are treated as empty.
                for rec in e.get("excluded_records") or []:
                    if not isinstance(rec, dict):
                        continue
                    records.append(
                        {
                            "instance": rec.get("instance"),
                            "A": rec.get("A"),
                            "status": rec.get("status"),
                            "detail": str(rec.get("detail") or ""),
                            "reason": str(rec.get("reason") or ""),
                        }
                    )
        if records is not None:
            records.sort(key=lambda r: str(r.get("instance")))
        entry["records"] = records
        if n > 1:
            entry["failed_shards"] = len(absent)
        merged.append(entry)
    result: dict[str, Any] = {
        "submissions": merged,
        "count": len(merged),
        "shards": n,
    }
    if n > 1:
        result["failed_shards"] = len(failed)
    return result


def _write_archive(store: "JudgeSessionStore", session: JudgeSession) -> None:
    """Rewrite the session's raw-record archive atomically
    (``state_dir/judge_archive/<sid>.json``).

    Every shard's latest fetched /submissions payload (full per-instance
    records) plus the shard failure markers — the verifier recomputes
    metrics from HERE, and reconciliation replays trajectories from HERE.
    Best-effort: an archive failure never breaks the request path (logged
    only).
    """
    state_dir = getattr(store._config, "state_dir", None)
    if not state_dir:
        return
    try:
        base = Path(state_dir) / "judge_archive"
        base.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": session.session_id,
            "image": session.image,
            "instance_set": session.instance_set,
            "n_shards": session.n_shards,
            "created": session.created,
            "failed_shards": {
                str(i): reason for i, reason in sorted(session.failed_shards.items())
            },
            "shard_payloads": {
                str(i): session.shard_payloads[i] for i in sorted(session.shard_payloads)
            },
        }
        tmp = base / f"{session.session_id}.json.tmp"
        tmp.write_text(json.dumps(payload, indent=1, sort_keys=True))
        tmp.replace(base / f"{session.session_id}.json")
    except Exception:  # noqa: BLE001 - the archive must never break requests
        LOGGER.warning("judge archive write failed for %s", session.session_id, exc_info=True)


# --------------------------------------------------------------------------- #
# Submission-content persistence (audit: case studies and replay need every
# submission's body; judge_archive stores only per-instance scores, not
# submission content). Lifecycle: files survive destroy/reap, exactly like
# judge_archive; both layers are best-effort (failures logged, never break
# the request path).
# --------------------------------------------------------------------------- #
def _safe_payload_join(root: Path, rel: str) -> Path:
    """Join one payload_files path under root, rejecting traversal — the
    keys are client-supplied (create-time judge_payload), a ``..`` or
    absolute path must not escape the session directory."""
    dest = root / rel
    resolved = dest.resolve()
    if not str(resolved).startswith(str(root.resolve()) + "/"):
        raise ValueError(f"unsafe payload path {rel!r}")
    return resolved


def _persist_creation_payload(
    store: "JudgeSessionStore", sid: str, payload_files: dict[str, bytes] | None
) -> None:
    """Persist the creation-time judge_payload verbatim:
    ``state_dir/judge_payload/<sid>/<path...>`` — payload paths are
    worker-absolute, expanded under the sid dir with the leading slash
    stripped. Skipped (WARN) when oversized, unconfigured, empty, or on any
    error."""
    state_dir = getattr(store._config, "state_dir", None)
    if not state_dir or not payload_files:
        return
    total = sum(len(data) for data in payload_files.values())
    cap = store.cfg.payload_persist_max_bytes
    if total > cap:
        LOGGER.warning(
            "judge session %s creation payload %d bytes exceeds %d cap; not persisted",
            sid, total, cap,
        )
        return
    try:
        root = Path(state_dir) / "judge_payload" / sid
        for rel, data in payload_files.items():
            # Payload paths are worker-absolute (where the file lands in the
            # worker); strip the leading slash for the on-disk expansion so
            # /judge/x.py lands at judge_payload/<sid>/judge/x.py.
            dest = _safe_payload_join(root, rel.lstrip("/"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    except Exception:  # noqa: BLE001
        LOGGER.warning("creation payload persist failed for %s", sid, exc_info=True)


def _persist_submission_body(store: "JudgeSessionStore", sid: str, body: bytes) -> None:
    """Persist one accepted submission's body:
    ``state_dir/judge_submissions/<sid>/<seq:03d>.tar.gz`` — seq = existing
    file count + 1 (the directory itself is the counter, restart-safe; the
    numbers align with the journal's accept order, hidden and public share
    the sequence). Called AFTER the cap-accept block: 429-rejected bodies
    are never persisted. Written to a .tmp then renamed (atomic)."""
    state_dir = getattr(store._config, "state_dir", None)
    if not state_dir:
        return
    try:
        root = Path(state_dir) / "judge_submissions" / sid
        root.mkdir(parents=True, exist_ok=True)
        seq = sum(1 for p in root.iterdir() if p.name.endswith(".tar.gz")) + 1
        tmp = root / f"{seq:03d}.tar.gz.tmp"
        tmp.write_bytes(body)
        tmp.replace(root / f"{seq:03d}.tar.gz")
    except Exception:  # noqa: BLE001
        LOGGER.warning("submission body persist failed for %s", sid, exc_info=True)



async def _call_shards(
    store: JudgeSessionStore,
    session: JudgeSession,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    timeout: float,
) -> dict[int, tuple[int, dict[str, str], bytes]]:
    """Bounded fan-out to the session's LIVE shards.

    One store-wide semaphore (``fanout_concurrency``) bounds concurrency —
    hundreds of shards x a multi-MB submit body would otherwise spike egress
    bandwidth and memory; every leg is wrapped in its own ``wait_for``
    timeout so one wedged shard cannot stall the gather. A live shard that
    answers 5xx, times out, or raises is marked failed on the spot (its
    instances count toward the aggregate's ``failed`` number from now
    on); 4xx answers are left to the caller —
    every shard validates the same tar, so a 4xx is the submission's
    fault, not the shard's.
    """
    live = [s for s in session.shards if s.index not in session.failed_shards]
    results: dict[int, tuple[int, dict[str, str], bytes]] = {}

    async def _one(shard: Shard) -> None:
        async with store._fanout_sem:
            try:
                results[shard.index] = await asyncio.wait_for(
                    store._tunnels.call(shard.app_name, method, path, body=body),
                    timeout=timeout,
                )
            except Exception as exc:  # noqa: BLE001 - timeout / transport
                # Cold-worker grace: the tunnel's READY precedes the
                # in-worker worker actually serving (heavy images import/load
                # for minutes). A transport failure within the boot grace
                # after the ready-flip is NOT a shard failure — the caller
                # 502s transient and the client retries, instead of
                # permanently degrading the session. 5xx is different: an
                # answering worker is up.
                if (
                    session.ready_at
                    and time.time() - session.ready_at
                    < store.cfg.shard_boot_call_grace_seconds
                ):
                    LOGGER.info(
                        "judge session %s shard %d: %s %s transport failure inside boot "
                        "grace (%.0fs since ready), not marking failed: %s: %s",
                        session.session_id, shard.index, method, path,
                        time.time() - session.ready_at, type(exc).__name__, exc,
                    )
                    return
                _mark_shard_failed(
                    store, session, shard.index, f"{method} {path}: {type(exc).__name__}: {exc}"
                )
                return
        status, _headers, payload = results[shard.index]
        if status >= 500:
            _mark_shard_failed(
                store,
                session,
                shard.index,
                f"{method} {path}: HTTP {status}: {payload[:200].decode(errors='replace')}",
            )

    await asyncio.gather(*(_one(shard) for shard in live))
    return results


async def _fanout_submit(
    store: JudgeSessionStore, session: JudgeSession, request: web.Request
) -> web.Response:
    """Fan one /submit out to every LIVE shard with the same body (bounded).

    Acceptance is per-shard now: every shard that answers 202 keeps the
    submission, and the caller gets an overall 202 as long as AT LEAST ONE
    live shard accepted. The submission-id consistency check runs over the
    accepting shards only — a failed shard leaves the live set, so its
    missed ids can no longer misalign the merge on retry (an all-or-nothing
    502 would make a retried submit land as #k+1 on the shards that had
    accepted and #k on the failed one, permanently diverged).
    """
    body = await request.read()
    results = await _call_shards(
        store, session, "POST", "/submit", body=body,
        timeout=store.cfg.submit_fanout_timeout_seconds,
    )
    # 4xx (bad submission tar) passes through as-is — every shard validates
    # the same tar and would 4xx in lockstep; the fault is the submission's,
    # so the shard is NOT marked failed and the harness must NOT retry.
    for _idx, (status, _headers, payload) in sorted(results.items()):
        if status != 202 and status < 500:
            return web.Response(status=status, body=payload)
    accepted = {idx: r for idx, r in results.items() if r[0] == 202}
    if not accepted:
        # Every live shard failed (5xx/timeout; all marked failed inside
        # _call_shards): nothing was accepted, so a client retry is safe.
        # The relay's submission-cap count from earlier in this request is
        # NOT rolled back — "counted at accept" is unconditional (a
        # zero-cost probe must not be free; no compensating journal event
        # either, the append-only semantics stays intact). The wording keeps
        # the tunnel family's transient hint so the harness retries.
        return web.Response(
            status=502,
            body=b"502 Bad Gateway: no live shard accepted the submission (please try again)",
        )
    ids = []
    for _status, _headers, payload in accepted.values():
        try:
            ids.append(int(json.loads(payload.decode()).get("submission")))
        except Exception:  # noqa: BLE001
            return _json_error(502, "malformed submit response from a shard")
    if len(set(ids)) != 1:
        # Shards assign ids independently; identical submit sequences should
        # keep them identical among the ACCEPTING shards. A divergence means
        # an accepting shard missed an earlier submit — the merged history
        # would misalign, so surface it, don't hide it.
        LOGGER.error("shard submission ids diverged for %s: %s", session.session_id, ids)
        return _json_error(502, f"shard submission ids diverged: {ids}")
    return web.json_response(
        # Era offset (hibernate wake): a wake re-created worker restarts its
        # id sequence at 0; the client-facing sequence stays continuous with
        # the archived pre-hibernate numbering.
        {"submission": ids[0] + session.submit_era_base, "status": "running", "shards": session.n_shards},
        status=202,
    )


def _latest_submission_complete(session: JudgeSession, payloads: dict[int, dict]) -> bool:
    """Whether judging has SETTLED for the latest submission: every live
    shard carries an entry for the newest submission id with a TERMINAL
    status (anything but ``running`` — ``ok``/``timeout``/``build_error``/
    ``judge_error`` all count, records-bearing or not). Sessions with no
    submissions at all count as settled (nothing is in flight).

    The status is authoritative: a terminal entry may legitimately carry
    NO per-instance records (all-folded timeout/build_error, judge_error,
    pipeline-regression ok — aggregate semantics: ``records`` is None only
    while running). Used by the delivered marker and the pre-hibernate
    probe."""
    latest: int | None = None
    for payload in payloads.values():
        for entry in payload.get("submissions", []):
            sub = entry.get("submission")
            if sub is not None and (latest is None or int(sub) > latest):
                latest = int(sub)
    if latest is None:
        return True
    for shard in session.shards:
        idx = shard.index
        if idx in session.failed_shards:
            continue
        payload = payloads.get(idx)
        if payload is None:
            return False
        entry = next(
            (e for e in payload.get("submissions", []) if e.get("submission") == latest),
            None,
        )
        if entry is None or entry.get("status") == "running":
            return False
    return True


def _era_union_payloads(session: JudgeSession, payloads: dict[int, dict]) -> None:
    """Merge post-wake shard payloads (RESTARTED local submission ids) into
    each shard's continuous pre-hibernate history, offsetting the fresh ids
    by ``session.submit_era_base`` in place — the merged history never
    loses pre-hibernate submissions and ids never collide (base = archived
    max + 1).

    THE single era-merge caliber, shared by ``_merged_submissions``
    (client fetch) and the hibernate probe: writing a raw post-wake payload
    straight over the archive would truncate the session's history to the
    current era on every wake+re-hibernate cycle.

    Merge rule: archived ids below ``submit_era_base`` are the frozen
    pre-wake history; ids at or above it belong to the CURRENT era, for
    which the fresh worker payload is authoritative — same-id entries are
    REPLACED, never dropped. An append-only ``> seen`` filter would pin a
    mid-judging ``running`` entry forever (the fresh terminal state never
    overwrites it) and live-lock every post-wake submission's poll.

    A shard without any archived payload merges against an empty history;
    its fresh entries are still offset — every wake re-created worker
    restarts its ids at 0, so the offset keeps its labels on the same
    continuous sequence as the shards that do have archives (raw labels
    would collide with the pre-hibernate numbering in the archive).
    """
    base = session.submit_era_base
    if not base:
        return
    for idx, fresh in payloads.items():
        archived = session.shard_payloads.get(idx) or {}
        frozen: list[dict] = []  # pre-wake entries (ids < base), kept verbatim
        current: dict[int, dict] = {}  # this era's entries by continuous id
        for e in archived.get("submissions", []):
            eid = int(e.get("submission") or 0)
            if eid < base:
                frozen.append(e)
            else:
                current[eid] = e
        for e in fresh.get("submissions", []):
            e = dict(e)
            eid = int(e.get("submission") or 0) + base
            e["submission"] = eid
            if eid < base:
                # Unreachable by construction (fresh local ids are
                # non-negative, so offset ids are always >= base): firing
                # means the continuous numbering broke somewhere —
                # surface it, don't hide it.
                LOGGER.warning(
                    "judge session %s shard %d: era union dropping fresh "
                    "submission %d (< era_base %d) — submission-id continuity broken",
                    session.session_id, idx, eid, base,
                )
                continue
            current[eid] = e
        merged_payload = dict(fresh)
        merged_payload["submissions"] = frozen + [current[k] for k in sorted(current)]
        payloads[idx] = merged_payload


async def _merged_submissions(store: JudgeSessionStore, session: JudgeSession) -> web.Response:
    """Collect every LIVE shard's /submissions, archive the raw records, and
    aggregate into one hidden-channel history — five numbers plus the
    K-stripped per-instance table (bounded fan-out).

    Failed shards contribute their last archived payload (entries judged
    before they died keep their records) and count fully toward ``failed``
    for entries they never judged; the aggregation learns per-shard judging-
    set sizes from every fetched payload. Only when EVERY shard is
    unavailable does the endpoint answer 502 — the transient-retry contract
    is preserved for the polling client.
    """
    results = await _call_shards(
        store, session, "GET", "/submissions",
        timeout=store.cfg.shard_call_timeout_seconds,
    )
    payloads: dict[int, dict[str, Any]] = {}
    for idx, (status, _headers, body) in results.items():
        if status != 200:
            # /submissions has no 4xx semantics: a non-200 live shard is
            # treated like a 5xx one and marked failed.
            _mark_shard_failed(store, session, idx, f"GET /submissions: HTTP {status}")
            continue
        try:
            payloads[idx] = json.loads(body.decode())
        except Exception:  # noqa: BLE001
            _mark_shard_failed(store, session, idx, "GET /submissions: malformed payload")
    if not payloads:
        return web.Response(
            status=502,
            body=b"502 Bad Gateway: every shard is unavailable (please try again)",
        )
    # Era union (hibernate wake): a wake re-created worker only knows
    # post-wake submissions under RESTARTED local ids; union its archived
    # pre-hibernate entries (continuous numbering) with the fresh ones
    # offset by submit_era_base, so the merged history never loses
    # pre-hibernate submissions and ids never collide. Shared with the
    # hibernate probe via _era_union_payloads (single caliber).
    _era_union_payloads(session, payloads)
    # Snapshot BEFORE archiving/aggregating: these payloads are the
    # failed-shard record source for any shard that dies later.
    for idx, payload in payloads.items():
        session.shard_payloads[idx] = payload
    _write_archive(store, session)
    # Preserve the final error records before reaping an execution boundary
    # that failed cleanup. Such a worker must never accept another submission.
    execution_failed = False
    for idx, payload in payloads.items():
        if payload.get("worker_error"):
            execution_failed = True
            _mark_shard_failed(store, session, idx,
                               "judge execution isolation failed: " + str(payload["worker_error"])[:1000])
    if execution_failed:
        _write_archive(store, session)
    # Delivered marker (hibernate): the latest submission's complete merged
    # result is being served to the client — the session becomes
    # hibernate-eligible once it stays quiet past the grace window.
    if _latest_submission_complete(session, payloads):
        session.delivered = True
    shard_payloads: list[dict[str, Any] | None] = []
    for shard in session.shards:
        if shard.index in payloads:
            shard_payloads.append(payloads[shard.index])
        elif shard.index in session.failed_shards:
            shard_payloads.append(session.shard_payloads.get(shard.index))
        else:
            shard_payloads.append(None)  # unreachable: a live non-200 shard was just marked failed
    if session.instance_set == "public":
        # Public channel: per-instance full detail (B/K stripped), the twin
        # of the hidden channel's five-numbers + per-instance (K-stripped)
        # form.
        return web.json_response(
            aggregate_public(
                shard_payloads,
                n_shards=session.n_shards,
                failed=session.failed_shards,
            )
        )
    return web.json_response(
        aggregate_submissions(
            shard_payloads,
            n_shards=session.n_shards,
            failed=session.failed_shards,
            size_cache=session.shard_sizes,
        )
    )


def _submissions_from_memory(store: JudgeSessionStore, session: JudgeSession) -> web.Response:
    """Serve the merged history from the session's archived payloads with no
    live shards (hibernated sessions). Read-only: no shard calls, no archive
    write (nothing new could have arrived while hibernated)."""
    if not session.shard_payloads:
        return web.json_response(
            {"submissions": [], "count": 0, "shards": session.n_shards, "status": "hibernated"}
        )
    shard_payloads: list[dict[str, Any] | None] = [
        session.shard_payloads.get(shard.index) for shard in session.shards
    ]
    if session.instance_set == "public":
        return web.json_response(
            aggregate_public(
                shard_payloads,
                n_shards=session.n_shards,
                failed=session.failed_shards,
            )
        )
    return web.json_response(
        aggregate_submissions(
            shard_payloads,
            n_shards=session.n_shards,
            failed=session.failed_shards,
            size_cache=session.shard_sizes,
        )
    )


async def _merged_health(store: JudgeSessionStore, session: JudgeSession) -> web.Response:
    # Snapshot the live set before the fan-out: "healthy" means every shard
    # that was live for THIS call answered 200 (a shard that went failed
    # mid-call counts against this answer, and is excluded from the next).
    live_snapshot = [s.index for s in session.shards if s.index not in session.failed_shards]
    results = await _call_shards(
        store, session, "GET", "/health",
        timeout=store.cfg.shard_call_timeout_seconds,
    )
    for idx, (status, _h, _b) in results.items():
        if status != 200:
            _mark_shard_failed(store, session, idx, f"GET /health: HTTP {status}")
    if (
        live_snapshot
        and len(results) == len(live_snapshot)
        and all(status == 200 for status, _h, _b in results.values())
    ):
        # Purely additive keys for the degraded-ready visibility contract.
        return web.json_response(
            {
                "status": "ok",
                "shards": session.n_shards,
                "failed_shards": len(session.failed_shards),
            }
        )
    return _json_error(502, "a shard's judge worker is unhealthy")


async def handle_session_relay(request: web.Request) -> web.StreamResponse:
    """Relay one HTTP request to the session's in-worker judge worker(s).

    ``GET /submissions`` NEVER relays straight through, not even for
    unsharded sessions: the worker answers raw per-instance records (anchors
    included), and the caller-facing surface is the aggregated history —
    five numbers plus the per-instance table with K stripped — only the
    aggregation path strips the anchors. ``POST /submit`` relays through
    unsharded and fans out sharded; ``GET /health`` merges sharded; any
    other path goes to shard 0 (forward-compatible).
    """
    from .sessions_base import _unknown_or_gone

    store: JudgeSessionStore = request.app["judge_sessions"]
    denied = _deny_wrong_owner(store, request.match_info["sid"], request)
    if denied is not None:
        # Wrong run-id: the uniform unknown-session 404 (before every other
        # branch, including the hibernated read path — a hibernated
        # session's archived history is the owning run's alone).
        return denied
    session = store.get(request.match_info["sid"])
    if session is None:
        return _unknown_or_gone(store, request.match_info["sid"])
    if session.status == "provisioning":
        # Async creation: transient by contract — the task-side retry
        # matchers key on the "please try again" substring and keep backing
        # off until the session flips to ready. This branch MUST sit before
        # the submission-cap block: a provisioning short-circuit never
        # counts (nothing can be accepted yet).
        return _json_error(503, PROVISIONING_MESSAGE, error_class="transient")
    if session.status == "hibernated":
        # Hibernation. This branch, like the provisioning one above, MUST
        # precede the cap block: a wake short-circuit never counts — the
        # submit is retried after ready and counted exactly once then.
        tail_h = request.match_info.get("tail", "").strip("/")
        if request.method == "POST" and tail_h == "submit":
            store._wake_session(session)
            return _json_error(503, PROVISIONING_MESSAGE, error_class="transient")
        if request.method == "GET" and tail_h == "submissions":
            # History is a read-only fact: serve from the archived payloads
            # without waking the group.
            return _submissions_from_memory(store, session)
        return _json_error(503, PROVISIONING_MESSAGE, error_class="transient")
    session.last_active = time.time()
    # Submission cap: keyed by SESSION, not source identity — clients may
    # share a NAT egress pool, so identity-keyed accounting silently merges
    # one run's submissions into another's. Per-session counting needs no
    # identity: each hidden session accepts at most `cap` submissions,
    # counted BEFORE forwarding ("counted at accept"); only the 404 and the
    # provisioning 503 above and the 429 below skip counting. The run-level
    # rule ("at most N across the run's declared session chain") is the
    # verifier's chain reconciliation against the same journal. PUBLIC
    # sessions skip the whole cap block — journaled as
    # ``submit_accept_public`` (history attribution, never cap-counted).
    is_submit = request.method == "POST" and request.match_info.get("tail", "").strip("/") == "submit"
    if is_submit and store._journal is not None:
        identity = request.get("identity") or request.remote or "-"
        if session.instance_set == "public":
            store.record_submission_accept_public(session.session_id, identity)
        else:
            if store.cfg.submission_cap.enabled:
                cap = store.cap_for(image_family(session.image))
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
    if is_submit:
        # Persist every ACCEPTED submission's body (the 429 above returns
        # earlier, so rejected bodies never land here; hidden and public
        # share one sequence per session). aiohttp caches request.read(), so
        # the downstream forward/fan-out re-read returns the same bytes —
        # the relay body is undisturbed.
        _persist_submission_body(store, session.session_id, await request.read())
        # A new submission means judging is in flight again: the delivered
        # marker (hibernate eligibility) resets until the complete merged
        # result for THIS submission is served.
        session.delivered = False
    tail = request.match_info.get("tail", "")
    # /submissions never relays straight through, not even unsharded (the
    # docstring above: only the aggregation path strips the anchors).
    if request.method == "GET" and tail.strip("/") == "submissions":
        return await _merged_submissions(store, session)
    if request.method == "POST" and tail == "submit":
        # All submits go through the fan-out path (1-shard included): the
        # submission-id era offset after a hibernate wake must be applied
        # in exactly one place, and the straight-through forward would
        # bypass it.
        return await _fanout_submit(store, session, request)
    if session.n_shards == 1:
        return await store._tunnels.forward(session.shards[0].app_name, request, check_token=False)
    if request.method == "GET" and tail == "health":
        return await _merged_health(store, session)
    return await store._tunnels.forward(session.shards[0].app_name, request, check_token=False)


def register_routes(app: web.Application) -> None:
    app.router.add_post("/v1/judge/sessions", handle_session_create)
    app.router.add_get("/v1/judge/sessions", handle_session_list)
    app.router.add_get("/v1/judge/sessions/{sid}", handle_session_status)
    # The archive route MUST precede the wildcard relay below: aiohttp
    # resolves resources in registration order, so a GET on
    # /v1/judge/sessions/{sid}/archive lands here instead of relaying
    # tail="archive" into the worker (non-GET methods still fall through
    # to the relay, like any other unknown tail).
    app.router.add_get("/v1/judge/sessions/{sid}/archive", handle_session_archive)
    # The payload endpoints likewise precede the wildcard relay — same
    # invariant as the archive route above.
    app.router.add_get("/v1/judge/sessions/{sid}/payload", handle_session_payload)
    app.router.add_get(
        "/v1/judge/sessions/{sid}/payload/submissions", handle_session_payload_submissions
    )
    app.router.add_get(
        "/v1/judge/sessions/{sid}/payload/submissions/{seq}", handle_session_payload_submission
    )
    app.router.add_delete("/v1/judge/sessions/{sid}", handle_session_delete)
    app.router.add_route("*", "/v1/judge/sessions/{sid}/{tail:.*}", handle_session_relay)
