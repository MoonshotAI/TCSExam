"""Service configuration (YAML) for the TCSExam judging backend.

The backend has exactly one shape: judge sessions (one throwaway worker per
shard, running the task's self-contained judge image, reached from the task
container through the reverse tunnel).

Layout: :class:`BaseServiceConfig` holds the bind/advertise addresses and the
shared-token auth pair; :class:`JudgeSessionsConfig` holds the session
machinery's knobs (including the sharding, fan-out, hibernation and payload
persistence thresholds); :class:`BackendConfig` holds the worker-creation
backend section (retry/concurrency gates and the global usage pre-check caps);
:class:`Config` ties them together and adds the platform-adapter selection
(``adapter``), the worker-group tagging prefix (``worker_group``), the state
directory, the verifier-only archive credential and the public-only worker
image allowlist (``public_image_map``).

Secrets come from the environment first (``TCSEXAM_TOKEN_ID`` /
``TCSEXAM_TOKEN_SECRET`` / ``TCSEXAM_ARCHIVE_TOKEN`` /
``TCSEXAM_WORKER_GROUP``), falling back to the YAML values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BaseServiceConfig:
    """The fields the service machinery reads from a service config."""

    host: str = "0.0.0.0"
    port: int = 8420
    advertise_host: str = "127.0.0.1"  # host part of URLs handed to clients
    public_base_url: str = ""  # e.g. https://backend.example.com (tunnel dial-in)
    token_id: str | None = None
    token_secret: str | None = None
    # Graceful token rotation: extra accepted (id, secret) pairs alongside the
    # primary pair. During a rotation window the old pair lives here while
    # clients migrate to the new primary — in-flight runs keep working, then
    # the old pair is dropped from this list.
    additional_tokens: list[tuple[str, str]] = field(default_factory=list)
    require_environment_credentials: bool = False
    # Caller-identity enforcement: "warn" (default; missing/malformed
    # X-TCSEXAM-Run-Id logs a throttled WARNING, responses unaffected),
    # "required" (reject 400), "off" (the header is not read at all).
    run_id_mode: str = "warn"
    # Display name surfaced as /v1/status service.name.
    service_name: str | None = "tcsexam-backend"

    @property
    def auth_enabled(self) -> bool:
        return bool(self.token_id or self.token_secret or self.additional_tokens)

    def validate_auth(self) -> None:
        """Reject incomplete credentials without including secret values in errors."""
        if type(self.require_environment_credentials) is not bool:
            raise ValueError("auth.require_environment_credentials must be a boolean")
        if self.require_environment_credentials:
            required = ("TCSEXAM_TOKEN_ID", "TCSEXAM_TOKEN_SECRET", "TCSEXAM_ARCHIVE_TOKEN")
            missing = [name for name in required if not os.environ.get(name, "").strip()]
            if missing:
                raise ValueError("Environment-only backend credentials are required: " + ", ".join(missing))
        primary = (self.token_id, self.token_secret)
        configured = any(value is not None for value in primary)
        if configured and not all(isinstance(value, str) and value.strip() for value in primary):
            raise ValueError("auth.token_id and auth.token_secret must both be non-empty strings")
        if not isinstance(self.additional_tokens, (list, tuple)):
            raise ValueError("auth.additional_tokens must be a list of credential pairs")
        for index, pair in enumerate(self.additional_tokens):
            if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                    or not all(isinstance(value, str) and value.strip() for value in pair)):
                raise ValueError(f"auth.additional_tokens[{index}] must contain two non-empty strings")
        if self.additional_tokens and not configured:
            raise ValueError("auth.additional_tokens requires a complete primary credential pair")

    def public_url(self) -> str:
        """Externally reachable base URL of this service (the in-worker agents
        dial ``<public_url>/v1/tunnel/{app}``)."""
        return self.public_base_url.rstrip("/") or f"http://{self.advertise_host}:{self.port}"


@dataclass
class JudgeSessionRoute:
    """One readiness/lifecycle-budget route: the first route whose
    ``image_contains`` is a substring of the requested judge image wins;
    unset fields fall back to the section default
    (``ready_timeout_seconds``) resp. the adapter's own creation budget
    (``create_ready_timeout_seconds``)."""

    image_contains: str
    ready_timeout_seconds: float | None = None
    create_ready_timeout_seconds: float | None = None
    # Lifecycle routing: slow families (e.g. proof/verification judges whose
    # single judging run takes 30min-2h) get a longer idle tolerance and a
    # longer absolute lifetime.
    idle_ttl_seconds: float | None = None  # idle-reap threshold for the family
    ttl_seconds: float | None = None  # default lifetime when the caller omits TTL


@dataclass
class SubmissionCapConfig:
    """Per-session submission cap.

    Counts ACCEPTED submissions (relay-level POST /submit only — shard fan-out
    is judging-internal parallelism and never a counting unit) PER JUDGING
    SESSION, since ``effective_at``. The accounting key is the session, not
    any client identity: judging clients may egress through a NAT-shared
    address pool, so identity-keyed accounting silently merges one run's
    submissions into another's. The run-level rule ("at most N across the
    run's declared session chain") is enforced by the verifier's chain
    reconciliation against the same journal. ``enabled: false`` still counts
    (reconciliation visibility) but never rejects. ``overrides`` is family
    (image_family-normalized) -> cap, family hit beats default.
    """

    enabled: bool = False  # opt-in per deployment
    default: int = 10
    effective_at: float = 0.0  # epoch seconds; 0 = service start time
    overrides: dict[str, int] = field(default_factory=dict)
    exempt_identities: list[str] = field(default_factory=list)
    # Hot-reload exemption file: one identity per line, '#' comments, re-read
    # on every cap check — a debug exemption lands without a service restart.
    # Missing or unreadable file = no file exemptions (never crashes a submit).
    exempt_identities_file: str = ""


@dataclass
class JudgeSessionsConfig:
    """Settings for the judge-session endpoints (``/v1/judge/sessions/*``):
    one throwaway worker per shard running the task's judge image (its judge
    worker on localhost), reached from the task container through the reverse
    tunnel.
    """

    max_sessions: int = 16  # global cap; create beyond it fails as transient
    # Creation profile: an OPAQUE string passed through to the platform
    # adapter as-is (its meaning is adapter-defined; the local test adapter
    # ignores it). Empty = the adapter's own default.
    profile: str = ""
    ttl_seconds: float = 21600.0  # default per-session TTL (platform safety net)
    max_ttl_seconds: float = 46800.0  # clamp for caller-requested ttl
    ready_timeout_seconds: float = 1800.0  # create + judge worker boot -> tunnel connect
    # Idle sessions are reaped after this. Must exceed the longest single
    # judge request (final evaluations run for hours — activity is stamped at
    # request ACCEPT time, not completion).
    idle_ttl_seconds: float = 14400.0
    reaper_interval_seconds: float = 60.0
    # Janitor margin: the total provisioning deadline = create budget +
    # ready_timeout + this value. Tunable downward for tests.
    provision_janitor_margin_seconds: float = 600.0
    spec: dict[str, int] = field(
        default_factory=lambda: {
            "cpu_count": 4,
            "memory_mb": 8192,
            "storage_mb": 20480,
        }
    )
    # In-worker working directory for the uploaded agent bundle. Must match
    # the adapter's work_dir: stop_app's agent.log tail recovery reads
    # <work_dir>/agent.log on teardown.
    work_dir: str = "/tcsexam-backend"
    # The judge worker started inside the worker (an EMPTY command starts
    # nothing: the agent only relays to an already-running server) and the
    # port it listens on.
    command: str = "python3 /judge/judge_worker.py"
    judge_port: int = 8082
    health_path: str = "/health"
    # Label carried by the agent's READY frame (informational; service logs).
    ready_label: str = "tcsexam-judge"
    # Upstream read timeout for the in-worker relay (long evaluations are
    # legitimate).
    read_timeout_seconds: float = 7200.0
    # Gate the auth-exempt /apps/<app> twin of each session tunnel with a
    # random token nobody receives. This backend registers no /apps/* proxy
    # (every relay path sits behind the service auth middleware), so there is
    # nothing for the gate to protect; keep it off.
    gate_session_tokens: bool = False
    # Deduplicate concurrent creations of the same logical session
    # (singleflight): matching caller identity and effective creation
    # parameters share an in-flight worker. Sharing REQUIRES the explicit
    # X-TCSEXAM-Client-Id header; without it every create gets its own session.
    singleflight: bool = True
    # Per-image-family readiness/lifecycle budgets (GB-scale judge images
    # cold-boot far past the generic defaults). First matching route wins.
    routes: list[JudgeSessionRoute] = field(default_factory=list)
    # Failed-session retention: failed sessions are kept for outcome polling,
    # then destroyed (their records stop counting as live). A broken image
    # hammered by retries would otherwise accumulate corpses.
    failed_retention_seconds: float = 3600.0
    # Tunnel reconnect grace: a ready session whose tunnel dropped is kept
    # (worker and all) for this long so the in-worker agent can redial and
    # resume; only a drop outlasting the window reaps the session.
    tunnel_reconnect_grace_seconds: float = 180.0
    # Upper bound on n_shards per session (a sharded session boots one worker
    # per shard; see sessions.py for the sharding contract).
    max_shards: int = 512
    # Session-level resource quotas (checked synchronously at create accept
    # time, n_shards x per-worker spec). 0 = DISABLED (the default): the
    # dual-dimension GLOBAL usage pre-check (instances + memory) subsumes
    # these static per-session caps; set a positive value to re-enable.
    max_session_cpu_count: int = 0  # cores; 0 = no per-session cpu cap
    max_session_memory_mb: int = 0  # MB; 0 = no per-session memory cap
    # Degraded-ready floor: a session goes ready once every shard's boot has
    # settled AND the live count is >= ceil(min_ready_ratio x n_shards);
    # below the floor the whole session goes failed. Pinned at 1.0 by
    # default: partial provisioning must NEVER produce a score — an
    # incomplete shard set returns failed, not partial credit. A retried
    # judging is a NEW session, not a new submission — the submission cap
    # counts accepted submissions only, and a failed provisioning never
    # accepted one, so the caller's submission budget is untouched.
    min_ready_ratio: float = 1.0
    # Per-shard boot retries (shard_boot_retries extra attempts after the
    # first failure, transient errors only) with exponential backoff
    # (delay x 2^n capped at 60s). The worker create itself is already
    # covered by the adapter's own retry loop; these retries exist for
    # one-shot flaps in the agent upload / tunnel-connect stages.
    shard_boot_retries: int = 2
    shard_boot_retry_delay_seconds: float = 15.0
    # Fan-out bound: at most this many concurrent tunnel calls per relay
    # fan-out (hundreds of shards x a multi-MB submit body would otherwise
    # spike egress and memory). Store-wide semaphore.
    fanout_concurrency: int = 64
    # Per-call timeout for the /submissions and /health fan-out legs.
    shard_call_timeout_seconds: float = 30.0
    # Per-call timeout for the /submit fan-out leg (bigger: submit bodies
    # are MB-sized).
    submit_fanout_timeout_seconds: float = 120.0
    # Session teardown concurrency (store-wide): stop_app per shard in
    # parallel instead of one-by-one.
    destroy_concurrency: int = 32
    # Tunnel-drop grace in REAPER TICKS: a shard whose tunnel is down is
    # marked failed only after this many consecutive reap ticks (4 ticks x
    # the 60s default reaper interval ~= 240s, strictly above the 180s
    # reconnect grace). A dropped shard no longer kills the whole session.
    shard_down_grace_ticks: int = 4
    # Creation-payload persistence cap: a judge_payload larger than this is
    # NOT persisted (skip + WARN — the persistence layer is best-effort like
    # the archive, it never fails session creation). The cap only guards
    # anomalies. Submission bodies are bounded by the server's global 1 GiB
    # body limit instead.
    payload_persist_max_bytes: int = 67108864  # 64 MiB
    # Session hibernation: once a session's latest submission is delivered
    # AND it stays quiet for hibernate_grace_seconds, the reaper recycles the
    # whole worker group and keeps only metadata/archive; the next submit
    # re-provisions. The idle_ttl path also becomes hibernate instead of
    # destroy while enabled. Disable to fall back to the destroy-based idle
    # reaper.
    hibernate_enabled: bool = True
    hibernate_grace_seconds: float = 1800.0
    # Cold-worker boot grace: within this window after a session's
    # ready-flip, shard transport failures (timeout / unreachable) in the
    # fan-out are treated as cold-worker boot stragglers, never as permanent
    # shard failure. Heavy judge workers can take minutes to serve after the
    # tunnel's READY.
    shard_boot_call_grace_seconds: float = 300.0
    # Per-session submission cap: see SubmissionCapConfig.
    submission_cap: SubmissionCapConfig = field(default_factory=SubmissionCapConfig)

    def resolve_readiness(self, image: str) -> tuple[float, float | None]:
        """Route a judge image to (ready_timeout, create_ready_timeout).

        ``ready_timeout`` covers the store's tunnel-wait budget and the
        in-worker agent's boot timeout; ``create_ready_timeout`` is handed
        to the adapter's worker creation (None = the adapter's own
        default). First route whose ``image_contains`` is a substring of
        ``image`` wins; no route hits -> (section default, None).
        """
        for route in self.routes:
            if route.image_contains in image:
                ready = route.ready_timeout_seconds
                return (
                    self.ready_timeout_seconds if ready is None else ready,
                    route.create_ready_timeout_seconds,
                )
        return (self.ready_timeout_seconds, None)

    def resolve_lifecycle(self, image: str) -> tuple[float, float]:
        """Route a judge image to ``(idle_ttl_seconds, ttl_seconds)`` — the
        idle-reap threshold and the absolute lifetime cap. First route whose
        ``image_contains`` is a substring of ``image`` wins; unset fields
        fall back to the section defaults.
        """
        for route in self.routes:
            if route.image_contains in image:
                idle = route.idle_ttl_seconds
                ttl = route.ttl_seconds
                return (
                    self.idle_ttl_seconds if idle is None else idle,
                    self.ttl_seconds if ttl is None else ttl,
                )
        return (self.idle_ttl_seconds, self.ttl_seconds)

    def agent_timeouts(self, ready_timeout: float) -> dict[str, float]:
        """Identical worker-agent limits for single and multiple workers."""
        return {"boot_timeout_seconds": min(ready_timeout, 7200.0),
                "read_timeout_seconds": self.read_timeout_seconds}


@dataclass
class BackendConfig:
    """Worker-creation backend settings (the platform adapter's budget and
    the store's creation gates)."""

    create_retries: int = 20  # extra creation attempts after the first failure
    # Base delay between creation retries; attempt N waits base * 2^(N-1),
    # capped at 10 min. A "pool temporarily full" style failure fails fast
    # platform-side, so retries must WAIT, not spin.
    create_retry_delay_seconds: float = 60.0
    # Upper bound on concurrent worker creations (a sharded session fires one
    # creation per shard at once).
    create_concurrency: int = 64
    # Per-session creation concurrency (the store takes this semaphore before
    # the adapter's global gate — session gate first, always, so the two
    # never cross-hold). Same default as the global gate: a lone session
    # loses no speed; smaller values keep one large session from starving
    # others on the global gate.
    session_create_concurrency: int = 64
    # Global worker-usage cap: create accept time estimates usage = live +
    # in-flight + requested on BOTH dimensions and rejects over either with a
    # readable 503 transient instead of queueing inside the creation gate.
    max_sandboxes_global: int = 4096
    # Memory dimension of the same pre-check, in MiB. Judging defaults to
    # 8 GiB/worker, so memory — not instances — is the dimension that binds
    # first.
    max_sandbox_memory_mb: int = 32768000
    ready_timeout_seconds: float = 2400.0  # creation/readiness budget (cold image pulls)
    judge_sessions: JudgeSessionsConfig = field(default_factory=JudgeSessionsConfig)


@dataclass
class Config(BaseServiceConfig):
    """Top-level service configuration."""

    state_dir: Path = Path("/tmp/tcsexam-backend-state")
    # Platform adapter loading spec: "" = not configured (the service refuses
    # to create judge sessions with a clear error), "docker" = the bundled
    # Docker Engine adapter, "local-test" = the local-process test adapter,
    # otherwise "module:factory" (see adapter.load_adapter).
    adapter: str = ""
    # Worker-group tagging prefix: with a run-id present, creations carry
    # ``group_name = "<worker_group>--<run-id slug>"`` so the platform can
    # reap exactly one run's workers. Overridable via TCSEXAM_WORKER_GROUP;
    # empty = no group tagging.
    worker_group: str = "tcsexam"
    # Verifier-only credential for archive/payload downloads, hidden-session
    # creation, and every session list/reconciliation query. The verifier
    # presents it as ``X-TCSEXAM-Archive-Token``; inject it via the
    # TCSEXAM_ARCHIVE_TOKEN env var (never as YAML plaintext in git). Empty
    # disables those operations; archive/payload retain their uniform-404
    # contract, while the create and list gates answer 403.
    archive_token: str = ""
    # Exact allowlist for public sessions: client-requested original judge
    # image -> public-only worker image. Empty rejects every public create.
    public_image_map: dict[str, str] = field(default_factory=dict)
    # Docker adapter settings. Only a local Unix socket is supported; an
    # unauthenticated remote Docker API would expose host-level control.
    docker_socket: str = "/var/run/docker.sock"
    docker_network: str = "bridge"
    docker_pull_missing_images: bool = True
    docker_host_gateway: bool = True
    docker_api_timeout_seconds: float = 60.0
    backend: BackendConfig = field(default_factory=BackendConfig)

    def validate_docker(self) -> None:
        if (
            not isinstance(self.docker_socket, str)
            or not Path(self.docker_socket).is_absolute()
            or "\x00" in self.docker_socket
        ):
            raise ValueError("docker_socket must be an absolute Unix socket path; remote TCP is not supported")
        if not isinstance(self.docker_network, str) or not self.docker_network.strip():
            raise ValueError("docker_network must be a nonempty Docker network name")
        if not isinstance(self.docker_pull_missing_images, bool) or not isinstance(self.docker_host_gateway, bool):
            raise ValueError("docker_pull_missing_images and docker_host_gateway must be booleans")
        import math

        if not math.isfinite(float(self.docker_api_timeout_seconds)) or self.docker_api_timeout_seconds <= 0:
            raise ValueError("docker_api_timeout_seconds must be a positive finite number")

    def validate_public_image_map(self) -> None:
        """Validate the public image allowlist without echoing its values."""
        if not isinstance(self.public_image_map, dict):
            raise ValueError("public_image_map must be a mapping of image names")
        if any(
            not isinstance(image, str) or not image.strip()
            or not isinstance(public_image, str) or not public_image.strip()
            for image, public_image in self.public_image_map.items()
        ):
            raise ValueError("public_image_map keys and values must be non-empty strings")


def _positive_timeout(value: Any, label: str) -> float | None:
    """Optional route timeout: None when unset, else a strictly positive float."""
    if value is None:
        return None
    result = float(value)
    if result <= 0:
        raise ValueError(f"{label} must be a positive number of seconds, got {value!r}")
    return result


def _route_from_dict(index: int, raw: Any) -> JudgeSessionRoute:
    """Parse one readiness route; invalid entries fail at startup (config load)."""
    if not isinstance(raw, dict):
        raise ValueError(f"judge_sessions.routes[{index}] must be a mapping, got {raw!r}")
    match = raw.get("match") or {}
    if not isinstance(match, dict):
        raise ValueError(f"judge_sessions.routes[{index}].match must be a mapping")
    image_contains = str(match.get("image_contains") or "")
    if not image_contains:
        raise ValueError(f"judge_sessions.routes[{index}].match.image_contains is required")
    return JudgeSessionRoute(
        image_contains=image_contains,
        ready_timeout_seconds=_positive_timeout(
            raw.get("ready_timeout_seconds"), f"judge_sessions.routes[{index}].ready_timeout_seconds"
        ),
        create_ready_timeout_seconds=_positive_timeout(
            raw.get("create_ready_timeout_seconds"),
            f"judge_sessions.routes[{index}].create_ready_timeout_seconds",
        ),
        idle_ttl_seconds=_positive_timeout(
            raw.get("idle_ttl_seconds"), f"judge_sessions.routes[{index}].idle_ttl_seconds"
        ),
        ttl_seconds=_positive_timeout(
            raw.get("ttl_seconds"), f"judge_sessions.routes[{index}].ttl_seconds"
        ),
    )


def _submission_cap_from_dict(raw: dict[str, Any]) -> SubmissionCapConfig:
    """Parse the ``judge_sessions.submission_cap`` section."""
    default = SubmissionCapConfig()
    return SubmissionCapConfig(
        enabled=bool(raw.get("enabled", default.enabled)),
        default=int(raw.get("default", default.default)),
        effective_at=float(raw.get("effective_at", default.effective_at)),
        overrides={str(k): int(v) for k, v in (raw.get("overrides") or {}).items()},
        exempt_identities=[str(x) for x in (raw.get("exempt_identities") or [])],
        exempt_identities_file=str(
            raw.get("exempt_identities_file", default.exempt_identities_file)
        ),
    )


def read_exempt_identities_file(path: str) -> list[str]:
    """Parse the hot-reload exemption file: one identity per line, '#'
    comments and blanks ignored. Shared by the cap check and /v1/status; an
    unreadable file yields no exemptions (never crashes a submit)."""
    import logging as _logging

    try:
        with open(path) as fh:
            return [x for x in (line.split("#", 1)[0].strip() for line in fh) if x]
    except OSError:
        _logging.getLogger(__name__).warning("exempt identities file unreadable: %s", path)
        return []


def judge_sessions_from_dict(raw: dict[str, Any]) -> JudgeSessionsConfig:
    """Parse the ``judge_sessions`` config section (YAML) over the defaults."""
    default = JudgeSessionsConfig()
    return JudgeSessionsConfig(
        max_sessions=int(raw.get("max_sessions", default.max_sessions)),
        profile=str(raw.get("profile", default.profile)),
        ttl_seconds=float(raw.get("ttl_seconds", default.ttl_seconds)),
        max_ttl_seconds=float(raw.get("max_ttl_seconds", default.max_ttl_seconds)),
        ready_timeout_seconds=float(
            raw.get("ready_timeout_seconds", default.ready_timeout_seconds)
        ),
        idle_ttl_seconds=float(raw.get("idle_ttl_seconds", default.idle_ttl_seconds)),
        reaper_interval_seconds=float(
            raw.get("reaper_interval_seconds", default.reaper_interval_seconds)
        ),
        provision_janitor_margin_seconds=float(
            raw.get(
                "provision_janitor_margin_seconds",
                default.provision_janitor_margin_seconds,
            )
        ),
        spec={
            **default.spec,
            **{
                str(k): None if k == "storage_mb" and v is None else int(v)
                for k, v in (raw.get("spec") or {}).items()
            },
        },
        work_dir=str(raw.get("work_dir", default.work_dir)),
        command=str(raw.get("command", default.command)),
        judge_port=int(raw.get("judge_port", default.judge_port)),
        health_path=str(raw.get("health_path", default.health_path)),
        ready_label=str(raw.get("ready_label", default.ready_label)),
        read_timeout_seconds=float(
            raw.get("read_timeout_seconds", default.read_timeout_seconds)
        ),
        gate_session_tokens=bool(raw.get("gate_session_tokens", default.gate_session_tokens)),
        singleflight=bool(raw.get("singleflight", default.singleflight)),
        routes=[_route_from_dict(i, r) for i, r in enumerate(raw.get("routes") or [])],
        failed_retention_seconds=float(
            raw.get("failed_retention_seconds", default.failed_retention_seconds)
        ),
        tunnel_reconnect_grace_seconds=float(
            raw.get("tunnel_reconnect_grace_seconds", default.tunnel_reconnect_grace_seconds)
        ),
        max_shards=int(raw.get("max_shards", default.max_shards)),
        max_session_cpu_count=int(raw.get("max_session_cpu_count", default.max_session_cpu_count)),
        max_session_memory_mb=int(raw.get("max_session_memory_mb", default.max_session_memory_mb)),
        min_ready_ratio=float(raw.get("min_ready_ratio", default.min_ready_ratio)),
        shard_boot_retries=int(raw.get("shard_boot_retries", default.shard_boot_retries)),
        shard_boot_retry_delay_seconds=float(
            raw.get("shard_boot_retry_delay_seconds", default.shard_boot_retry_delay_seconds)
        ),
        fanout_concurrency=int(raw.get("fanout_concurrency", default.fanout_concurrency)),
        shard_call_timeout_seconds=float(
            raw.get("shard_call_timeout_seconds", default.shard_call_timeout_seconds)
        ),
        submit_fanout_timeout_seconds=float(
            raw.get("submit_fanout_timeout_seconds", default.submit_fanout_timeout_seconds)
        ),
        destroy_concurrency=int(raw.get("destroy_concurrency", default.destroy_concurrency)),
        shard_down_grace_ticks=int(raw.get("shard_down_grace_ticks", default.shard_down_grace_ticks)),
        payload_persist_max_bytes=int(
            raw.get("payload_persist_max_bytes", default.payload_persist_max_bytes)
        ),
        hibernate_enabled=bool(raw.get("hibernate_enabled", default.hibernate_enabled)),
        hibernate_grace_seconds=float(
            raw.get("hibernate_grace_seconds", default.hibernate_grace_seconds)
        ),
        shard_boot_call_grace_seconds=float(
            raw.get("shard_boot_call_grace_seconds", default.shard_boot_call_grace_seconds)
        ),
        submission_cap=_submission_cap_from_dict(raw.get("submission_cap") or {}),
    )


def load_config(path: str | Path) -> Config:
    """Load the YAML config file into a :class:`Config`."""
    raw = yaml.safe_load(Path(path).read_text()) or {}
    auth = raw.get("auth")
    auth = {} if auth is None else auth
    if not isinstance(auth, dict):
        raise ValueError("auth must be a mapping of credential settings")
    backend_raw = raw.get("backend") or {}
    backend_default = BackendConfig()
    config = Config(
        host=str(raw.get("host", "0.0.0.0")),
        port=int(raw.get("port", 8420)),
        public_base_url=str(raw.get("public_base_url", "")),
        token_id=auth.get("token_id"),
        token_secret=auth.get("token_secret"),
        additional_tokens=auth.get("additional_tokens", []),
        require_environment_credentials=auth.get("require_environment_credentials", False),
        run_id_mode=str(auth.get("run_id_mode", "warn")),
        state_dir=Path(raw.get("state_dir", "/tmp/tcsexam-backend-state")),
        adapter=str(raw.get("adapter", "")),
        worker_group=str(raw.get("worker_group", "tcsexam")),
        archive_token=str(raw.get("archive_token", "")),
        public_image_map=raw.get("public_image_map", {}),
        docker_socket=raw.get("docker_socket", "/var/run/docker.sock"),
        docker_network=raw.get("docker_network", "bridge"),
        docker_pull_missing_images=raw.get("docker_pull_missing_images", True),
        docker_host_gateway=raw.get("docker_host_gateway", True),
        docker_api_timeout_seconds=float(raw.get("docker_api_timeout_seconds", 60.0)),
        backend=BackendConfig(
            create_retries=int(backend_raw.get("create_retries", backend_default.create_retries)),
            create_retry_delay_seconds=float(
                backend_raw.get("create_retry_delay_seconds", backend_default.create_retry_delay_seconds)
            ),
            create_concurrency=int(
                backend_raw.get("create_concurrency", backend_default.create_concurrency)
            ),
            session_create_concurrency=int(
                backend_raw.get("session_create_concurrency", backend_default.session_create_concurrency)
            ),
            max_sandboxes_global=int(
                backend_raw.get("max_sandboxes_global", backend_default.max_sandboxes_global)
            ),
            max_sandbox_memory_mb=int(
                backend_raw.get("max_sandbox_memory_mb", backend_default.max_sandbox_memory_mb)
            ),
            ready_timeout_seconds=float(
                backend_raw.get("ready_timeout_seconds", backend_default.ready_timeout_seconds)
            ),
            judge_sessions=judge_sessions_from_dict(backend_raw.get("judge_sessions") or {}),
        ),
    )
    # Env overrides (the deployment keeps secrets out of the YAML).
    if os.environ.get("TCSEXAM_TOKEN_ID"):
        config.token_id = os.environ["TCSEXAM_TOKEN_ID"]
    if os.environ.get("TCSEXAM_TOKEN_SECRET"):
        config.token_secret = os.environ["TCSEXAM_TOKEN_SECRET"]
    if os.environ.get("TCSEXAM_ARCHIVE_TOKEN"):
        config.archive_token = os.environ["TCSEXAM_ARCHIVE_TOKEN"]
    if os.environ.get("TCSEXAM_WORKER_GROUP"):
        config.worker_group = os.environ["TCSEXAM_WORKER_GROUP"]
    if os.environ.get("TCSEXAM_DOCKER_SOCKET"):
        config.docker_socket = os.environ["TCSEXAM_DOCKER_SOCKET"]
    config.validate_auth()
    config.validate_public_image_map()
    config.validate_docker()
    return config
