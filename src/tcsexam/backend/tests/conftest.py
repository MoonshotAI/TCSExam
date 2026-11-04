"""Shared fixtures: a recording fake-adapter (in-memory fake workers) and a
live backend service on a background event loop with a toy judge upstream.

No real platform workers are created, no credentials are needed, nothing
leaves localhost. The fake adapter drives :class:`BasePlatformAdapter` with
an in-memory factory; when the store launches ``judge_session_agent.py``
inside a fake worker, the harness runs the REAL tunnel client code
(:class:`WSClient`/:class:`TunnelClient` from the agent bundle) in a daemon
thread against the toy judge upstream — exactly what the in-worker agent
would do.
"""
from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
import types
from pathlib import Path

import pytest

# Make `import tcsexam` work without installation (src layout).
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import aiohttp.web  # noqa: E402

from tcsexam.backend.adapter import BasePlatformAdapter  # noqa: E402
from tcsexam.backend.agent_files.sandbox_agent import TunnelClient, WSClient  # noqa: E402
from tcsexam.backend.config import BackendConfig, Config, JudgeSessionsConfig  # noqa: E402
from tcsexam.backend.server import create_app  # noqa: E402
from tcsexam.backend.tunnel_protocol import CONTROL_ID, T_READY  # noqa: E402

TOKEN_ID = "test-token-id"
TOKEN_SECRET = "test-token-secret"
ARCHIVE_TOKEN = "test-archive-token"
PUBLIC_IMAGE_MAP = {
    "registry.example.com/family-judge:1.0.0":
        "registry.example.com/family-judge-public-only:1.0.0",
}

#: The in-worker work dir the store writes the agent bundle to (config default).
WORK_DIR = "/tcsexam-backend"


def wait_session_settled(handle, sid: str, timeout: float = 30.0):
    """Poll the in-memory store until the session leaves "provisioning".

    Reads the store directly (no HTTP traffic) so request-counting
    assertions in the status endpoint tests stay exact. Returns the session;
    raises AssertionError on failure or timeout.
    """
    store = handle.app["judge_sessions"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        session = store.get(sid)
        if session is None:
            break
        if session.status in ("ready", "failed"):
            return session
        time.sleep(0.02)
    raise AssertionError(f"judge session {sid} did not settle within {timeout}s")


def wait_session_ready(handle, sid: str, timeout: float = 30.0):
    """Poll the store until the session is ready (AssertionError otherwise)."""
    session = wait_session_settled(handle, sid, timeout)
    if session.status != "ready":
        raise AssertionError(f"judge session {sid} is {session.status}: {session.error}")
    return session


class FakeCtrl:
    """File writes plus an agent-start hook: when the store launches
    judge_session_agent.py, we run the REAL tunnel client in-process against
    the toy judge upstream (what the in-worker agent would do)."""

    def __init__(self, harness) -> None:
        self.harness = harness
        self.files: dict[str, bytes] = {}
        self.run_calls: list[dict] = []

    async def write_bytes(self, path: str, data: bytes, parents: bool = False) -> None:
        self.files[path] = data

    async def read_text(self, path: str) -> str:
        return self.files.get(path, b"").decode()

    async def run(self, args, shell=False, text=False, timeout=None, env=None, **kw):
        self.run_calls.append({"args": args, "timeout": timeout})
        if "judge_session_agent.py" in str(args):
            config = json.loads(self.files[f"{WORK_DIR}/agent_config.json"].decode())
            self.harness.connect_agent(config)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")


class FakeSandbox:
    def __init__(self, harness) -> None:
        self.ctrl = FakeCtrl(harness)
        self.deleted = 0

    async def delete(self) -> None:
        self.deleted += 1


class FakeFactory:
    """The worker-creation hook behind the recording fake adapter."""

    def __init__(self, harness) -> None:
        self.harness = harness
        self.calls: list[dict] = []
        self.sandboxes: list[FakeSandbox] = []
        self.fail_with: BaseException | None = None
        self.delay_seconds = 0.0  # simulated creation latency (singleflight tests)

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.fail_with is not None:
            raise self.fail_with
        sandbox = FakeSandbox(self.harness)
        self.sandboxes.append(sandbox)
        return sandbox


class FactoryAdapter(BasePlatformAdapter):
    """A BasePlatformAdapter whose single creation attempt delegates to the
    in-memory fake factory (the migrated StubExecutor role)."""

    def __init__(self, factory, **kwargs) -> None:
        defaults = dict(create_retries=0, ready_timeout_seconds=30.0)
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.factory = factory

    async def _create_worker(
        self,
        profile: str,
        image_url: str,
        *,
        ttl_seconds: float,
        resources,
        ready_timeout_seconds: float,
        group_name: str | None,
        labels: dict[str, str] | None,
    ):
        return await self.factory(
            profile=profile,
            image_url=image_url,
            ttl_seconds=ttl_seconds,
            resources=resources,
            ready_timeout_seconds=ready_timeout_seconds,
            group_name=group_name,
            labels=labels,
        )


class _Harness:
    def __init__(self) -> None:
        self.agents: list[TunnelClient] = []
        self._agent_ready: list[threading.Event] = []

    def connect_agent(self, config: dict) -> None:
        """Run the real sandbox-agent tunnel client in a daemon thread.

        The agent sends its READY control frame right after connecting, like
        the in-worker judge_session_agent does (the service treats it as
        informational; the tunnel-lifecycle tests assert on ready_info).
        """
        ready = threading.Event()
        self._agent_ready.append(ready)

        def _run() -> None:
            ws = WSClient(
                config["service_ws_url"],
                headers={
                    "X-TCSEXAM-Token-Id": config.get("token_id") or "",
                    "X-TCSEXAM-Token-Secret": config.get("token_secret") or "",
                },
            )
            ws.connect()
            client = TunnelClient(ws, target_port=self.toy_port)
            self.agents.append(client)
            client.send_frame(
                T_READY,
                CONTROL_ID,
                json.dumps(
                    {
                        "app_name": config.get("app_name", ""),
                        "port": self.toy_port,
                        "label": config.get("ready_label", ""),
                    }
                ).encode(),
            )
            ready.set()
            client.run_forever()

        threading.Thread(target=_run, daemon=True).start()

    def close_agents(self) -> None:
        # The agent thread appends itself after the WS handshake, which can
        # land AFTER session create returns (the server sees the tunnel
        # first); wait so a close never misses a late-registering agent.
        for event in self._agent_ready:
            event.wait(timeout=10)
        for client in self.agents:
            client.ws.close()


def make_service_config(port: int, state_dir, **judge_overrides) -> Config:
    """The jservice fixture's Config: sharded session store wiring, fast
    failure paths (no shard-boot retries), the test token pair."""
    judge = dict(
        max_sessions=2,
        profile="test-profile",
        ttl_seconds=21600,
        ready_timeout_seconds=30,
        idle_ttl_seconds=14400,
        reaper_interval_seconds=60,
        shard_boot_retries=0,
        shard_boot_retry_delay_seconds=0.01,
        # The migrated lifecycle tests exercise the destroy-based reaper;
        # hibernation is covered by its own suite (test_session_hibernate.py)
        # and the C4/E1 acceptance tests.
        hibernate_enabled=False,
        spec={"cpu_count": 4, "memory_mb": 8192, "storage_mb": 20480},
    )
    judge.update(judge_overrides)
    return Config(
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


def build_toy_app(extra_routes=None) -> aiohttp.web.Application:
    """The toy judge upstream: the health/submit/submissions/evaluate
    endpoints the core tests relay to (plus /slow for in-flight aborts)."""
    toy = aiohttp.web.Application()

    async def health(request):
        return aiohttp.web.json_response({"status": "ok", "ready": True})

    async def submit(request):
        body = await request.json()
        return aiohttp.web.json_response(
            {
                "submission_uuid": "toy-uuid-1",
                "status": "queued",
                "role_token_seen": request.headers.get("X-TCSExam-Role-Token") or "",
                "code_len": len(body.get("code") or ""),
            }
        )

    async def submissions(request):
        return aiohttp.web.json_response({"submissions": []})

    async def evaluate(request):
        return aiohttp.web.json_response(
            {
                "status": "done",
                "score": 0.0,
                "role_token_seen": request.headers.get("X-TCSExam-Role-Token") or "",
            }
        )

    async def slow(request):
        await asyncio.sleep(30)
        return aiohttp.web.json_response({"status": "slow-done"})

    toy.router.add_get("/health", health)
    toy.router.add_post("/submit", submit)
    toy.router.add_get("/submissions", submissions)
    toy.router.add_post("/evaluate", evaluate)
    toy.router.add_get("/slow", slow)
    if extra_routes:
        for method, path, handler in extra_routes:
            toy.router.add_route(method, path, handler)
    return toy


@pytest.fixture
def jservice(tmp_path):
    """Backend service with a recording fake adapter + toy judge upstream.

    The port is pre-allocated so the config's public_url matches the bound
    socket (the store hands the in-worker agent a ws URL derived from it).
    """
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    config = make_service_config(port, tmp_path)
    harness = _Harness()
    factory = FakeFactory(harness)
    adapter = FactoryAdapter(factory)

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    async def _start() -> tuple[int, list, object]:
        toy = build_toy_app()
        toy_runner = aiohttp.web.AppRunner(toy)
        await toy_runner.setup()
        toy_site = aiohttp.web.TCPSite(toy_runner, "127.0.0.1", 0)
        await toy_site.start()
        toy_port = toy_site._server.sockets[0].getsockname()[1]

        app = create_app(config, adapter=adapter)
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, "127.0.0.1", port)
        await site.start()
        return toy_port, [runner, toy_runner], app

    harness.toy_port, runners, app = asyncio.run_coroutine_threadsafe(_start(), loop).result(
        timeout=30
    )
    handle = types.SimpleNamespace(
        url=f"http://127.0.0.1:{port}",
        factory=factory,
        executor=adapter,  # historical name: the platform adapter
        adapter=adapter,
        config=config,
        app=app,
        loop=loop,
        harness=harness,
        state_dir=tmp_path,
    )
    yield handle
    harness.close_agents()  # open tunnels would stall the aiohttp shutdown

    async def _stop() -> None:
        for runner in runners:
            await runner.cleanup()

    asyncio.run_coroutine_threadsafe(_stop(), loop).result(timeout=30)
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=10)
