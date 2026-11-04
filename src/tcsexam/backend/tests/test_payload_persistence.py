"""Submission-content persistence tests (no workers).

Covers:
- _persist_creation_payload: on-disk layout / over-cap skip / traversal
  rejection
- _persist_submission_body: increasing seq, the directory as the counter
  (restart-safe)
- config parsing: payload_persist_max_bytes YAML key
- endpoints (TestServer real routing): GET {sid}/payload,
  /payload/submissions, /payload/submissions/{seq} — the 404 family (same
  discipline as the archive endpoint: wrong/missing/unconfigured token and
  unknown sid all collapse into the same 404) and the byte-level round trip
- relay integration: an accepted submit is persisted and the forwarded body
  is not consumed by the read (aiohttp request.read() caching)
"""
from __future__ import annotations

import asyncio
import io
import json
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

import tcsexam.backend.sessions as js
from tcsexam.backend.config import load_config
from tcsexam.backend.sessions import (
    _persist_creation_payload,
    _persist_submission_body,
    register_routes,
)

H = {"X-TCSEXAM-Archive-Token": "tok"}


def _store(token="tok", state_dir=None, live_sids=(), cap_bytes=67108864):
    sessions = {
        sid: SimpleNamespace(
            session_id=sid,
            last_active=123.0,
            status="ready",
            instance_set="hidden",
            n_shards=1,
            shards=[SimpleNamespace(app_name=f"app-{sid}")],
        )
        for sid in live_sids
    }
    store = SimpleNamespace(
        _config=SimpleNamespace(archive_token=token, state_dir=state_dir),
        cfg=SimpleNamespace(payload_persist_max_bytes=cap_bytes),
        get=sessions.get,
        _journal=None,
    )
    return store


def test_config_payload_persist_max_bytes(tmp_path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        "host: 127.0.0.1\nport: 0\npublic_base_url: http://test\n"
        "auth: {token_id: t, token_secret: s}\nadapter: local-test\nstate_dir: /tmp/t\n"
        "backend:\n  judge_sessions:\n    payload_persist_max_bytes: 1024\n"
    )
    cfg = load_config(p)
    assert cfg.backend.judge_sessions.payload_persist_max_bytes == 1024
    p.write_text(
        "host: 127.0.0.1\nport: 0\npublic_base_url: http://test\n"
        "auth: {token_id: t, token_secret: s}\nadapter: local-test\nstate_dir: /tmp/t\n"
    )
    cfg = load_config(p)
    assert cfg.backend.judge_sessions.payload_persist_max_bytes == 67108864


def test_persist_creation_payload(tmp_path) -> None:
    store = _store(state_dir=str(tmp_path))
    _persist_creation_payload(store, "jsess-c", {"/a/b.txt": b"hello", "/c.bin": b"\x00\x01"})
    got = (tmp_path / "judge_payload" / "jsess-c" / "a" / "b.txt").read_bytes()
    assert got == b"hello", "worker-absolute paths expand relative under the sid dir"
    _persist_creation_payload(store, "jsess-big", {"/x": b"0" * (67108864 + 1)})
    assert not (tmp_path / "judge_payload" / "jsess-big").exists(), "over the cap: skipped"
    _persist_creation_payload(store, "jsess-evil", {"/../../evil.txt": b"x"})
    assert not (tmp_path / "evil.txt").exists()
    assert not (tmp_path / "judge_payload" / "evil.txt").exists(), "traversal rejected"
    _persist_creation_payload(store, "jsess-none", None)
    assert not (tmp_path / "judge_payload" / "jsess-none").exists(), "empty payload: no-op"


def test_persist_submission_body_seq_and_restart_counter(tmp_path) -> None:
    store = _store(state_dir=str(tmp_path))
    _persist_submission_body(store, "jsess-s", b"first")
    _persist_submission_body(store, "jsess-s", b"second")
    root = tmp_path / "judge_submissions" / "jsess-s"
    assert (root / "001.tar.gz").read_bytes() == b"first"
    assert (root / "002.tar.gz").read_bytes() == b"second"
    # A later write (e.g. after a service restart) continues the numbering:
    # the directory itself is the counter.
    _persist_submission_body(store, "jsess-s", b"third")
    assert (root / "003.tar.gz").read_bytes() == b"third"


async def _client(store):
    app = web.Application()
    app["judge_sessions"] = store
    register_routes(app)
    client = TestClient(TestServer(app))
    await client.start_server()
    return client


def test_payload_endpoints_round_trip(tmp_path) -> None:
    async def main() -> None:
        _persist_creation_payload(_store(state_dir=str(tmp_path)), "jsess-a", {"/solver/main.py": b"print(1)"})
        store = _store(state_dir=str(tmp_path))
        _persist_submission_body(store, "jsess-a", b"body-one")
        _persist_submission_body(store, "jsess-a", b"body-two")

        store = _store(token="tok", state_dir=str(tmp_path), live_sids=("jsess-a",))
        client = await _client(store)
        try:
            async with client.get("/v1/judge/sessions/jsess-a/payload", headers=H) as r:
                body = await r.read()
                assert r.status == 200
                assert r.headers.get("Content-Type") == "application/gzip"
                with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as tf:
                    assert tf.extractfile("solver/main.py").read() == b"print(1)"

            async with client.get("/v1/judge/sessions/jsess-a/payload/submissions", headers=H) as r:
                d = json.loads(await r.text())
                assert r.status == 200 and d["submissions"] == [1, 2]
            async with client.get("/v1/judge/sessions/jsess-a/payload/submissions/2", headers=H) as r:
                assert r.status == 200 and await r.read() == b"body-two"
            async with client.get("/v1/judge/sessions/jsess-a/payload/submissions/9", headers=H) as r:
                assert r.status == 404
            async with client.get("/v1/judge/sessions/jsess-a/payload/submissions/junk", headers=H) as r:
                assert r.status == 404
        finally:
            await client.close()

    asyncio.run(main())


def test_payload_endpoints_404_family(tmp_path) -> None:
    async def main() -> None:
        _persist_creation_payload(_store(state_dir=str(tmp_path)), "jsess-a", {"/solver/main.py": b"print(1)"})
        store = _store(state_dir=str(tmp_path))
        _persist_submission_body(store, "jsess-a", b"body-one")
        store = _store(token="tok", state_dir=str(tmp_path), live_sids=("jsess-a",))
        client = await _client(store)
        try:
            # Same URL: missing/wrong token and "session does not exist" are
            # byte-identical — the persistence layer's existence never leaks.
            async with client.get("/v1/judge/sessions/jsess-a/payload") as r:
                no_tok = (r.status, await r.read())
            async with client.get("/v1/judge/sessions/jsess-a/payload", headers={"X-TCSEXAM-Archive-Token": "bad"}) as r:
                bad_tok = (r.status, await r.read())
            assert no_tok == bad_tok and no_tok[0] == 404
            async with client.get("/v1/judge/sessions/jsess-noexist/payload", headers={"X-TCSEXAM-Archive-Token": "bad"}) as r:
                wrong_body = (r.status, await r.read())
            async with client.get("/v1/judge/sessions/jsess-noexist/payload", headers=H) as r:
                unknown_body = (r.status, await r.read())
            assert wrong_body == unknown_body
            async with client.get("/v1/judge/sessions/jsess-noexist/payload/submissions", headers=H) as r:
                unk2 = (r.status, await r.read())
            assert unk2 == unknown_body
            async with client.get("/v1/judge/sessions/jsess-noexist/payload/submissions/1", headers=H) as r:
                unk3 = (r.status, await r.read())
            assert unk3 == unknown_body
        finally:
            await client.close()
        # Empty token config: the endpoints are disabled entirely.
        client2 = await _client(_store(token="", state_dir=str(tmp_path), live_sids=("jsess-a",)))
        try:
            async with client2.get("/v1/judge/sessions/jsess-a/payload", headers=H) as r:
                assert r.status == 404
        finally:
            await client2.close()
        # A live session without payload dirs: 404 with a readable diagnosis.
        client3 = await _client(_store(token="tok", state_dir=str(tmp_path), live_sids=("jsess-b",)))
        try:
            async with client3.get("/v1/judge/sessions/jsess-b/payload", headers=H) as r:
                assert r.status == 404 and b"no creation payload" in await r.read()
            async with client3.get("/v1/judge/sessions/jsess-b/payload/submissions", headers=H) as r:
                assert r.status == 404 and b"no submission payload" in await r.read()
        finally:
            await client3.close()

    asyncio.run(main())


def test_relay_persists_accepted_body_without_consuming_it(tmp_path, monkeypatch) -> None:
    async def main() -> None:
        forwarded = {}

        async def fake_call_shards(store, session, method, path, *, body=b"", timeout=30):
            forwarded["body"] = body
            return {0: (202, {}, json.dumps({"submission": 1}).encode())}

        monkeypatch.setattr(js, "_call_shards", fake_call_shards)
        live = SimpleNamespace(
            session_id="jsess-r", last_active=0.0, status="ready",
            instance_set="hidden", n_shards=1, failed_shards={},
            submit_era_base=0, delivered=False,
            shards=[SimpleNamespace(app_name="app-jsess-r")],
        )
        store4 = _store(token="tok", state_dir=str(tmp_path), live_sids=("jsess-r",))
        store4.cfg = SimpleNamespace(
            payload_persist_max_bytes=67108864,
            submit_fanout_timeout_seconds=600.0,
            submission_cap=SimpleNamespace(enabled=False),
        )
        store4.get = lambda sid: live if sid == "jsess-r" else None
        client4 = await _client(store4)
        try:
            async with client4.post(
                "/v1/judge/sessions/jsess-r/submit",
                data=b"submit-body-bytes",
                headers={"X-TCSEXAM-Token-Id": "t", "X-TCSEXAM-Token-Secret": "s"},
            ) as r:
                assert r.status == 202
        finally:
            await client4.close()
        root = tmp_path / "judge_submissions" / "jsess-r"
        assert (root / "001.tar.gz").read_bytes() == b"submit-body-bytes"
        assert forwarded.get("body") == b"submit-body-bytes", "the fan-out body was not consumed"

    asyncio.run(main())
