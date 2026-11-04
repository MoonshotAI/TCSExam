"""Singleflight create dedup and per-image-family readiness routes.

Store-level tests drive ``sessions_base.JudgeSessionStore.create_shared``
directly against a fake executor/tunnels (full control over creation latency
and cancellation); HTTP-level tests go through the live service fixture (the
sharded store the server wires). No real workers are created.
"""
from __future__ import annotations

import asyncio
import json
import threading
import types
import urllib.error
import urllib.request

import pytest

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
    JudgeSessionRoute,
    JudgeSessionsConfig,
)
from tcsexam.backend.sessions_base import (
    _AGENT_LOG_POLL_SECONDS,
    JudgeSessionStore,
)


class QuotaError(Exception):
    """Name matches a transient platform error."""


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
    """Just the store-facing protocol: create_sandbox/register/stop."""

    def __init__(self, *, delay: float = 0.0, fail_with: BaseException | None = None) -> None:
        self.calls: list[dict] = []
        self.delay = delay
        self.fail_with = fail_with
        self.registered: dict[str, FakeWorker] = {}

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
        return FakeWorker()

    def register_long_lived(self, app_name: str, sandbox) -> None:
        self.registered[app_name] = sandbox

    async def stop_app(self, app_name: str) -> None:
        sandbox = self.registered.pop(app_name, None)
        if sandbox is not None:
            await sandbox.delete()


class FakeTunnels:
    def __init__(self) -> None:
        self.session_tokens: dict[str, str] = {}
        self.wait_calls: list[tuple[str, float]] = []
        self.closed: set[str] = set()

    async def wait_connected(self, app_name: str, timeout: float) -> bool:
        self.wait_calls.append((app_name, timeout))
        return app_name not in self.closed

    def is_connected(self, app_name: str) -> bool:
        return app_name not in self.closed

    async def close(self, app_name: str) -> None:
        self.closed.add(app_name)
        self.session_tokens.pop(app_name, None)


def _store(
    cfg: JudgeSessionsConfig | None = None, executor: FakeExecutor | None = None
) -> tuple[JudgeSessionStore, FakeExecutor]:
    executor = executor or FakeExecutor()
    service_config = BaseServiceConfig(
        host="127.0.0.1", port=8420, advertise_host="127.0.0.1",
        token_id=TOKEN_ID, token_secret=TOKEN_SECRET,
    )
    store = JudgeSessionStore(executor, cfg or JudgeSessionsConfig(), service_config)
    store.attach_tunnels(FakeTunnels())
    return store, executor


KEY = (TOKEN_ID, "registry.example.com/family-judge:1.0.0", "198.51.100.1")


# --------------------------------------------------------------------------- #
# Singleflight semantics (store level)
# --------------------------------------------------------------------------- #
def test_concurrent_same_key_shares_one_creation() -> None:
    async def main() -> None:
        store, executor = _store(executor=FakeExecutor(delay=0.2))
        results = await asyncio.gather(
            *[store.create_shared(KEY, KEY[1], None, None, None) for _ in range(5)]
        )
        assert len(executor.calls) == 1, "the creator ran more than once for one key"
        assert len({r.session_id for r in results}) == 1, "waiters got different sessions"
        assert store._inflight == {}, "the key must settle out of the in-flight table"

    asyncio.run(main())


def test_waiter_cancellation_does_not_cancel_shared_creation() -> None:
    async def main() -> None:
        store, executor = _store(executor=FakeExecutor(delay=0.2))
        leader = asyncio.create_task(store.create_shared(KEY, KEY[1], None, None, None))
        await asyncio.sleep(0.05)  # the leader registers the in-flight task
        waiter = asyncio.create_task(store.create_shared(KEY, KEY[1], None, None, None))
        await asyncio.sleep(0.05)
        waiter.cancel()  # the waiter's client timed out and went away
        with pytest.raises(asyncio.CancelledError):
            await waiter
        session = await leader  # the shared creation is undisturbed
        assert len(executor.calls) == 1
        assert store.get(session.session_id) is session

    asyncio.run(main())


def test_leader_cancellation_keeps_creation_and_later_create_starts_fresh() -> None:
    async def main() -> None:
        store, executor = _store(executor=FakeExecutor(delay=0.2))
        leader = asyncio.create_task(store.create_shared(KEY, KEY[1], None, None, None))
        await asyncio.sleep(0.05)
        leader.cancel()  # the leader's own client went away mid-creation
        with pytest.raises(asyncio.CancelledError):
            await leader
        await asyncio.sleep(0.3)  # the orphaned creation still completes
        assert len(executor.calls) == 1
        orphans = store.live_sessions()
        assert len(orphans) == 1, "the finished creation registers until reaped"
        # The key settled: a later same-key create is a brand-new session (the
        # legitimate rebuild path), not an attach to the finished one.
        session = await store.create_shared(KEY, KEY[1], None, None, None)
        assert len(executor.calls) == 2
        assert session.session_id != orphans[0].session_id

    asyncio.run(main())


def test_leader_failure_reaches_all_waiters_and_retry_elects_new_leader() -> None:
    async def main() -> None:
        executor = FakeExecutor(delay=0.1, fail_with=QuotaError("pool full"))
        store, executor = _store(executor=executor)
        results = await asyncio.gather(
            *[store.create_shared(KEY, KEY[1], None, None, None) for _ in range(4)],
            return_exceptions=True,
        )
        assert len(executor.calls) == 1
        assert all(isinstance(r, QuotaError) for r in results)
        assert len({id(r) for r in results}) == 1, "waiters must share the leader's failure"
        assert store._inflight == {}, "a failed creation settles out of the table"
        executor.fail_with = None  # the caller's retry becomes a new leader
        session = await store.create_shared(KEY, KEY[1], None, None, None)
        assert len(executor.calls) == 2
        assert store.get(session.session_id) is session

    asyncio.run(main())


def test_different_image_and_remote_ip_create_independently() -> None:
    async def main() -> None:
        store, executor = _store(executor=FakeExecutor(delay=0.1))
        keys = [
            (TOKEN_ID, "registry.example.com/a-judge:1", "198.51.100.1"),
            (TOKEN_ID, "registry.example.com/b-judge:1", "198.51.100.1"),  # other image
            (TOKEN_ID, "registry.example.com/a-judge:1", "198.51.100.2"),  # other client
        ]
        results = await asyncio.gather(
            *[store.create_shared(key, key[1], None, None, None) for key in keys]
        )
        assert len(executor.calls) == 3
        assert len({r.session_id for r in results}) == 3

    asyncio.run(main())


def test_singleflight_disabled_falls_back_to_per_request_create() -> None:
    async def main() -> None:
        cfg = JudgeSessionsConfig(singleflight=False)
        store, executor = _store(cfg, FakeExecutor(delay=0.05))
        r1, r2 = await asyncio.gather(
            *[store.create_shared(KEY, KEY[1], None, None, None) for _ in range(2)]
        )
        assert len(executor.calls) == 2
        assert r1.session_id != r2.session_id

    asyncio.run(main())


# --------------------------------------------------------------------------- #
# Readiness routes (store level: all three consumers see the routed values)
# --------------------------------------------------------------------------- #
def test_routed_readiness_reaches_creator_wait_and_agent_config() -> None:
    async def main() -> None:
        cfg = JudgeSessionsConfig(
            routes=[
                JudgeSessionRoute(
                    image_contains="family",
                    ready_timeout_seconds=900.0,
                    create_ready_timeout_seconds=5400.0,
                )
            ]
        )
        store, executor = _store(cfg)
        session = await store.create_shared(KEY, KEY[1], None, None, None)
        assert executor.calls[0]["ready_timeout_seconds"] == 5400.0  # adapter create
        # The tunnel wait runs in agent.log-poll slices of the budget.
        assert store._tunnels.wait_calls[0] == (
            session.session_id,
            min(_AGENT_LOG_POLL_SECONDS, 900.0),
        )
        sandbox = executor.registered[session.session_id]
        agent_config = json.loads(sandbox.ctrl.files[f"{WORK_DIR}/agent_config.json"].decode())
        assert agent_config["boot_timeout_seconds"] == 900.0  # min(route, 7200)

    asyncio.run(main())


def test_unrouted_image_keeps_legacy_budgets_and_call_shape() -> None:
    async def main() -> None:
        store, executor = _store()  # no routes: ready_timeout_seconds 1800 default
        session = await store.create_shared(KEY, KEY[1], None, None, None)
        assert "ready_timeout_seconds" not in executor.calls[0], (
            "no route -> the creator call carries no readiness override"
        )
        assert store._tunnels.wait_calls[0] == (
            session.session_id,
            min(_AGENT_LOG_POLL_SECONDS, 1800.0),
        )
        sandbox = executor.registered[session.session_id]
        agent_config = json.loads(sandbox.ctrl.files[f"{WORK_DIR}/agent_config.json"].decode())
        assert agent_config["boot_timeout_seconds"] == 1800.0

    asyncio.run(main())


# --------------------------------------------------------------------------- #
# HTTP level (live service fixture, recording fake adapter)
# --------------------------------------------------------------------------- #
def _request(url: str, body: dict, extra_headers: dict | None = None) -> tuple[int, bytes]:
    """Raw-byte variant of the endpoint tests' helper (contract snapshots)."""
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-TCSEXAM-Token-Id": TOKEN_ID,
            "X-TCSEXAM-Token-Secret": TOKEN_SECRET,
            "X-TCSEXAM-Archive-Token": ARCHIVE_TOKEN,
            **(extra_headers or {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _post_concurrently(
    jservice, body: dict, count: int, extra_headers: dict | None = None
) -> list[tuple[int, bytes]]:
    results: list[tuple[int, bytes]] = []

    def worker() -> None:
        results.append(_request(f"{jservice.url}/v1/judge/sessions", body, extra_headers))

    threads = [threading.Thread(target=worker) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert len(results) == count
    return results


def test_http_concurrent_same_key_shares_one_session(jservice) -> None:
    jservice.factory.delay_seconds = 1.0  # outlast the spread of the 3 arrivals
    results = _post_concurrently(
        jservice,
        {"judge_image": "registry.example.com/family-judge:1"},
        3,
        extra_headers={"X-TCSEXAM-Client-Id": "test-client"},
    )
    bodies = [json.loads(body) for status, body in results]
    # Every caller immediately gets the same 202 with the shared
    # provisioning session — nobody waits for the creation to finish.
    assert all(status == 202 for status, _ in results), bodies
    assert all(b["status"] == "provisioning" for b in bodies)
    assert len({b["session_id"] for b in bodies}) == 1
    assert len({b["base_url"] for b in bodies}) == 1
    wait_session_ready(jservice, bodies[0]["session_id"])
    # HTTP 202 can arrive before the background factory is scheduled.
    assert len(jservice.factory.calls) == 1, "concurrent retries churned extra workers"


def test_http_concurrent_without_client_id_never_shares(jservice) -> None:
    """No X-TCSEXAM-Client-Id => no sharing: concurrent same-token same-image
    creates must each get their OWN session. A remote-IP fallback would merge
    unrelated runs behind NAT into one provisioning session."""
    jservice.factory.delay_seconds = 1.0
    results = _post_concurrently(jservice, {"judge_image": "registry.example.com/family-judge:1"}, 2)
    bodies = [json.loads(body) for status, body in results]
    assert all(status == 202 for status, _ in results), bodies
    assert len({b["session_id"] for b in bodies}) == 2
    # The 202s return before the background provisions fire — wait for both
    # to finish booting, THEN count the workers actually created.
    for b in bodies:
        wait_session_ready(jservice, b["session_id"])
    assert len(jservice.factory.calls) == 2, "no-header creates must never share"


def test_http_concurrent_waiters_share_identical_failure(jservice) -> None:
    jservice.factory.delay_seconds = 1.0
    jservice.factory.fail_with = QuotaError("pool full")
    jservice.executor.create_retry_delay_seconds = 0.1  # don't sleep out the wait
    results = _post_concurrently(
        jservice,
        {"judge_image": "x/y:1"},
        3,
        extra_headers={"X-TCSEXAM-Client-Id": "test-client"},
    )
    statuses = {status for status, _ in results}
    bodies = {body for _, body in results}
    assert statuses == {202}
    assert len(bodies) == 1, "every caller must receive the same shared session verbatim"
    sid = json.loads(bodies.pop())["session_id"]
    session = wait_session_settled(jservice, sid)
    assert session.status == "failed"
    assert b"please try again" in session.error.encode()
    assert len(jservice.factory.calls) == 1


def test_http_distinct_client_id_headers_create_independently(jservice) -> None:
    """Same token + same image + same remote, but different X-TCSEXAM-Client-Id
    headers: those are distinct logical callers (e.g. two containers on one
    host) and must NOT share an in-flight create."""
    jservice.factory.delay_seconds = 1.0
    results: list[tuple[int, bytes]] = []

    def worker(cid: str) -> None:
        results.append(
            _request(
                f"{jservice.url}/v1/judge/sessions",
                {"judge_image": "registry.example.com/family-judge:1"},
                {"X-TCSEXAM-Client-Id": cid},
            )
        )

    # Two containers: the fixture's session cap is 2 (a third distinct
    # create would legitimately 503 on the cap), and two already prove the
    # point — a false same-key dedup would collapse them into one session.
    threads = [threading.Thread(target=worker, args=(f"container-{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert len(results) == 2
    bodies = [json.loads(body) for _, body in results]
    assert all(status == 202 for status, _ in results)
    assert all(b["status"] == "provisioning" for b in bodies)
    assert len({b["session_id"] for b in bodies}) == 2
    for b in bodies:
        wait_session_ready(jservice, b["session_id"])
    assert len(jservice.factory.calls) == 2, "distinct client ids were wrongly deduped"


def test_http_same_client_id_header_dedupes(jservice) -> None:
    """Concurrent retries carrying the same X-TCSEXAM-Client-Id share one
    in-flight create — the storm-protection path for header-aware clients."""
    jservice.factory.delay_seconds = 1.0
    results: list[tuple[int, bytes]] = []

    def worker() -> None:
        results.append(
            _request(
                f"{jservice.url}/v1/judge/sessions",
                {"judge_image": "registry.example.com/family-judge:2"},
                {"X-TCSEXAM-Client-Id": "one-logical-client"},
            )
        )

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert len(results) == 3
    bodies = [json.loads(body) for _, body in results]
    assert all(status == 202 for status, _ in results)
    assert len({b["session_id"] for b in bodies}) == 1
    wait_session_ready(jservice, bodies[0]["session_id"])
    assert len(jservice.factory.calls) == 1


def test_http_singleflight_disabled_creates_per_request(jservice) -> None:
    jservice.app["judge_sessions"].cfg.singleflight = False
    jservice.factory.delay_seconds = 1.0
    results = _post_concurrently(jservice, {"judge_image": "registry.example.com/family-judge:1"}, 2)
    bodies = [json.loads(body) for status, body in results]
    assert all(status == 202 for status, _ in results), bodies
    assert len({b["session_id"] for b in bodies}) == 2
    for b in bodies:
        wait_session_ready(jservice, b["session_id"])
    assert len(jservice.factory.calls) == 2


def test_error_contract_byte_identical_with_and_without_singleflight(jservice) -> None:
    """The singleflight path must not alter the on-the-wire error contract:
    the failed-session wording and the 503 (cap) body are byte-identical
    whether the toggle is on or off (the task-side retry matchers key on
    these strings)."""
    store = jservice.app["judge_sessions"]

    # Transient platform failure: same failed-session wording both ways.
    jservice.factory.fail_with = QuotaError("pool full")
    jservice.executor.create_retry_delay_seconds = 0.1  # don't sleep out the wait
    on_status, on = _request(f"{jservice.url}/v1/judge/sessions", {"judge_image": "x/y:1"})
    store.cfg.singleflight = False
    off_status, off = _request(f"{jservice.url}/v1/judge/sessions", {"judge_image": "x/y:1"})
    store.cfg.singleflight = True
    assert on_status == off_status == 202
    on_session = wait_session_settled(jservice, json.loads(on)["session_id"])
    off_session = wait_session_settled(jservice, json.loads(off)["session_id"])
    assert on_session.status == off_session.status == "failed"
    assert on_session.error == off_session.error
    assert on_session.error == (
        "judge session create failed: QuotaError: pool full"
        " (transient platform error, please try again)"
    )

    # 503 cap: fill both slots, then compare the over-cap error both ways.
    jservice.factory.fail_with = None
    for i in range(2):
        status, body = _request(
            f"{jservice.url}/v1/judge/sessions", {"judge_image": f"registry.example.com/family-judge:1{i}"}
        )
        assert status == 202, body
        wait_session_ready(jservice, json.loads(body)["session_id"])
    on = _request(f"{jservice.url}/v1/judge/sessions", {"judge_image": "x/y:1"})
    store.cfg.singleflight = False
    off = _request(f"{jservice.url}/v1/judge/sessions", {"judge_image": "x/y:1"})
    assert on == off
    assert on[0] == 503 and b"please try again" in on[1]
