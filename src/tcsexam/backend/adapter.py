"""The platform-adapter interface: how the backend creates and destroys
judge workers.

The session stores (:mod:`tcsexam.backend.sessions_base` and
:mod:`tcsexam.backend.sessions`) never talk to a worker platform directly;
they drive an adapter through the small protocol defined here. An adapter
implements "create an isolated worker from this judge image with these
resources, let me upload files and run commands in it, and destroy it on
request" — a cloud sandbox service, a container runtime, a VM fleet, or the
bundled local-process test double.

Terminology: the historical method names say ``sandbox`` (e.g.
``create_sandbox``); read "sandbox" as "worker" throughout. The names are
kept so the session stores' call surface stays stable.

The store-facing call surface (do not change without updating the stores):

* ``create_sandbox(profile, image_url, *, ttl_seconds, spec,
  ready_timeout_seconds=None, group_name=None, labels=None) -> Worker``
* ``register_long_lived(app_name, worker)`` — put a worker on the long-lived
  table (the tunnel-close reaper and ``stop_app`` work through it)
* ``sandbox_for_app(app_name) -> Worker | None``
* ``long_lived_count() -> int`` / ``long_lived_memory_mb() -> int``
* ``stop_app(app_name)`` — destroy a long-lived worker (idempotent)
* attribute ``ready_timeout_seconds: float`` — the adapter's own creation
  budget (read by the store's provisioning-deadline math)

The worker-facing surface the stores use:

* ``worker.ctrl.write_bytes(path, data: bytes, parents=True)``
* ``worker.ctrl.run(cmd, shell=True, text=True, timeout=30)`` — returns an
  object with a ``stdout`` attribute
* ``worker.ctrl.read_text(path) -> str``
* ``await worker.delete()``
* optional attribute ``worker.judge_port: int`` — per-worker judge port
  override (used by the local test adapter, whose workers share one
  localhost; real isolated workers each have their own localhost and use
  the configured port)
* optional attribute ``worker.resources: WorkerResources`` — the
  creation-time resources. Not required: :class:`BasePlatformAdapter`
  prefers it for the ``long_lived_memory_mb`` accounting when present and
  otherwise falls back to the resources its own create_sandbox recorded.
  Adapters that do NOT subclass the base must keep their own creation
  records for the accounting — a ``long_lived_memory_mb`` that always
  returns 0 under-reports the global memory usage check.

Adapter contract (all implementations):

* Creation must honor the requested image and resources AS GIVEN. If the
  platform cannot provide them (e.g. cannot allocate the requested memory),
  the adapter must raise a clear error — silently booting a smaller worker
  is a contract violation: judging runs assume the declared resources.
* Errors: raise exceptions whose class name is in
  ``errors.NON_TRANSIENT_ERROR_NAMES`` (``AuthenticationError``,
  ``PermissionDeniedError``, ``InvalidArgumentError``,
  ``InsufficientCreditsError``) for failures a retry cannot fix; every
  other exception class is treated as TRANSIENT and retried with backoff
  (a wasted retry beats an aborted evaluation). ``ValueError`` is always
  treated as non-transient (a caller bug).
* ``stop_app`` and ``worker.delete()`` must be idempotent: unknown or
  already-destroyed workers are a silent no-op.
* Cleanup is scoped: an adapter only ever destroys resources IT created —
  never account/platform-wide purges.
* Cancellation: a cancelled creation must not leak a half-created worker;
  the adapter (or the store's ``asyncio.shield``-ed delete path) destroys
  it before the cancellation propagates.
* Credentials: platform credentials live in the adapter's own configuration
  and must never be written to logs, worker environment variables, or
  exception messages (exception text propagates to task clients).
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .errors import (
    NON_TRANSIENT_ERROR_NAMES,
    TRANSIENT_HINT,
    is_transient_platform_error,
)

__all__ = [
    "WorkerResources",
    "WorkerControl",
    "Worker",
    "PlatformAdapter",
    "BasePlatformAdapter",
    "ConfigurationError",
    "load_adapter",
    "NON_TRANSIENT_ERROR_NAMES",
    "TRANSIENT_HINT",
    "is_transient_platform_error",
]

LOGGER = logging.getLogger("tcsexam.backend.adapter")

#: The members load_adapter verifies on a freshly loaded adapter instance.
_REQUIRED_MEMBERS = (
    "create_sandbox",
    "register_long_lived",
    "sandbox_for_app",
    "long_lived_count",
    "long_lived_memory_mb",
    "stop_app",
    "ready_timeout_seconds",
)


class ConfigurationError(ValueError):
    """The service configuration is incomplete or invalid (raised before any
    worker is created; never classified as transient)."""


@dataclass
class WorkerResources:
    """Per-worker resource request (the creation-time parameter check set).

    Adapters must provide exactly these amounts or raise; see the module
    docstring ("no silent downgrade").
    """

    cpu_count: int = 0
    memory_mb: int = 0
    storage_mb: int | None = None

    @classmethod
    def from_spec(cls, spec: dict[str, int] | None) -> "WorkerResources":
        """Build from the store's spec dict; unknown keys are ignored
        (forward-compatible: newer resource knobs degrade silently)."""
        values = spec or {}
        return cls(
            cpu_count=int(values.get("cpu_count") or 0),
            memory_mb=int(values.get("memory_mb") or 0),
            storage_mb=(
                None if values.get("storage_mb") is None else int(values["storage_mb"])
            ),
        )


class WorkerControl(Protocol):
    """File/command channel into a live worker (the store uploads the agent
    bundle and launches it through this)."""

    async def write_bytes(self, path: str, data: bytes, parents: bool = False) -> None:
        """Write ``data`` to ``path`` inside the worker; ``parents=True``
        creates missing parent directories."""
        ...

    async def run(
        self,
        cmd: str,
        shell: bool = False,
        text: bool = False,
        timeout: float = 30,
    ) -> Any:
        """Run ``cmd`` inside the worker; returns an object with (at least)
        a ``stdout`` attribute. Raises on transport failure; a non-zero exit
        code is reported, not raised."""
        ...

    async def read_text(self, path: str) -> str:
        """Read a text file from the worker (raises when missing/unreadable)."""
        ...


class Worker(Protocol):
    """One isolated judge worker created from a judge image."""

    #: The control channel (see WorkerControl).
    @property
    def ctrl(self) -> WorkerControl: ...

    #: A platform-side identifier (logs only).
    @property
    def name(self) -> str: ...

    async def delete(self) -> None:
        """Destroy the worker. Idempotent; best-effort (the caller treats a
        raised error as "teardown failed", logs it, and moves on — the
        worker's own TTL is the final safety net)."""
        ...


class _WorkerOptionalResources(Protocol):
    """OPTIONAL worker metadata member: ``resources: WorkerResources``.

    Not part of the required Worker protocol — the stores never read it.
    An adapter that exposes the creation-time resources on the worker makes
    them authoritative for :class:`BasePlatformAdapter`'s memory accounting
    (``long_lived_memory_mb``); without it the base falls back to the
    resources recorded by its own create_sandbox.
    """

    @property
    def resources(self) -> WorkerResources: ...


@runtime_checkable
class PlatformAdapter(Protocol):
    """What the session stores need from a worker platform."""

    @property
    def ready_timeout_seconds(self) -> float:
        """The adapter's own creation/readiness budget."""
        ...

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
    ) -> Worker:
        """Create one worker from ``image_url`` with the given resources.

        ``profile`` is an opaque, adapter-defined scheduling hint (the
        config's ``judge_sessions.profile``, passed through untouched; ""
        means the adapter's default). ``ttl_seconds`` is the platform-side
        safety-net lifetime. ``spec`` carries cpu_count/memory_mb/
        storage_mb. ``ready_timeout_seconds`` overrides the adapter's
        creation budget for this one call. ``group_name``/``labels`` are
        attribution tags (the platform may use them for scoped cleanup and
        lookup); an adapter without a tagging concept may ignore them.
        """
        ...

    def register_long_lived(self, app_name: str, worker: Worker) -> None:
        """Put a worker on the long-lived table."""
        ...

    def sandbox_for_app(self, app_name: str) -> Worker | None:
        """The live long-lived worker for an app, if any (no state change)."""
        ...

    def long_lived_count(self) -> int:
        """Number of workers on the long-lived table (usage accounting)."""
        ...

    def long_lived_memory_mb(self) -> int:
        """Total memory (MiB) of the long-lived table (usage accounting;
        workers whose creation-time resources are unknown count as 0 rather
        than breaking the sum — but an implementation must keep enough
        metadata that a worker it created itself is NEVER unknown: a
        fixed-zero answer silently disables the global memory check)."""
        ...

    async def stop_app(self, app_name: str) -> None:
        """Destroy a long-lived worker (idempotent; unknown app = no-op)."""
        ...


class BasePlatformAdapter:
    """Shared adapter machinery: creation retry-with-backoff under a
    concurrency gate, the long-lived worker table, and stop_app with the
    agent.log tail recovery.

    Concrete adapters subclass this and implement :meth:`_create_worker`
    (one creation attempt against their platform). The retry loop classifies
    errors with :func:`errors.is_transient_platform_error` — transient
    failures wait base*2^(n-1) (capped at 10 min) between attempts: a busy
    pool must become a WAIT, not an evaluation failure.
    """

    #: Logger used for lifecycle messages; subclasses keep their own name.
    logger_name = "tcsexam.backend.adapter"

    def __init__(
        self,
        *,
        create_retries: int = 1,
        create_retry_delay_seconds: float = 30.0,
        ready_timeout_seconds: float = 2400.0,
        default_ttl_seconds: float = 7200.0,
        default_spec: dict[str, int] | None = None,
        work_dir: str = "/tcsexam-backend",
        create_concurrency: int = 64,
    ) -> None:
        self.LOGGER = logging.getLogger(self.logger_name)
        self.create_retries = create_retries
        self.create_retry_delay_seconds = create_retry_delay_seconds
        self.ready_timeout_seconds = ready_timeout_seconds
        self.default_ttl_seconds = default_ttl_seconds
        self.default_spec = default_spec or {}
        # In-worker directory the agent bundles are uploaded to; the
        # agent.log tail recovery reads <work_dir>/agent.log on teardown.
        self._work_dir = work_dir
        # Concurrency gate on worker creation: a sharded session fires N
        # creations at once; the gate keeps platform pressure bounded (held
        # for the whole retry loop, so at most ``create_concurrency``
        # creations are ever in flight).
        self._create_sem = asyncio.Semaphore(create_concurrency)
        # Long-lived workers (app name -> worker): a session holds its
        # resources for hours by design.
        self._long_lived: dict[str, Worker] = {}
        # Creation-time resources of workers created through THIS base,
        # keyed by id(worker) — the bridge between create_sandbox (which
        # knows the resources) and register_long_lived (which does the
        # accounting). Entries are popped at register time; the table is
        # bounded (workers that never register would otherwise leak).
        self._created_resources: dict[int, WorkerResources] = {}
        # The accounting table behind long_lived_memory_mb: app name ->
        # the worker's resolved creation resources (see
        # _resolve_worker_resources). Populated by register_long_lived,
        # dropped by stop_app.
        self._long_lived_resources: dict[str, WorkerResources] = {}

    # ------------------------------------------------------------------ #
    # Worker lifecycle
    # ------------------------------------------------------------------ #
    async def _create_worker(
        self,
        profile: str,
        image_url: str,
        *,
        ttl_seconds: float,
        resources: WorkerResources,
        ready_timeout_seconds: float,
        group_name: str | None,
        labels: dict[str, str] | None,
    ) -> Worker:
        """ONE creation attempt against the concrete platform (no retry, no
        gate — the base class wraps both around this). Implementations must
        honor the requested image/resources exactly or raise (see the module
        docstring)."""
        raise NotImplementedError

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
    ) -> Worker:
        """Create a worker, retrying transient creation failures with backoff
        under the creation concurrency gate.

        ``ready_timeout_seconds`` overrides ``self.ready_timeout_seconds``
        for this one creation (per-image-family readiness budgets); None
        keeps the configured value.
        """
        resources = WorkerResources.from_spec(
            spec if spec is not None else self.default_spec
        )
        ready_timeout = (
            self.ready_timeout_seconds if ready_timeout_seconds is None else ready_timeout_seconds
        )
        ttl = ttl_seconds or self.default_ttl_seconds
        async with self._create_sem:
            last: BaseException | None = None
            for attempt in range(1 + self.create_retries):
                try:
                    worker = await self._create_worker(
                        profile,
                        image_url,
                        ttl_seconds=ttl,
                        resources=resources,
                        ready_timeout_seconds=ready_timeout,
                        group_name=group_name,
                        labels=labels,
                    )
                    # Remember the creation-time resources so
                    # register_long_lived can account them even when the
                    # worker object exposes no resources metadata of its
                    # own. Bounded: entries are popped at register time, and
                    # the oldest is evicted past the cap (a worker that is
                    # never registered would otherwise linger).
                    self._created_resources[id(worker)] = resources
                    if len(self._created_resources) > 4096:
                        self._created_resources.pop(next(iter(self._created_resources)))
                    return worker
                except Exception as exc:  # noqa: BLE001 - adapters raise several types
                    last = exc
                    # ValueError is always non-transient (a caller bug) — the
                    # module docstring's rule; is_transient_platform_error
                    # matches by class name only, so it is enforced here.
                    if not is_transient_platform_error(exc) or isinstance(exc, ValueError):
                        raise
                    delay = min(
                        self.create_retry_delay_seconds * (2**attempt), 600.0
                    )
                    self.LOGGER.info(
                        "worker creation attempt %d failed transiently (%s: %s); "
                        "retrying in %gs",
                        attempt + 1, type(exc).__name__, exc, delay,
                    )
                    await asyncio.sleep(delay)
            assert last is not None
            raise last

    # Legacy alias: pre-existing callers probe and call this name.
    _create_sandbox = create_sandbox

    def register_long_lived(self, app_name: str, worker: Worker) -> None:
        """Put a worker on the long-lived table (the tunnel-close reaper and
        stop_app work through this registry)."""
        self._long_lived[app_name] = worker
        self._long_lived_resources[app_name] = self._resolve_worker_resources(worker)

    def _resolve_worker_resources(self, worker: Worker) -> WorkerResources | None:
        """The worker's creation-time resources, for memory accounting.

        Preference order: the worker's own ``resources`` attribute (the
        Worker Protocol's OPTIONAL metadata member — an adapter that
        exposes it is authoritative), then the resources this base's
        create_sandbox recorded when the worker was created through it,
        then the legacy duck-chain (``worker.spec.resources``) kept for
        adapters that register foreign workers with the base. None = the
        resources are unknown; the worker then counts as 0 memory rather
        than breaking the sum.
        """
        try:
            own = getattr(worker, "resources", None)
            memory = getattr(own, "memory_mb", None)
            if memory is not None:
                return WorkerResources(
                    cpu_count=int(getattr(own, "cpu_count", 0) or 0),
                    memory_mb=int(memory or 0),
                    storage_mb=(
                        None
                        if getattr(own, "storage_mb", None) is None
                        else int(own.storage_mb)
                    ),
                )
        except Exception:  # noqa: BLE001 - a foreign object must never crash this
            pass
        recorded = self._created_resources.pop(id(worker), None)
        if recorded is not None:
            return recorded
        try:
            spec = getattr(worker, "spec", None)
            legacy = getattr(spec, "resources", None)
            memory = getattr(legacy, "memory_mb", None)
            if memory is not None:
                return WorkerResources(memory_mb=int(memory or 0))
        except Exception:  # noqa: BLE001
            pass
        return None

    def sandbox_for_app(self, app_name: str) -> Worker | None:
        """The live long-lived worker for an app, if any (no state change)."""
        return self._long_lived.get(app_name)

    def long_lived_count(self) -> int:
        """Number of workers on the long-lived table (the /v1/status data source)."""
        return len(self._long_lived)

    def long_lived_memory_mb(self) -> int:
        """Total memory (MiB) of the long-lived table: the memory dimension
        of the global usage pre-check. Sums the per-worker resources
        resolved at register time (see _resolve_worker_resources); workers
        with unknown resources count as 0 rather than breaking the sum (a
        foreign object must never crash a create path)."""
        total = 0
        for app_name in self._long_lived:
            resources = self._long_lived_resources.get(app_name)
            if resources is not None:
                total += int(resources.memory_mb or 0)
        return total

    async def stop_app(self, app_name: str) -> None:
        """Destroy a long-lived worker (its tunnel then drops by itself).

        The agent's log tail is recovered into the service journal first —
        it is the only place with the worker-side last words.
        """
        # Deployment-level warm pools hang off the adapter as an optional
        # ``judge_pool`` attribute (duck-typed hook); the core never imports
        # them.
        pool = getattr(self, "judge_pool", None)
        if pool is not None:
            pool.discard(app_name)
        worker = self._long_lived.pop(app_name, None)
        self._long_lived_resources.pop(app_name, None)
        if worker is None:
            return
        await self._dump_agent_log(app_name, worker)
        try:
            await worker.delete()
        except Exception:  # noqa: BLE001 - best-effort teardown
            pass

    async def _dump_agent_log(self, app_name: str, worker: Worker, *, lines: int = 50) -> None:
        """Best-effort: copy the tail of <work_dir>/agent.log into the journal.

        A dead/unreachable worker simply logs that the tail could not be read.
        """
        try:
            text = await worker.ctrl.read_text(f"{self._work_dir}/agent.log")
        except Exception as exc:  # noqa: BLE001 - worker may be dead already
            self.LOGGER.info(
                "could not read agent.log for %s (%s: %s)", app_name, type(exc).__name__, exc
            )
            return
        tail = "\n".join(text.splitlines()[-lines:])
        self.LOGGER.info("agent.log tail for %s (last %d lines):\n%s", app_name, lines, tail)


def _call_factory(factory: Any, config: Any) -> Any:
    """Call an adapter factory as ``factory(config)`` when it accepts one
    positional argument, else as ``factory()``."""
    try:
        signature = inspect.signature(factory)
    except (TypeError, ValueError):  # exotic callables (C extensions, ...)
        try:
            return factory(config)
        except TypeError:
            return factory()
    takes_config = any(
        p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.VAR_POSITIONAL)
        or (
            p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
            and p.default is inspect.Parameter.empty
        )
        for p in signature.parameters.values()
    )
    return factory(config) if takes_config else factory()


def load_adapter(spec: str, config: Any) -> PlatformAdapter:
    """Resolve the configured platform adapter.

    * ``spec == ""`` — not configured: raises :class:`ConfigurationError`
      (the service must NEVER fall back to a test double silently).
    * ``spec == "local-test"`` — the bundled local-process test adapter
      (:mod:`tcsexam.backend.testing.local_adapter`), an explicit testing
      choice.
    * ``spec == "docker"`` — the bundled Docker Engine adapter
      (:mod:`tcsexam.backend.docker_adapter`), using a local Unix socket.
    * ``spec == "module:factory"`` — import ``module``, call ``factory``
      (with ``config`` when it accepts an argument), and verify the result
      has the full adapter surface.

    Every failure mode raises a readable error listing what is missing;
    nothing here silently degrades.
    """
    if not spec:
        raise ConfigurationError(
            "no platform adapter configured: the backend cannot create judging "
            "workers. Set `adapter` in the config to `docker`, a "
            "`module:factory` spec for your platform, or the explicit "
            "`local-test` value for local testing only."
        )
    if spec == "local-test":
        from .testing.local_adapter import LocalProcessAdapter

        return LocalProcessAdapter(config)
    if spec == "docker":
        from .docker_adapter import DockerAdapter

        return DockerAdapter(config)
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise ConfigurationError(
            f"invalid adapter spec {spec!r}: expected `docker`, "
            "`module:factory`, or the explicit `local-test`"
        )
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ConfigurationError(
            f"adapter spec {spec!r}: cannot import module {module_name!r}: {exc}"
        ) from exc
    factory = getattr(module, attr, None)
    if factory is None or not callable(factory):
        raise ConfigurationError(
            f"adapter spec {spec!r}: {module_name!r} has no callable {attr!r}"
        )
    try:
        adapter = _call_factory(factory, config)
    except Exception as exc:
        raise ConfigurationError(
            f"adapter spec {spec!r}: factory raised {type(exc).__name__}: {exc}"
        ) from exc
    missing = [name for name in _REQUIRED_MEMBERS if not hasattr(adapter, name)]
    if missing:
        raise ConfigurationError(
            f"adapter spec {spec!r}: the loaded adapter {type(adapter).__name__} "
            f"is missing required members: {', '.join(missing)} "
            f"(required: {', '.join(_REQUIRED_MEMBERS)})"
        )
    return adapter
