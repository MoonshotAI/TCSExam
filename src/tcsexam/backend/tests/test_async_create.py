"""Asynchronous judge-session creation tests (202 + polling).

POST /v1/judge/sessions registers the session immediately (status
"provisioning", HTTP 202) and runs the worker creation + tunnel wait as a
background task flipping it to "ready" or "failed". Store-level tests drive
``sessions_base.JudgeSessionStore.begin_create`` against fakes (full control
over creation latency, tunnel behavior and cancellation); HTTP-level tests
go through the live service fixture (the sharded store the server wires).
No real workers, no network beyond localhost.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
import types
import urllib.error
import urllib.request

from conftest import (
    ARCHIVE_TOKEN,
    TOKEN_ID,
    TOKEN_SECRET,
    WORK_DIR,
    wait_session_ready,
    wait_session_settled,
)

from tcsexam.backend.config import (
    BaseServiceConfig,
    JudgeSessionsConfig,
)
from tcsexam.backend.errors import PROVISIONING_MESSAGE, TRANSIENT_HINT
from tcsexam.backend.sessions_base import JudgeSessionStore


class QuotaError(Exception):
    """Name matches a transient platform error."""


class AuthenticationError(Exception):
    """Name matches a non-transient platform error."""


# --------------------------------------------------------------------------- #
# Store-level fakes
# --------------------------------------------------------------------------- #
class FakeCtrl:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def write_bytes(self, path: str, data: bytes, parents: bool = False) -> None:
        self.files[path] = data

    async def read_text(self, path: str) -> str:
        return self.files.get(path, b"").decode()

    async def run(self, args, **kwargs):
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")


class FakeWorker:
    def __init__(self) -> None:
        self.ctrl = FakeCtrl()
        self.deleted = 0

    async def delete(self) -> None:
        self.deleted += 1


class FakeExecutor:
    """The store-facing protocol with controllable latency/failure."""

    def __init__(self, *, delay: float = 0.0, fail_with: BaseException | None = None) -> None:
        self.calls: list[dict] = []
        self.delay = delay
        self.fail_with = fail_with
        self.registered: dict[str, FakeWorker] = {}
        self.sandboxes: list[FakeWorker] = []

    async def create_sandbox(
        self, profile, image, *, ttl_seconds=None, spec=None, **kwargs
    ) -> FakeWorker:
        self.calls.append(
            {"profile": profile, "image": image, "ttl_seconds": ttl_seconds, "spec": spec, **kwargs}
        )
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_with is not None:
            raise self.fail_with
        sandbox = FakeWorker()
        self.sandboxes.append(sandbox)
        return sandbox

    def register_long_lived(self, app_name: str, sandbox) -> None:
        self.registered[app_name] = sandbox

    async def stop_app(self, app_name: str) -> None:
        sandbox = self.registered.pop(app_name, None)
        if sandbox is not None:
            await sandbox.delete()


class FakeTunnels:
    """wait_connected modes: "connect" (True), "refuse" (False -> ready
    timeout), "hang" (never -> cancelled by DELETE)."""

    def __init__(self, mode: str = "connect") -> None:
        self.session_tokens: dict[str, str] = {}
        self.mode = mode
        self.wait_calls: list[tuple[str, float]] = []
        self.closed: set[str] = set()

    async def wait_connected(self, app_name: str, timeout: float) -> bool:
        self.wait_calls.append((app_name, timeout))
        if self.mode == "connect":
            return app_name not in self.closed
        if self.mode == "refuse":
            return False
        await asyncio.Event().wait()  # hang forever
        return False  # unreachable

    def is_connected(self, app_name: str) -> bool:
        return self.mode == "connect" and app_name not in self.closed

    async def close(self, app_name: str) -> None:
        self.closed.add(app_name)
        self.session_tokens.pop(app_name, None)

    def in_flight(self, app_name: str) -> int:
        return 0


def _store(
    cfg: JudgeSessionsConfig | None = None,
    executor: FakeExecutor | None = None,
    tunnels: FakeTunnels | None = None,
) -> tuple[JudgeSessionStore, FakeExecutor, FakeTunnels]:
    executor = executor or FakeExecutor()
    tunnels = tunnels or FakeTunnels()
    service_config = BaseServiceConfig(
        host="127.0.0.1", port=8420, advertise_host="127.0.0.1",
        token_id=TOKEN_ID, token_secret=TOKEN_SECRET,
    )
    store = JudgeSessionStore(executor, cfg or JudgeSessionsConfig(), service_config)
    store.attach_tunnels(tunnels)
    return store, executor, tunnels


KEY = (TOKEN_ID, "registry.example.com/family-judge:1.0.0", "client-1")


# --------------------------------------------------------------------------- #
# Store level: registration, singleflight sharing, state machine
# --------------------------------------------------------------------------- #
def test_begin_create_registers_provisioning_and_returns_immediately() -> None:
    async def main() -> None:
        store, executor, _ = _store(executor=FakeExecutor(delay=0.5))
        started = time.monotonic()
        session = store.begin_create(KEY, KEY[1], None, None, None)
        elapsed = time.monotonic() - started
        assert elapsed < 0.3, "begin_create blocked on the creation"
        assert session.status == "provisioning"
        assert session.error == ""
        assert store.get(session.session_id) is session
        # The creation is still running in the background.
        ready = await store._wait_provision(session)
        assert ready.status == "ready"
        assert len(executor.calls) == 1

    asyncio.run(main())


def test_concurrent_begin_create_same_key_shares_one_provisioning_session() -> None:
    async def main() -> None:
        store, executor, _ = _store(executor=FakeExecutor(delay=0.3))
        # Five callers arriving before the provision task's first step — the
        # same interleaving the HTTP path produces for concurrent requests
        # (the task only starts running at the next loop await).
        sessions = [store.begin_create(KEY, KEY[1], None, None, None) for _ in range(5)]
        assert len({s.session_id for s in sessions}) == 1, "same key churned extra sessions"
        assert all(s.status == "provisioning" for s in sessions)
        assert executor.calls == [], "the creator must not have run yet (no loop await)"
        assert store._inflight != {}, "the key must be in flight while creating"
        ready = await asyncio.gather(*[store._wait_provision(s) for s in sessions])
        assert all(s.status == "ready" for s in ready)
        assert len(executor.calls) == 1, "the creator ran more than once for one key"
        assert store._inflight == {}, "the key must settle out of the in-flight table"

    asyncio.run(main())


def test_creator_failure_marks_failed_with_contract_wording() -> None:
    async def main() -> None:
        store, executor, _ = _store(executor=FakeExecutor(fail_with=QuotaError("pool full")))
        session = store.begin_create(KEY, KEY[1], None, None, None)
        try:
            await store._wait_provision(session)
        except QuotaError:
            pass
        else:
            raise AssertionError("the original exception must reach the waiter")
        assert session.status == "failed"
        assert session.error == (
            "judge session create failed: QuotaError: pool full"
            " (transient platform error, please try again)"
        )
        assert store._inflight == {}
        # A failed session does not count against the cap: a retry can start.
        executor.fail_with = None
        fresh = store.begin_create(KEY, KEY[1], None, None, None)
        assert fresh.session_id != session.session_id
        assert (await store._wait_provision(fresh)).status == "ready"

    asyncio.run(main())


def test_non_transient_failure_has_no_retry_hint() -> None:
    async def main() -> None:
        store, _, _ = _store(executor=FakeExecutor(fail_with=AuthenticationError("bad token")))
        session = store.begin_create(KEY, KEY[1], None, None, None)
        try:
            await store._wait_provision(session)
        except AuthenticationError:
            pass
        assert session.status == "failed"
        assert session.error == "judge session create failed: AuthenticationError: bad token"
        assert "please try again" not in session.error

    asyncio.run(main())


def test_ready_timeout_marks_failed_and_recycles_the_worker() -> None:
    async def main() -> None:
        # Small budget: the store waits in polled slices, so the test would
        # otherwise sit out the 1800s default.
        store, executor, tunnels = _store(
            cfg=JudgeSessionsConfig(ready_timeout_seconds=0.5),
            tunnels=FakeTunnels(mode="refuse"),
        )
        session = store.begin_create(KEY, KEY[1], None, None, None)
        try:
            await store._wait_provision(session)
        except RuntimeError:
            pass
        else:
            raise AssertionError("the not-connected RuntimeError must reach the waiter")
        assert session.status == "failed"
        assert "did not connect" in session.error
        assert "please try again" in session.error  # RuntimeError is transient-class
        assert len(executor.sandboxes) == 1
        assert executor.sandboxes[0].deleted == 1, "the worker was not recycled"
        assert executor.registered == {}, "a failed session must not register long-lived"

    asyncio.run(main())


def test_boot_failure_sentinel_fails_fast_with_judge_wording() -> None:
    # The in-worker agent writes BOOT-FATAL to agent.log when the
    # judge server dies at boot or reports the terminal {"status": "error"}
    # health state; the store's sliced tunnel wait spots it and fails the
    # session in seconds (not after the whole ready budget).
    async def main() -> None:
        started = time.monotonic()
        store, executor, tunnels = _store(
            cfg=JudgeSessionsConfig(ready_timeout_seconds=1800.0),
            tunnels=FakeTunnels(mode="refuse"),
        )
        session = store.begin_create(KEY, KEY[1], None, None, None)
        while not executor.sandboxes:
            await asyncio.sleep(0.01)
        executor.sandboxes[0].ctrl.files[f"{store.cfg.work_dir}/agent.log"] = (
            b"[sandbox_agent 05:11:32] starting judge server (python3 /judge/judge_worker.py, port=8082)\n"
            b"[sandbox_agent 05:11:34] BOOT-FATAL: judge assets missing: /judge/bench/run_bench.py\n"
        )
        try:
            await store._wait_provision(session)
        except RuntimeError:
            pass
        else:
            raise AssertionError("the boot-failure RuntimeError must reach the waiter")
        assert session.status == "failed"
        assert (
            "judge server failed during boot: judge assets missing: /judge/bench/run_bench.py"
            in session.error
        )
        # A broken judge image is NOT transient: the retry hint must be absent.
        assert "please try again" not in session.error
        assert executor.sandboxes[0].deleted == 1, "the worker was not recycled"
        assert executor.registered == {}, "a failed session must not register long-lived"
        assert time.monotonic() - started < 30, "boot failure must fail fast, not wait out the budget"

    asyncio.run(main())


# --------------------------------------------------------------------------- #
# Failed retention / tunnel reconnect grace
# --------------------------------------------------------------------------- #
def test_failed_session_reaped_after_retention() -> None:
    async def main() -> None:
        store, _, _ = _store(executor=FakeExecutor(fail_with=RuntimeError("boom")))
        session = store.begin_create(KEY, KEY[1], None, None, None)
        try:
            await store._wait_provision(session)
        except RuntimeError:
            pass
        assert session.status == "failed"
        await store._reap_once()
        assert store.get(session.session_id) is not None, "fresh failed sessions are kept for polling"
        session.last_active -= 3601
        await store._reap_once()
        assert store.get(session.session_id) is None, "stale failed sessions are reaped"

    asyncio.run(main())


def test_tunnel_down_within_grace_is_held_then_reaped() -> None:
    async def main() -> None:
        store, executor, tunnels = _store(tunnels=FakeTunnels(mode="connect"))
        session = await store.create_shared(KEY, KEY[1], None, None, None)
        assert session.status == "ready"
        # Tunnel drops: the store claims the close (the project layer must
        # then NOT tear the worker down).
        tunnels.mode = "refuse"
        assert store.claim_tunnel_close(session.app_name) is True
        assert session.tunnel_down_at > 0
        await store._reap_once()
        assert store.get(session.session_id) is not None, "within grace the session is held"
        assert executor.sandboxes[0].deleted == 0, "the worker is held too"
        # The grace elapses without a reconnect: reaped.
        session.tunnel_down_at -= store.cfg.tunnel_reconnect_grace_seconds + 1
        await store._reap_once()
        assert store.get(session.session_id) is None
        assert executor.sandboxes[0].deleted == 1

    asyncio.run(main())


def test_tunnel_reconnect_within_grace_resumes_session() -> None:
    async def main() -> None:
        store, executor, tunnels = _store(tunnels=FakeTunnels(mode="connect"))
        session = await store.create_shared(KEY, KEY[1], None, None, None)
        tunnels.mode = "refuse"
        assert store.claim_tunnel_close(session.app_name) is True
        # The agent redials before the grace ends.
        tunnels.mode = "connect"
        await store._reap_once()
        assert session.tunnel_down_at == 0.0, "the reaper clears the drop mark on reconnect"
        assert store.get(session.session_id) is not None
        assert executor.sandboxes[0].deleted == 0
        # A later unrelated close beyond grace still reaps (the mark was cleared).
        tunnels.mode = "refuse"
        store.claim_tunnel_close(session.app_name)
        session.tunnel_down_at -= store.cfg.tunnel_reconnect_grace_seconds + 1
        await store._reap_once()
        assert store.get(session.session_id) is None

    asyncio.run(main())


def test_claim_tunnel_close_rejects_unknown_and_non_ready() -> None:
    store, _, _ = _store()
    assert store.claim_tunnel_close("jsess-doesnotexist") is False

    async def main() -> None:
        store, executor, _ = _store(tunnels=FakeTunnels(mode="hang"))
        session = store.begin_create(KEY, KEY[1], None, None, None)
        # Wait until the worker exists and the task blocks in wait_connected.
        while not executor.sandboxes:
            await asyncio.sleep(0.01)
        sid = session.session_id
        assert await store.destroy(sid) is True
        assert store.get(sid) is None
        task = store._provision_tasks.get(sid)
        assert task is None, "destroy must drop the provision task"
        assert session.destroyed is True
        # The cancelled task must not rewrite the destroyed session's state.
        assert session.status == "provisioning"
        assert executor.sandboxes[0].deleted == 1, "the worker was not recycled"
        assert executor.registered == {}, "nothing may register after destroy"
        # Give the loop a beat: no resurrection, no late state write.
        await asyncio.sleep(0.05)
        assert store.get(sid) is None
        assert session.status == "provisioning"

    asyncio.run(main())


def test_provisioning_session_is_not_idle_reaped() -> None:
    async def main() -> None:
        store, executor, _ = _store(tunnels=FakeTunnels(mode="hang"))
        session = store.begin_create(KEY, KEY[1], None, None, None)
        while not executor.sandboxes:
            await asyncio.sleep(0.01)
        # The reaper must skip provisioning sessions (their tunnel is down by
        # definition; reaping here would cancel every in-flight creation).
        session.last_active = time.time() - 10_000
        await store._reap_once()
        assert store.get(session.session_id) is session
        assert session.destroyed is False
        await store.destroy(session.session_id)

    asyncio.run(main())


# --------------------------------------------------------------------------- #
# HTTP level (live service fixture, recording fake adapter; the server wires
# the SHARDED session store — a single-shard session is the base shape)
# --------------------------------------------------------------------------- #
def _request(url: str, body=None, *, method: str = "POST", headers=None) -> tuple[int, bytes]:
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {
        "Content-Type": "application/json",
        "X-TCSEXAM-Token-Id": TOKEN_ID,
        "X-TCSEXAM-Token-Secret": TOKEN_SECRET,
    }
    if isinstance(body, dict) and body.get("instance_set", "hidden") == "hidden":
        hdrs["X-TCSEXAM-Archive-Token"] = ARCHIVE_TOKEN
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_post_returns_202_immediately_while_creation_is_delayed(jservice) -> None:
    jservice.factory.delay_seconds = 3.0  # the creation outlasts the POST by far
    started = time.monotonic()
    status, body = _request(
        f"{jservice.url}/v1/judge/sessions",
        {"judge_image": "registry.example.com/family-judge:1.0.0"},
    )
    elapsed = time.monotonic() - started
    assert elapsed < 2.0, "the POST blocked on the creation"
    assert status == 202
    resp = json.loads(body)
    # The synchronous body keys plus the async-creation status and the
    # sharded store's n_shards / instance_set.
    assert set(resp) == {
        "session_id", "base_url", "url", "image", "expires_at", "status",
        "n_shards", "instance_set",
    }
    assert resp["session_id"].startswith("jsess-")
    assert resp["status"] == "provisioning"
    assert resp["n_shards"] == 1
    assert resp["instance_set"] == "hidden"
    assert resp["base_url"].endswith(f"/v1/judge/sessions/{resp['session_id']}")
    assert resp["url"] == resp["base_url"]
    assert resp["expires_at"] > time.time()
    wait_session_ready(jservice, resp["session_id"])


def test_concurrent_posts_share_one_provisioning_session(jservice) -> None:
    jservice.factory.delay_seconds = 1.5
    results: list[tuple[int, bytes]] = []

    def worker() -> None:
        results.append(
            _request(
                f"{jservice.url}/v1/judge/sessions",
                {"judge_image": "registry.example.com/family-judge:1.0.0"},
                headers={"X-TCSEXAM-Client-Id": "one-logical-client"},
            )
        )

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert len(results) == 4
    bodies = [json.loads(body) for _, body in results]
    assert all(status == 202 for status, _ in results), bodies
    assert all(b["status"] == "provisioning" for b in bodies)
    assert len({b["session_id"] for b in bodies}) == 1
    wait_session_ready(jservice, bodies[0]["session_id"])
    assert len(jservice.factory.calls) == 1, "concurrent retries churned extra workers"


def test_provisioning_relay_is_503_transient_then_ready_relays(jservice) -> None:
    jservice.factory.delay_seconds = 2.0
    status, body = _request(
        f"{jservice.url}/v1/judge/sessions",
        {"judge_image": "registry.example.com/family-judge:1.0.0"},
    )
    assert status == 202
    sid = json.loads(body)["session_id"]
    base = f"{jservice.url}/v1/judge/sessions/{sid}"

    expected = {
        "error": PROVISIONING_MESSAGE,
        "error_class": "transient",
    }
    # Judge traffic of every shape (GET relay, submit, submissions) answers
    # the same 503 transient while provisioning.
    status, resp = _request(f"{base}/health", method="GET")
    assert status == 503 and json.loads(resp) == expected
    status, resp = _request(f"{base}/submit", {"code": "x"})
    assert status == 503 and json.loads(resp) == expected
    status, resp = _request(f"{base}/submissions", method="GET")
    assert status == 503 and json.loads(resp) == expected

    wait_session_ready(jservice, sid)
    status, resp = _request(f"{base}/health", method="GET")
    assert status == 200 and json.loads(resp)["status"] == "ok"


def test_status_endpoint_tracks_provisioning_to_ready(jservice) -> None:
    jservice.factory.delay_seconds = 2.0
    status, body = _request(
        f"{jservice.url}/v1/judge/sessions",
        {"judge_image": "registry.example.com/family-judge:1.0.0"},
    )
    assert status == 202
    sid = json.loads(body)["session_id"]

    status, info = _request(f"{jservice.url}/v1/judge/sessions/{sid}", method="GET")
    assert status == 200
    info = json.loads(info)
    assert info["status"] == "provisioning"
    assert info["error"] == ""
    assert info["tunnel_connected"] is False

    wait_session_ready(jservice, sid)
    status, info = _request(f"{jservice.url}/v1/judge/sessions/{sid}", method="GET")
    assert status == 200
    info = json.loads(info)
    assert info["status"] == "ready"
    assert info["error"] == ""
    assert info["tunnel_connected"] is True


def test_failed_creation_is_pollable_on_the_status_endpoint(jservice) -> None:
    jservice.factory.fail_with = QuotaError("pool full")
    jservice.executor.create_retry_delay_seconds = 0.1  # don't sleep out the wait
    status, body = _request(
        f"{jservice.url}/v1/judge/sessions", {"judge_image": "x/y:1"}
    )
    assert status == 202
    sid = json.loads(body)["session_id"]
    session = wait_session_settled(jservice, sid)
    assert session.status == "failed"
    status, info = _request(f"{jservice.url}/v1/judge/sessions/{sid}", method="GET")
    assert status == 200
    info = json.loads(info)
    assert info["status"] == "failed"
    assert info["error"] == session.error
    assert "QuotaError" in info["error"]
    assert "please try again" in info["error"]


def test_delete_provisioning_session_over_http(jservice) -> None:
    jservice.factory.delay_seconds = 30.0  # the creation outlasts the DELETE
    status, body = _request(
        f"{jservice.url}/v1/judge/sessions",
        {"judge_image": "registry.example.com/family-judge:1.0.0"},
    )
    assert status == 202
    sid = json.loads(body)["session_id"]
    status, resp = _request(f"{jservice.url}/v1/judge/sessions/{sid}", method="DELETE")
    assert status == 200 and json.loads(resp)["stopped"] is True
    status, _ = _request(f"{jservice.url}/v1/judge/sessions/{sid}", method="GET")
    assert status == 410  # destroyed sessions answer 410 Gone (terminal)
    # The interrupted creation must not resurrect the session nor rewrite
    # the destroyed entry's state.
    store = jservice.app["judge_sessions"]
    destroyed = [s for s in store._destroyed if s.session_id == sid]
    assert len(destroyed) == 1
    deadline = time.time() + 5
    while time.time() < deadline:
        if destroyed[0].status != "provisioning":
            break
        time.sleep(0.05)
    assert destroyed[0].status == "provisioning", "the cancelled task rewrote the state"
    assert store._provision_tasks.get(sid) is None


# --------------------------------------------------------------------------- #
# Wire contract
# --------------------------------------------------------------------------- #
def test_provisioning_message_is_wire_contract() -> None:
    assert PROVISIONING_MESSAGE == "judge session is still provisioning; please try again"
    assert TRANSIENT_HINT in PROVISIONING_MESSAGE


# --------------------------------------------------------------------------- #
# Provisioning janitor: wall-clock deadline for the whole flow
# --------------------------------------------------------------------------- #
def _poll_status(url: str, sid: str, want: str, timeout: float = 15.0) -> dict:
    import time as _time
    deadline = _time.time() + timeout
    last = {}
    while _time.time() < deadline:
        status, body = _request(f"{url}/v1/judge/sessions/{sid}", method="GET")
        if status == 200:
            last = json.loads(body)
            if last.get("status") == want:
                return last
        _time.sleep(0.5)
    raise AssertionError(f"session {sid} never reached status={want}: last={last.get('status')}")


def test_provisioning_janitor_marks_failed_and_releases_key(jservice) -> None:
    """A provision task that never completes (create never answered) must be
    bounded by the janitor: session -> failed with transient wording, the
    singleflight key settles (next same-key POST leads a fresh create)."""
    jservice.factory.delay_seconds = 3600.0  # create never finishes in-test
    store = jservice.app["judge_sessions"]
    store.cfg.ready_timeout_seconds = 0.2
    store.cfg.provision_janitor_margin_seconds = 0.3
    store._executor.ready_timeout_seconds = 0.2  # create_budget
    body = {"judge_image": "registry.example.com/family-judge:1"}
    status, resp = _request(f"{jservice.url}/v1/judge/sessions", body)
    assert status == 202, resp
    sid = json.loads(resp)["session_id"]

    settled = _poll_status(jservice.url, sid, "failed")
    assert settled["error"].startswith(
        "judge session create failed: RuntimeError: provisioning deadline exceeded"
    ), settled["error"]
    assert "transient platform error" in settled["error"]

    # Key released: a same-key POST is a brand-new leader (not stuck on the wedge).
    status2, resp2 = _request(f"{jservice.url}/v1/judge/sessions", body)
    assert status2 == 202, resp2
    assert json.loads(resp2)["session_id"] != sid
