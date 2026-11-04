"""Session list endpoint tests: GET /v1/judge/sessions returns live
sessions plus the recent destroyed tail (DESTROYED_SESSIONS_KEEP), sorted by
created desc, capped at SESSION_LIST_LIMIT, with family normalization reused
from status.image_family.

All stub/fake based: no real workers, no network beyond localhost.
"""
from __future__ import annotations

import asyncio
import json
import types
import urllib.error
import urllib.request

from conftest import ARCHIVE_TOKEN, TOKEN_ID, TOKEN_SECRET

from tcsexam.backend.config import BaseServiceConfig, JudgeSessionsConfig
from tcsexam.backend.sessions_base import (
    DESTROYED_SESSIONS_KEEP,
    SESSION_LIST_LIMIT,
    JudgeSessionStore,
)


# --------------------------------------------------------------------------- #
# Store-level fakes (same pattern as test_run_id.py)
# --------------------------------------------------------------------------- #
class _FakeCtrl:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def write_bytes(self, path: str, data: bytes, parents: bool = False) -> None:
        self.files[path] = data

    async def read_text(self, path: str) -> str:
        return self.files.get(path, b"").decode()

    async def run(self, args, **kwargs):
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")


class _FakeWorker:
    def __init__(self) -> None:
        self.ctrl = _FakeCtrl()

    async def delete(self) -> None:
        pass


class _FakeExecutor:
    def __init__(self) -> None:
        self.registered: dict = {}

    async def create_sandbox(self, profile, image, *, ttl_seconds=None, spec=None, **kwargs):
        return _FakeWorker()

    def register_long_lived(self, app_name: str, sandbox) -> None:
        self.registered[app_name] = sandbox

    async def stop_app(self, app_name: str) -> None:
        self.registered.pop(app_name, None)


class _FakeTunnels:
    def __init__(self) -> None:
        self.session_tokens: dict[str, str] = {}
        self.closed: set[str] = set()

    async def wait_connected(self, app_name: str, timeout: float) -> bool:
        return app_name not in self.closed

    def is_connected(self, app_name: str) -> bool:
        return app_name not in self.closed

    async def close(self, app_name: str) -> None:
        self.closed.add(app_name)
        self.session_tokens.pop(app_name, None)


def _store(max_sessions: int = 1000) -> JudgeSessionStore:
    service_config = BaseServiceConfig(
        host="127.0.0.1", port=8420, advertise_host="127.0.0.1",
        token_id=TOKEN_ID, token_secret=TOKEN_SECRET,
    )
    store = JudgeSessionStore(
        _FakeExecutor(), JudgeSessionsConfig(max_sessions=max_sessions), service_config
    )
    store.attach_tunnels(_FakeTunnels())
    return store


def test_list_sessions_created_desc_with_destroyed_tail() -> None:
    async def main() -> None:
        store = _store()
        sessions = []
        for i in range(3):
            session = await store.create(f"reg/family{i}-judge:1", None, None, None)
            session.created = 1000.0 + i  # deterministic ordering
            sessions.append(session)
        store._tunnels.session_tokens[sessions[0].app_name] = "secret"
        await store.destroy(sessions[0].session_id)
        assert not store._tunnels.is_connected(sessions[0].app_name)
        assert sessions[0].app_name not in store._tunnels.session_tokens
        assert await store.destroy(sessions[0].session_id) is False

        listed = store.list_sessions()
        assert [s.session_id for s in listed] == [
            sessions[2].session_id,
            sessions[1].session_id,
            sessions[0].session_id,
        ]
        assert [s.destroyed for s in listed] == [False, False, True]
        # live_sessions() is unaffected by the destroyed tail.
        assert {s.session_id for s in store.live_sessions()} == {
            sessions[1].session_id,
            sessions[2].session_id,
        }

    asyncio.run(main())


def test_destroyed_retention_capped() -> None:
    async def main() -> None:
        store = _store()
        for _ in range(DESTROYED_SESSIONS_KEEP + 10):
            session = await store.create("reg/family-judge:1", None, None, None)
            await store.destroy(session.session_id)
        listed = store.list_sessions()
        assert len(listed) == DESTROYED_SESSIONS_KEEP
        assert all(s.destroyed for s in listed)

    asyncio.run(main())


def test_list_cap_covers_live_and_destroyed_together() -> None:
    async def main() -> None:
        store = _store()
        # 150 destroyed (only the newest DESTROYED_SESSIONS_KEEP=100 survive
        # retention) plus 150 live: 250 rows in memory, the list caps at 200.
        for i in range(150):
            old = await store.create("reg/family-judge:1", None, None, None)
            old.created = 1000.0 + i
            await store.destroy(old.session_id)
        live = [
            await store.create("reg/family-judge:1", None, None, None)
            for _ in range(150)
        ]
        for i, session in enumerate(live):
            session.created = 2000.0 + i  # the live ones are the newest

        listed = store.list_sessions()
        assert len(listed) == SESSION_LIST_LIMIT
        # created desc: the 150 live sessions lead, the newest destroyed follow.
        assert [s.destroyed for s in listed[:150]] == [False] * 150
        assert all(s.destroyed for s in listed[150:])
        # The destroyed rows that survived the 200 cap are the newest ones.
        assert min(s.created for s in listed[150:]) == 1100.0

    asyncio.run(main())


# --------------------------------------------------------------------------- #
# HTTP level over the live service (jservice fixture, sharded store rows)
# --------------------------------------------------------------------------- #
def _request(url: str, *, method: str = "GET", body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Content-Type": "application/json",
        "X-TCSEXAM-Token-Id": TOKEN_ID,
        "X-TCSEXAM-Token-Secret": TOKEN_SECRET,
    }
    if url.split("?", 1)[0].endswith("/v1/judge/sessions") and (
        method == "GET"
        or (isinstance(body, dict) and body.get("instance_set", "hidden") == "hidden")
    ):
        headers["X-TCSEXAM-Archive-Token"] = ARCHIVE_TOKEN
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_session_list_endpoint_http(jservice) -> None:
    url = jservice.url
    jservice.factory.delay_seconds = 2.0  # the rows stay "provisioning" deterministically
    # Empty at first.
    status, rows = _request(f"{url}/v1/judge/sessions")
    assert status == 200 and rows == []

    status, created1 = _request(
        f"{url}/v1/judge/sessions",
        method="POST",
        body={"judge_image": "registry.example.com/public/bench-knn-judge:v3"},
    )
    assert status == 202, created1
    assert created1["status"] == "provisioning"
    status, created2 = _request(
        f"{url}/v1/judge/sessions",
        method="POST",
        body={"judge_image": "registry.example.com/public/bench-lwe-judge:v1"},
    )
    assert status == 202, created2

    status, rows = _request(f"{url}/v1/judge/sessions")
    assert status == 200
    assert len(rows) == 2
    # created desc: the second create leads.
    assert rows[0]["session_id"] == created2["session_id"]
    # Schema + family normalization (image_family: tag and -judge stripped).
    # status/error are the async-creation fields; instance_set/n_shards are
    # the sharded store's columns.
    row = rows[0]
    assert set(row) == {
        "session_id", "image", "family", "instance_set", "n_shards",
        "created", "last_active", "destroyed", "run_id", "agent_name",
        "attrs", "status", "error",
    }
    assert row["family"] == "bench-lwe"
    assert row["instance_set"] == "hidden"
    assert row["n_shards"] == 1
    assert row["destroyed"] is False
    assert row["status"] == "provisioning"
    assert row["error"] == ""
    assert rows[1]["family"] == "bench-knn"

    # DELETE keeps the row with destroyed=true.
    status, _ = _request(
        f"{url}/v1/judge/sessions/{created1['session_id']}", method="DELETE"
    )
    assert status == 200
    status, rows = _request(f"{url}/v1/judge/sessions")
    assert status == 200
    by_id = {r["session_id"]: r for r in rows}
    assert by_id[created1["session_id"]]["destroyed"] is True
    assert by_id[created2["session_id"]]["destroyed"] is False

    # The endpoint is behind the same service auth.
    req = urllib.request.Request(f"{url}/v1/judge/sessions", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    assert status == 401
