"""Raw-record archive endpoint tests (no workers; aiohttp TestServer with
real routing).

Covers the verifier-only GET /v1/judge/sessions/{sid}/archive paths:
- right token + existing sid + archive present -> 200 verbatim
  (application/json; also proves the route registers before the wildcard
  relay — a fake store without _tunnels would 500 through the relay)
- wrong/missing token -> 404, byte-identical to the "unknown sid" response
  (the endpoint's existence is never exposed)
- empty archive_token config -> the endpoint is disabled, 404 with or
  without the header
- right token + unknown sid -> 404
- right token + existing sid + no archive file -> 404 with a readable error
Plus: load_config's archive_token key parsing + the TCSEXAM_ARCHIVE_TOKEN
env override.
"""
from __future__ import annotations

import json
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from tcsexam.backend.config import load_config
from tcsexam.backend.sessions import register_routes

ARCHIVE = {
    "session_id": "jsess-a",
    "n_shards": 2,
    "instance_set": "hidden",
    "failed_shards": {},
    "shard_payloads": {"0": {"submissions": [{"submission": 0, "records": [{"instance": "i1", "A": 5, "B": 3, "K": 10}]}]}},
}

H = {"X-TCSEXAM-Archive-Token": "tok"}


def _store(token, state_dir, live_sids):
    sessions = {sid: SimpleNamespace(session_id=sid, last_active=123.0) for sid in live_sids}
    store = SimpleNamespace(
        _config=SimpleNamespace(archive_token=token, state_dir=state_dir),
        get=sessions.get,
    )
    store._sessions = sessions  # test assertions (last_active untouched)
    return store


async def _client(store):
    app = web.Application()
    app["judge_sessions"] = store
    register_routes(app)
    client = TestClient(TestServer(app))
    await client.start_server()
    return client


def test_config_archive_token_yaml_and_env(tmp_path, monkeypatch) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("archive_token: yaml-tok\n")
    assert load_config(cfg_path).archive_token == "yaml-tok"
    cfg_path.write_text("host: 127.0.0.1\n")
    assert load_config(cfg_path).archive_token == ""  # missing key: disabled
    monkeypatch.setenv("TCSEXAM_ARCHIVE_TOKEN", "env-tok")
    cfg_path.write_text("archive_token: yaml-tok\n")
    assert load_config(cfg_path).archive_token == "env-tok"


@pytest.fixture
def archive_dir(tmp_path):
    base = tmp_path / "judge_archive"
    base.mkdir()
    (base / "jsess-a.json").write_text(json.dumps(ARCHIVE))
    return tmp_path


def test_happy_path_200_verbatim(archive_dir) -> None:
    async def main() -> None:
        store = _store("tok", str(archive_dir), ("jsess-a", "jsess-b"))
        client = await _client(store)
        try:
            resp = await client.get("/v1/judge/sessions/jsess-a/archive", headers=H)
            raw = await resp.read()
            assert resp.status == 200
            assert resp.content_type == "application/json"
            assert raw == (archive_dir / "judge_archive" / "jsess-a.json").read_bytes()
            # The archive keeps the raw records (B/K anchors intact).
            assert json.loads(raw)["shard_payloads"]["0"]["submissions"][0]["records"][0]["K"] == 10
            # Purely read-only: last_active untouched.
            assert store._sessions["jsess-a"].last_active == 123.0
        finally:
            await client.close()

    import asyncio
    asyncio.run(main())


def test_wrong_or_missing_token_is_uniform_404(archive_dir) -> None:
    async def main() -> None:
        store = _store("tok", str(archive_dir), ("jsess-a", "jsess-b"))
        client = await _client(store)
        try:
            resp = await client.get(
                "/v1/judge/sessions/jsess-a/archive", headers={"X-TCSEXAM-Archive-Token": "WRONG"}
            )
            assert resp.status == 404
            resp = await client.get("/v1/judge/sessions/jsess-a/archive")
            assert resp.status == 404
            # The wrong-credential response is byte-identical to the
            # unknown-session response: the endpoint's existence never leaks.
            resp = await client.get(
                "/v1/judge/sessions/jsess-noexist/archive", headers={"X-TCSEXAM-Archive-Token": "WRONG"}
            )
            wrong_body = await resp.read()
            assert resp.status == 404
            resp = await client.get("/v1/judge/sessions/jsess-noexist/archive", headers=H)
            unknown_body = await resp.read()
            assert wrong_body == unknown_body
            assert resp.status == 404
            assert b"unknown judge session jsess-noexist" in unknown_body
        finally:
            await client.close()

    import asyncio
    asyncio.run(main())


def test_existing_session_without_archive_file_is_404(archive_dir) -> None:
    async def main() -> None:
        store = _store("tok", str(archive_dir), ("jsess-a", "jsess-b"))
        client = await _client(store)
        try:
            resp = await client.get("/v1/judge/sessions/jsess-b/archive", headers=H)
            body = json.loads(await resp.read())
            assert resp.status == 404
            assert "no archive yet" in body.get("error", "")
        finally:
            await client.close()

    import asyncio
    asyncio.run(main())


def test_unconfigured_token_disables_the_endpoint(archive_dir) -> None:
    async def main() -> None:
        client = await _client(_store("", str(archive_dir), ("jsess-a",)))
        try:
            resp = await client.get("/v1/judge/sessions/jsess-a/archive", headers=H)
            assert resp.status == 404
            resp = await client.get("/v1/judge/sessions/jsess-a/archive")
            assert resp.status == 404
        finally:
            await client.close()

    import asyncio
    asyncio.run(main())
