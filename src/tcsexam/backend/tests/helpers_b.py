"""Shared machinery for the group-B acceptance tests (platform interface,
resource passing, tunnel end-to-end).

This module provides the small pieces the group-B tests need — a service config builder, a live service on a
background event loop, a recording wrapper around the local-process adapter,
a failure-injecting factory adapter, and an in-process synthetic judge pool
(the real ``testing.synthetic_worker._shard_app`` behavior, plus a control
kill mirroring its ctrl-port ``/kill/<port>``).

Everything stays on loopback; the local adapter spawns real agent processes
on this machine (that IS the local adapter's design).
"""
from __future__ import annotations

import asyncio
import json
import socket
import sys
import threading
import time
import types
from pathlib import Path
from typing import Any

# Make `import tcsexam` work without installation (src layout), independent of
# conftest (self-contained suite).
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import aiohttp  # noqa: E402
import aiohttp.web  # noqa: E402

from tcsexam.backend.adapter import BasePlatformAdapter  # noqa: E402
from tcsexam.backend.config import BackendConfig, Config, JudgeSessionsConfig  # noqa: E402
from tcsexam.backend.server import create_app  # noqa: E402
from tcsexam.backend.testing.local_adapter import LocalProcessAdapter  # noqa: E402
from tcsexam.backend.testing.synthetic_worker import _shard_app  # noqa: E402

TOKEN_ID = "groupb-token-id"
TOKEN_SECRET = "groupb-token-secret"
ARCHIVE_TOKEN = "groupb-archive-token"
PUBLIC_IMAGE_MAP = {
    "registry.example.com/family-judge:1.0.0":
        "registry.example.com/family-judge-public-only:1.0.0",
}
TOKEN_HEADERS = {
    "X-TCSEXAM-Token-Id": TOKEN_ID,
    "X-TCSEXAM-Token-Secret": TOKEN_SECRET,
}

#: The in-worker work dir the stores write the agent bundle to (config default).
WORK_DIR = "/tcsexam-backend"

#: Default per-worker spec used by the B fixtures (the config defaults).
DEFAULT_SPEC = {"cpu_count": 4, "memory_mb": 8192, "storage_mb": 20480}


# --------------------------------------------------------------------------- #
# Config + ports
# --------------------------------------------------------------------------- #
def free_port() -> int:
    """One currently-free loopback TCP port (racy by nature, like every
    bind-0-then-close probe; the suites tolerate a rare collision)."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def free_port_range(n: int, attempts: int = 50) -> int:
    """The base of a block of ``n`` consecutive currently-free ports (the
    local adapter hands out judge_port + i, so the block must be contiguous)."""
    for _ in range(attempts):
        base = free_port()
        socks = []
        try:
            for offset in range(n):
                s = socket.socket()
                s.bind(("127.0.0.1", base + offset))
                socks.append(s)
            return base
        except OSError:
            continue
        finally:
            for s in socks:
                s.close()
    raise RuntimeError(f"no free block of {n} consecutive ports found")


def make_config(
    port: int,
    state_dir: Any,
    *,
    public_base_url: str | None = None,
    **judge_overrides: Any,
) -> Config:
    """A Config for the B suites: test token pair, relay-only agent
    (``command: ""`` — the judge server is the synthetic pool, already
    listening), no hibernation, fast failure paths."""
    judge = dict(
        max_sessions=16,
        profile="groupb-profile",
        ttl_seconds=21600.0,
        max_ttl_seconds=46800.0,
        ready_timeout_seconds=30.0,
        idle_ttl_seconds=14400.0,
        reaper_interval_seconds=60.0,
        # The agent only relays: the judge server (synthetic pool) is already
        # up; the agent must not try to start one itself.
        command="",
        judge_port=8082,
        shard_boot_retries=0,
        shard_boot_retry_delay_seconds=0.01,
        hibernate_enabled=False,
        spec=dict(DEFAULT_SPEC),
    )
    judge.update(judge_overrides)
    config = Config(
        host="127.0.0.1",
        port=port,
        advertise_host="127.0.0.1",
        token_id=TOKEN_ID,
        token_secret=TOKEN_SECRET,
        archive_token=ARCHIVE_TOKEN,
        public_image_map=dict(PUBLIC_IMAGE_MAP),
        state_dir=Path(state_dir),
        backend=BackendConfig(
            ready_timeout_seconds=30.0,
            judge_sessions=JudgeSessionsConfig(**judge),
        ),
    )
    if public_base_url is not None:
        config.public_base_url = public_base_url
    return config


# --------------------------------------------------------------------------- #
# Adapters
# --------------------------------------------------------------------------- #
class RecordingAdapter:
    """Recording wrapper around a real adapter (the local-process one): every
    ``create_sandbox`` call is captured verbatim (positional + keyword), then
    delegated. Everything else delegates. The created workers are kept on
    ``workers`` so tests can reach their local roots / delete them directly
    (the tunnel-drop injections)."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.calls: list[dict[str, Any]] = []
        self.workers: list[Any] = []

    async def create_sandbox(self, profile: str, image_url: str, **kwargs: Any) -> Any:
        worker = await self.inner.create_sandbox(profile, image_url, **kwargs)
        self.calls.append({"profile": profile, "image_url": image_url, **kwargs})
        self.workers.append(worker)
        return worker

    def __getattr__(self, name: str) -> Any:
        # ready_timeout_seconds / register_long_lived / sandbox_for_app /
        # long_lived_count / long_lived_memory_mb / stop_app all delegate.
        return getattr(self.inner, name)


class FakeCtrl:
    """In-memory ctrl for the factory adapter's fake workers (the store's
    agent-bundle uploads land here; run() is a no-op success)."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.run_calls: list[str] = []

    async def write_bytes(self, path: str, data: bytes, parents: bool = False) -> None:
        self.files[path] = data

    async def read_text(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path].decode()

    async def run(self, cmd: str, shell: bool = False, text: bool = False, timeout: float = 30, **kw: Any) -> Any:
        self.run_calls.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")


class FakeWorker:
    """A fake worker for the factory adapter: in-memory ctrl, idempotent delete."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.ctrl = FakeCtrl()
        self.deleted = 0

    async def delete(self) -> None:
        self.deleted += 1


class FactoryAdapter(BasePlatformAdapter):
    """A BasePlatformAdapter whose single creation attempt delegates to a
    hook — the failure-injection point for resource-insufficiency and
    error-classification tests.

    The hook receives exactly what ``_create_worker`` receives (including the
    parsed :class:`WorkerResources`); every call is recorded on ``worker_calls``.
    A hook that returns None yields a fresh :class:`FakeWorker`.
    """

    def __init__(self, hook: Any, **kwargs: Any) -> None:
        defaults = dict(create_retries=0, create_retry_delay_seconds=0.01, ready_timeout_seconds=30.0)
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.hook = hook
        self.worker_calls: list[dict[str, Any]] = []
        self._counter = 0

    async def _create_worker(
        self,
        profile: str,
        image_url: str,
        *,
        ttl_seconds: float,
        resources: Any,
        ready_timeout_seconds: float,
        group_name: str | None,
        labels: dict[str, str] | None,
    ) -> Any:
        self.worker_calls.append(
            {
                "profile": profile,
                "image_url": image_url,
                "ttl_seconds": ttl_seconds,
                "resources": resources,
                "ready_timeout_seconds": ready_timeout_seconds,
                "group_name": group_name,
                "labels": labels,
            }
        )
        worker = self.hook(
            profile=profile,
            image_url=image_url,
            ttl_seconds=ttl_seconds,
            resources=resources,
            ready_timeout_seconds=ready_timeout_seconds,
            group_name=group_name,
            labels=labels,
        )
        if worker is not None:
            return worker
        self._counter += 1
        return FakeWorker(f"fake-{self._counter}")


#: Non-transient platform errors by contract (class NAME is what matters).
class PermissionDeniedError(Exception):
    """The platform refuses the request (quota/permission) — non-transient."""


class InsufficientCreditsError(Exception):
    """The platform cannot provide the requested resources — non-transient."""


# --------------------------------------------------------------------------- #
# Live service on a background event loop
# --------------------------------------------------------------------------- #
class ServiceHandle:
    """Handle to a running backend service (see start_service)."""

    def __init__(self) -> None:
        self.url: str = ""
        self.app: Any = None
        self.loop: Any = None
        self.adapter: Any = None
        self.config: Any = None
        self.state_dir: Any = None
        self._runners: list[Any] = []
        self._thread: Any = None

    @property
    def store(self) -> Any:
        return self.app["judge_sessions"]

    @property
    def tunnels(self) -> Any:
        return self.app["tunnels"]

    def run_async(self, coro: Any, timeout: float = 60.0) -> Any:
        """Run a coroutine on the service loop from the test thread."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=timeout)


def start_service(
    state_dir: Any,
    *,
    adapter: Any | None = None,
    public_base_url: str | None = None,
    **judge_overrides: Any,
) -> ServiceHandle:
    """Start the real backend service (create_app) on a background loop.

    ``adapter=None`` builds a RecordingAdapter over the local-process adapter
    (the default for the resource-passing and tunnel suites). The port is
    pre-allocated so the config's public_url matches the bound socket (the
    store hands the in-worker agent a ws URL derived from it).
    """
    handle = ServiceHandle()
    port = free_port()
    config = make_config(port, state_dir, public_base_url=public_base_url, **judge_overrides)
    if adapter is None:
        adapter = RecordingAdapter(LocalProcessAdapter(config))

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    holder: dict[str, Any] = {}

    async def _start() -> list[Any]:
        app = create_app(config, adapter=adapter)
        holder["app"] = app
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, "127.0.0.1", port)
        await site.start()
        return [runner]

    runners = asyncio.run_coroutine_threadsafe(_start(), loop).result(timeout=30)
    handle.url = f"http://127.0.0.1:{port}"
    handle.app = holder["app"]
    handle.loop = loop
    handle.adapter = adapter
    handle.config = config
    handle.state_dir = Path(state_dir)
    handle._runners = runners
    handle._thread = thread
    return handle


def stop_service(handle: ServiceHandle) -> None:
    async def _stop() -> None:
        for runner in handle._runners:
            await runner.cleanup()

    try:
        # Generous timeout: cleanup reaps every session's agent process, and
        # the /proc scan in LocalWorker.delete crawls under host load.
        asyncio.run_coroutine_threadsafe(_stop(), handle.loop).result(timeout=90)
    finally:
        handle.loop.call_soon_threadsafe(handle.loop.stop)
        handle._thread.join(timeout=10)


# --------------------------------------------------------------------------- #
# HTTP + store polling helpers (called from the test thread)
# --------------------------------------------------------------------------- #
async def _http_request(
    handle: ServiceHandle,
    method: str,
    path: str,
    *,
    body: Any = None,
    json_body: Any = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    merged = dict(TOKEN_HEADERS)
    if headers:
        merged.update(headers)
    async with aiohttp.ClientSession() as client:
        async with client.request(
            method, handle.url + path, data=body, json=json_body, headers=merged
        ) as resp:
            return resp.status, await resp.read()


def http_request(handle: ServiceHandle, method: str, path: str, **kwargs: Any) -> tuple[int, bytes]:
    return handle.run_async(_http_request(handle, method, path, **kwargs))


def create_session(handle: ServiceHandle, payload: dict[str, Any]) -> dict[str, Any]:
    """POST /v1/judge/sessions; asserts the 202 contract and returns the body."""
    headers = (
        {"X-TCSEXAM-Archive-Token": ARCHIVE_TOKEN}
        if payload.get("instance_set", "hidden") == "hidden"
        else None
    )
    status, raw = http_request(
        handle, "POST", "/v1/judge/sessions", json_body=payload, headers=headers
    )
    assert status == 202, f"session create answered {status}: {raw.decode()}"
    return json.loads(raw.decode())


def wait_session_status(handle: ServiceHandle, sid: str, timeout: float = 30.0) -> Any:
    """Poll the in-memory store until the session leaves "provisioning"."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        session = handle.store.get(sid)
        if session is None:
            raise AssertionError(f"judge session {sid} vanished from the store")
        if session.status != "provisioning":
            return session
        time.sleep(0.02)
    raise AssertionError(f"judge session {sid} still provisioning after {timeout}s")


def wait_ready(handle: ServiceHandle, sid: str, timeout: float = 30.0) -> Any:
    session = wait_session_status(handle, sid, timeout)
    if session.status != "ready":
        raise AssertionError(f"judge session {sid} is {session.status}: {session.error}")
    return session


def wait_failed(handle: ServiceHandle, sid: str, timeout: float = 30.0) -> Any:
    session = wait_session_status(handle, sid, timeout)
    if session.status != "failed":
        raise AssertionError(f"judge session {sid} is {session.status}, expected failed")
    return session


def wait_until(predicate: Any, timeout: float = 10.0, interval: float = 0.05, what: str = "condition") -> Any:
    """Poll ``predicate`` until it returns a truthy value (returned) or time out."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"{what} did not happen within {timeout}s")


# --------------------------------------------------------------------------- #
# In-process synthetic judge pool
# --------------------------------------------------------------------------- #
class SyntheticPool:
    """The synthetic judge worker, in-process: N shard apps (the real
    ``testing.synthetic_worker._shard_app`` behavior — /health, /submit,
    /submissions with one ok record per shard) on consecutive ports, plus a
    control kill mirroring the standalone process's ctrl-port /kill/<port>.

    Runs on the service's background loop (one loop serves the whole test).
    """

    def __init__(self) -> None:
        self.base_port: int = 0
        self.ports: list[int] = []
        self._sites: dict[int, tuple[Any, Any]] = {}
        self.slow_release: Any = None  # asyncio.Event, set to release /slow

    def start(
        self,
        handle: ServiceHandle,
        n_ports: int = 1,
        *,
        base_port: int | None = None,
        with_slow: bool = False,
    ) -> "SyntheticPool":
        self._handle = handle

        async def _start() -> None:
            self.base_port = base_port if base_port is not None else free_port_range(n_ports)
            self.slow_release = asyncio.Event()
            for offset in range(n_ports):
                port = self.base_port + offset
                app = _shard_app(port)
                if with_slow:

                    async def slow(request: aiohttp.web.Request) -> aiohttp.web.Response:
                        # Released by the test (or teardown); the 30s ceiling
                        # keeps a leaked handler from wedging teardown.
                        try:
                            await asyncio.wait_for(self.slow_release.wait(), timeout=30)
                        except asyncio.TimeoutError:
                            pass
                        return aiohttp.web.json_response({"status": "slow-done"})

                    app.router.add_get("/slow", slow)
                runner = aiohttp.web.AppRunner(app)
                await runner.setup()
                site = aiohttp.web.TCPSite(runner, "127.0.0.1", port)
                await site.start()
                self._sites[port] = (runner, site)
                self.ports.append(port)

        handle.run_async(_start())
        return self

    def kill(self, port: int) -> None:
        """Stop one shard's listener — the standalone synthetic worker's
        ctrl-port ``POST /kill/<port>`` equivalent (the port then refuses
        connections, so the agent's relay gets an upstream failure)."""

        async def _kill() -> bool:
            entry = self._sites.pop(port, None)
            if entry is None:
                return False
            runner, site = entry
            await site.stop()
            await runner.cleanup()
            return True

        was_listening = self._handle.run_async(_kill())
        assert was_listening, f"pool port {port} was not listening"
        self.ports.remove(port)

    def cleanup(self) -> None:
        async def _cleanup() -> None:
            if self.slow_release is not None:
                self.slow_release.set()
            for runner, site in self._sites.values():
                try:
                    await site.stop()
                    await runner.cleanup()
                except Exception:  # noqa: BLE001 - best-effort teardown
                    pass
            self._sites.clear()

        self._handle.run_async(_cleanup())
