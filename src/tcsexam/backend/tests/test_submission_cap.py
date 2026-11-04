"""Submission cap + reconciliation query tests.

Covers: identity resolution (XFF first ?? remote), SubmissionCapConfig
parsing, the session journal (append + replay + counters), relay-level cap
enforcement (429 exact body, family override, exempt identities, disabled
mode), the client_ip/self reconciliation query, and the /v1/status section.
The HTTP tests run the full service (recording fake adapter, real tunnel,
toy judge upstream answering POST /submit with 200).
"""
from __future__ import annotations

import asyncio
import json
import threading
import types
import urllib.error
import urllib.request

import aiohttp
import aiohttp.web
import pytest

from conftest import (
    ARCHIVE_TOKEN,
    TOKEN_ID,
    TOKEN_SECRET,
    FactoryAdapter,
    FakeFactory,
    _Harness,
    wait_session_ready,
)

from tcsexam.backend.auth import resolve_identity
from tcsexam.backend.config import (
    BackendConfig,
    Config,
    JudgeSessionsConfig,
    SubmissionCapConfig,
    judge_sessions_from_dict,
)
from tcsexam.backend.journal import SessionJournal
from tcsexam.backend.server import create_app


# --------------------------------------------------------------------------- #
# Identity resolution
# --------------------------------------------------------------------------- #
def _req(headers: dict, remote: str = "9.9.9.9"):
    return types.SimpleNamespace(headers=headers, remote=remote)


def test_identity_xff_first_value() -> None:
    assert resolve_identity(_req({"X-Forwarded-For": "192.0.2.1"})) == "192.0.2.1"


def test_identity_xff_comma_chain_takes_first() -> None:
    assert resolve_identity(_req({"X-Forwarded-For": "192.0.2.1, 1.2.3.4"})) == "192.0.2.1"


def test_identity_falls_back_to_remote() -> None:
    assert resolve_identity(_req({})) == "9.9.9.9"
    assert resolve_identity(_req({"X-Forwarded-For": "  "})) == "9.9.9.9"


# --------------------------------------------------------------------------- #
# Config parsing
# --------------------------------------------------------------------------- #
def test_submission_cap_config_defaults() -> None:
    cfg = judge_sessions_from_dict({}).submission_cap
    assert cfg.enabled is False, "opt-in per deployment"
    assert cfg.default == 10
    assert cfg.effective_at == 0.0
    assert cfg.overrides == {}
    assert cfg.exempt_identities == []


def test_submission_cap_config_full_parse() -> None:
    cfg = judge_sessions_from_dict(
        {
            "submission_cap": {
                "enabled": True,
                "default": 5,
                "effective_at": 1757500000,
                "overrides": {"family-a": 20},
                "exempt_identities": ["10.1.1.1"],
            }
        }
    ).submission_cap
    assert cfg == SubmissionCapConfig(
        enabled=True,
        default=5,
        effective_at=1757500000.0,
        overrides={"family-a": 20},
        exempt_identities=["10.1.1.1"],
    )


# --------------------------------------------------------------------------- #
# Journal: append + replay + queries
# --------------------------------------------------------------------------- #
def test_journal_append_replay_and_queries(tmp_path) -> None:
    path = tmp_path / "j.jsonl"
    journal = SessionJournal(path)
    journal.record_register("jsess-a", "reg/family-judge:1.0.0", "family", "192.0.2.1", created=100.0)
    journal.record_submit_accept("jsess-a", "192.0.2.1")
    journal.record_submit_accept("jsess-a", "192.0.2.1")
    journal.record_submit_accept("jsess-a", "192.0.2.2")
    journal.record_score("jsess-a", 0.5, "sub-1")
    journal.record_score("jsess-a", 0.9, "sub-2")
    journal.record_destroyed("jsess-a")

    fresh = SessionJournal(path)  # replay from disk
    s = fresh.sessions["jsess-a"]
    assert s.family == "family" and s.destroyed is True
    assert len(s.submissions) == 3
    assert s.best_score == 0.9 and s.best_submission_id == "sub-2"
    assert fresh.submission_count("192.0.2.1") == 2
    assert fresh.submission_count("192.0.2.1", since=10**18) == 0  # future cutoff
    assert fresh.submission_count("192.0.2.1", exclude={"192.0.2.1"}) == 0
    assert [x.session_id for x in fresh.sessions_by_identity("192.0.2.1")] == ["jsess-a"]
    assert fresh.sessions_by_identity("10.9.9.9") == []


# --------------------------------------------------------------------------- #
# HTTP: full-service cap enforcement + reconciliation query
# --------------------------------------------------------------------------- #
def _request(url, body=None, *, method="POST", headers=None):
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"X-TCSEXAM-Token-Id": TOKEN_ID, "X-TCSEXAM-Token-Secret": TOKEN_SECRET}
    if url.split("?", 1)[0].endswith("/v1/judge/sessions") and (
        method == "GET"
        or (isinstance(body, dict) and body.get("instance_set", "hidden") == "hidden")
    ):
        hdrs["X-TCSEXAM-Archive-Token"] = ARCHIVE_TOKEN
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _capped_service(tmp_path, cap_config, seed_events=()):
    """Start the capped service in a thread (same loop pattern as conftest.jservice).

    seed_events: journal event dicts written to the journal file BEFORE the
    service starts — pre-seeded history for the grandfather-clause tests
    (identities whose footprint predates effective_at).
    """
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    if seed_events:
        with open(tmp_path / "judge_session_journal.jsonl", "w") as fh:
            for event in seed_events:
                fh.write(json.dumps(event) + "\n")
    config = Config(
        host="127.0.0.1",
        port=port,
        advertise_host="127.0.0.1",
        token_id=TOKEN_ID,
        token_secret=TOKEN_SECRET,
        archive_token=ARCHIVE_TOKEN,
        state_dir=tmp_path,
        backend=BackendConfig(
            ready_timeout_seconds=30.0,
            judge_sessions=JudgeSessionsConfig(
                max_sessions=8,
                ready_timeout_seconds=30,
                shard_boot_retries=0,
                hibernate_enabled=False,
                spec={"cpu_count": 4, "memory_mb": 8192, "storage_mb": 20480},
                submission_cap=cap_config,
            ),
        ),
    )
    harness = _Harness()
    factory = FakeFactory(harness)
    adapter = FactoryAdapter(factory)

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    async def _start():
        toy = aiohttp.web.Application()

        async def health(request):
            return aiohttp.web.json_response({"status": "ok", "ready": True})

        async def submit(request):
            return aiohttp.web.json_response({"submission_uuid": "toy-uuid", "status": "queued"})

        toy.router.add_get("/health", health)
        toy.router.add_post("/submit", submit)
        toy_runner = aiohttp.web.AppRunner(toy)
        await toy_runner.setup()
        toy_site = aiohttp.web.TCPSite(toy_runner, "127.0.0.1", 0)
        await toy_site.start()
        harness.toy_port = toy_site._server.sockets[0].getsockname()[1]

        app = create_app(config, adapter=adapter)
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, config.host, config.port)
        await site.start()
        return [runner, toy_runner]

    runners = asyncio.run_coroutine_threadsafe(_start(), loop).result(timeout=30)

    yield types.SimpleNamespace(url=f"http://127.0.0.1:{port}", harness=harness)
    harness.close_agents()  # open tunnels would stall the aiohttp shutdown

    async def _stop() -> None:
        for runner in runners:
            await runner.cleanup()

    asyncio.run_coroutine_threadsafe(_stop(), loop).result(timeout=30)
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=10)


@pytest.fixture
def capped(tmp_path):
    yield from _capped_service(
        tmp_path,
        SubmissionCapConfig(
            enabled=True, default=2, overrides={"family": 4},
            exempt_identities=["192.0.2.2"],
            exempt_identities_file=str(tmp_path / "exempt.txt"),
        ),
    )


# Grandfather clause: footprints at T0 predate the cap's
# effective_at (T1); identities first seen at/after T1 are capped.
GRANDFATHER_T0 = 1_000_000.0
GRANDFATHER_T1 = 2_000_000.0


@pytest.fixture
def capped_grandfather(tmp_path):
    seed = [
        # 192.0.2.8: register + an accepted submission before effective_at.
        {"t": GRANDFATHER_T0, "type": "register", "sid": "jsess-old8",
         "image": "reg/other-judge:1", "family": "other", "identity": "192.0.2.8"},
        {"t": GRANDFATHER_T0, "type": "submit_accept", "sid": "jsess-old8",
         "identity": "192.0.2.8"},
        # 192.0.2.9: register only (created its session pre-cap, never
        # submitted yet — the in-flight-without-submissions case).
        {"t": GRANDFATHER_T0, "type": "register", "sid": "jsess-old9",
         "image": "reg/other-judge:1", "family": "other", "identity": "192.0.2.9"},
        # jsess-pub: a public-channel accept in the ledger (history
        # attribution; never cap-counted).
        {"t": GRANDFATHER_T0, "type": "register", "sid": "jsess-pub",
         "image": "reg/other-judge:1", "family": "other", "identity": "192.0.2.1"},
        {"t": GRANDFATHER_T0, "type": "submit_accept_public", "sid": "jsess-pub",
         "identity": "192.0.2.1"},
    ]
    yield from _capped_service(
        tmp_path,
        SubmissionCapConfig(enabled=True, default=2, effective_at=GRANDFATHER_T1),
        seed,
    )


def _create(capped, image="registry.example.com/family-judge:1.0.0", xff="192.0.2.1") -> str:
    status, body = _request(
        f"{capped.url}/v1/judge/sessions",
        {"judge_image": image},
        headers={"X-Forwarded-For": xff},
    )
    assert status == 202, body
    sid = body["session_id"]
    # poll until ready
    import time as _time

    for _ in range(300):
        _, st = _request(f"{capped.url}/v1/judge/sessions/{sid}", None, method="GET")
        if st["status"] == "ready":
            return sid
        _time.sleep(0.1)
    raise AssertionError(f"session {sid} did not become ready: {st}")


def _submit(capped, sid, xff="192.0.2.1"):
    return _request(
        f"{capped.url}/v1/judge/sessions/{sid}/submit",
        {"code": "pass"},
        headers={"X-Forwarded-For": xff},
    )


def test_cap_rejects_at_limit_with_contract_body(capped) -> None:
    sid = _create(capped)
    # family override applies: image family is "family" -> cap 4, not default 2.
    for _ in range(4):
        status, _ = _submit(capped, sid)
        assert status == 200
    status, body = _submit(capped, sid)
    assert status == 429
    assert body == {
        "error": "submission_cap_exceeded",
        "cap": 4,
        "used": 4,
        "identity": "192.0.2.1",
        "message": "submission cap reached for this judging session: 4/4 used",
    }


def test_default_cap_applies_without_family_override(capped) -> None:
    sid = _create(capped, image="registry.example.com/other-judge:1.0.0")
    for _ in range(2):
        assert _submit(capped, sid)[0] == 200
    assert _submit(capped, sid)[0] == 429  # default cap 2 (no "other" override)


def test_exemption_is_retired_session_keyed(capped) -> None:
    # The cap is keyed by SESSION, so the static exempt-identities
    # list no longer lifts anyone — the exempt identity caps at the session
    # limit like every other session (still journaled for reconciliation).
    sid = _create(capped, xff="192.0.2.2")
    for _ in range(4):
        assert _submit(capped, sid, xff="192.0.2.2")[0] == 200
    status, _ = _submit(capped, sid, xff="192.0.2.2")
    assert status == 429  # family cap 4, identity exemption retired
    _, body = _request(f"{capped.url}/v1/judge/sessions?client_ip=192.0.2.2", None, method="GET")
    assert body["total_submissions"] == 4  # journaled regardless


def test_reconciliation_query_self_and_identity(capped) -> None:
    sid = _create(capped)
    for _ in range(3):
        assert _submit(capped, sid)[0] == 200
    status, body = _request(
        f"{capped.url}/v1/judge/sessions?client_ip=self",
        None,
        method="GET",
        headers={"X-Forwarded-For": "192.0.2.1"},
    )
    assert status == 200
    assert body["identity"] == "192.0.2.1"
    assert body["total_submissions"] == 3
    assert len(body["sessions"]) == 1
    row = body["sessions"][0]
    assert row["session_id"] == sid
    assert row["submissions"] == 3
    assert row["destroyed"] is False
    assert row["best"] is None  # score capture not wired (documented)


def test_journal_survives_service_restart(capped, tmp_path) -> None:
    sid = _create(capped)
    assert _submit(capped, sid)[0] == 200
    journal = SessionJournal(f"{tmp_path}/judge_session_journal.jsonl")
    assert journal.submission_count("192.0.2.1") == 1
    s = journal.sessions[sid]
    assert s.status == "ready"
    assert s.creator_identity == "192.0.2.1"


def test_status_exposes_submission_cap_section(capped) -> None:
    _, body = _request(f"{capped.url}/v1/status", None, method="GET")
    section = body["submission_cap"]
    assert section["enabled"] is True
    assert section["default"] == 2
    assert section["overrides"] == {"family": 4}
    assert section["exempt_identities"] == ["192.0.2.2"]
    assert section["journaled_sessions"] >= 0


# --------------------------------------------------------------------------- #
# Grandfather clause: in-flight runs keep the old unlimited rules
# --------------------------------------------------------------------------- #
def test_journal_first_seen_unit(tmp_path) -> None:
    path = tmp_path / "j.jsonl"
    journal = SessionJournal(path)
    journal.record_register("jsess-a", "reg/family-judge:1.0.0", "family", "192.0.2.9", created=100.0)
    journal.record_submit_accept("jsess-a", "192.0.2.8")
    assert journal.first_seen("192.0.2.9") == 100.0  # register alone counts
    assert journal.first_seen("192.0.2.8") is not None  # submit counts
    assert journal.first_seen("192.0.2.7") is None  # no footprint
    fresh = SessionJournal(path)  # survives replay
    assert fresh.first_seen("192.0.2.9") == 100.0


def test_session_cap_counts_only_since_effective_at(tmp_path) -> None:
    # Transition semantics: submissions before effective_at stay in
    # the ledger but never count toward the per-session cap — sessions from
    # the unlimited era start the cap fresh at the flip.
    journal = SessionJournal(tmp_path / "j.jsonl")
    journal._append({"t": GRANDFATHER_T0, "type": "register", "sid": "jsess-old",
                     "image": "reg/family-judge:1.0.0", "family": "family", "identity": "192.0.2.1"})
    journal._append({"t": GRANDFATHER_T0, "type": "submit_accept", "sid": "jsess-old", "identity": "192.0.2.1"})
    assert journal.session_submission_count("jsess-old") == 1  # ledger keeps it
    assert journal.session_submission_count("jsess-old", since=GRANDFATHER_T1) == 0  # cap ignores it
    # Replay preserves both views.
    fresh = SessionJournal(tmp_path / "j.jsonl")
    assert fresh.session_submission_count("jsess-old") == 1
    assert fresh.session_submission_count("jsess-old", since=GRANDFATHER_T1) == 0


def test_public_accepts_tracked_but_never_cap_counted(tmp_path) -> None:
    # Public channel: journaled per session for run-level history
    # attribution, never into the cap counter (hidden-only), replay-stable.
    journal = SessionJournal(tmp_path / "j.jsonl")
    journal.record_register("jsess-p", "reg/family-judge:1.0.0", "family", "192.0.2.1", created=100.0)
    journal._append({"t": 101.0, "type": "submit_accept_public", "sid": "jsess-p", "identity": "192.0.2.1"})
    journal._append({"t": 102.0, "type": "submit_accept_public", "sid": "jsess-p", "identity": "192.0.2.1"})
    s = journal.sessions["jsess-p"]
    assert len(s.public_submissions) == 2
    assert journal.session_submission_count("jsess-p") == 0
    fresh = SessionJournal(tmp_path / "j.jsonl")
    assert len(fresh.sessions["jsess-p"].public_submissions) == 2
    assert fresh.session_submission_count("jsess-p") == 0


def test_identity_first_seen_after_effective_at_is_capped(capped_grandfather) -> None:
    # A fresh session (new run, new chain link): capped per-session from its
    # very first submission — identity and footprints play no role.
    sid = _create(capped_grandfather, xff="192.0.2.1")
    assert _submit(capped_grandfather, sid)[0] == 200
    assert _submit(capped_grandfather, sid)[0] == 200
    status, body = _submit(capped_grandfather, sid)
    assert status == 429
    assert body["error"] == "submission_cap_exceeded"
    assert body["cap"] == 2 and body["used"] == 2


def test_session_ids_query_returns_chain_counts(capped_grandfather) -> None:
    # The verifier's chain reconciliation: ?session_ids=a,b,c
    # returns per-session hidden counts + the chain total; public accepts
    # ride along separately; unknown sids report present=false.
    sid_a = _create(capped_grandfather, xff="192.0.2.1")
    sid_b = _create(capped_grandfather, image="registry.example.com/other-judge:1.0.0", xff="192.0.2.1")
    _submit(capped_grandfather, sid_a)
    _submit(capped_grandfather, sid_b)
    _submit(capped_grandfather, sid_b)
    _, body = _request(
        f"{capped_grandfather.url}/v1/judge/sessions?session_ids={sid_a},{sid_b},jsess-pub,jsess-nope",
        None,
        method="GET",
    )
    rows = {r["session_id"]: r for r in body["sessions"]}
    assert rows[sid_a]["submissions"] == 1
    assert rows[sid_b]["submissions"] == 2
    assert rows["jsess-pub"]["submissions"] == 0
    assert rows["jsess-pub"]["public_submissions"] == 1
    assert rows["jsess-pub"]["present"] is True
    assert rows["jsess-nope"]["submissions"] == 0
    assert rows["jsess-nope"]["present"] is False
    assert body["total_submissions"] == 3  # hidden only, never public


# --------------------------------------------------------------------------- #
# Hot-reload exemption file: debug-IP exemptions without a restart
# --------------------------------------------------------------------------- #
def test_read_exempt_identities_file(tmp_path) -> None:
    from tcsexam.backend.config import read_exempt_identities_file

    p = tmp_path / "exempt.txt"
    p.write_text("# comment\n192.0.2.1\n\n  192.0.2.2  \n192.0.2.3 # inline\n")
    assert read_exempt_identities_file(str(p)) == ["192.0.2.1", "192.0.2.2", "192.0.2.3"]
    assert read_exempt_identities_file(str(tmp_path / "missing.txt")) == []


def test_hot_reload_exemption_file_is_inert_session_keyed(capped, tmp_path) -> None:
    # The hot-reload exemption file (an identity-keyed mechanism)
    # no longer lifts the cap — per-session counting ignores identity
    # entirely. The file stays for status display; the 429 never consults it.
    exempt_file = tmp_path / "exempt.txt"
    exempt_file.write_text("192.0.2.7\n")
    sid = _create(capped, image="registry.example.com/other-judge:1.0.0", xff="192.0.2.7")
    assert _submit(capped, sid, xff="192.0.2.7")[0] == 200
    assert _submit(capped, sid, xff="192.0.2.7")[0] == 200
    # The default cap (2) bites on the third submit, file entry or not.
    assert _submit(capped, sid, xff="192.0.2.7")[0] == 429


# --------------------------------------------------------------------------- #
# Destroyed-session signal: 410 Gone terminal, never a hanging 404
# --------------------------------------------------------------------------- #
def test_destroyed_session_relay_and_status_return_410_terminal(capped) -> None:
    sid = _create(capped)
    assert _submit(capped, sid)[0] == 200  # session proven working
    # Destroy it (idempotent delete).
    status, _ = _request(f"{capped.url}/v1/judge/sessions/{sid}", None, method="DELETE")
    assert status == 200
    # Relay now answers 410 with the terminal contract.
    status, body = _submit(capped, sid)
    assert status == 410
    assert body == {
        "error": "judge session destroyed",
        "session_id": sid,
        "error_class": "terminal",
    }
    # Status endpoint likewise.
    status, body = _request(f"{capped.url}/v1/judge/sessions/{sid}", None, method="GET")
    assert status == 410
    assert body["error_class"] == "terminal"
    # A never-existed sid stays 404 (no terminal marker).
    status, body = _request(f"{capped.url}/v1/judge/sessions/jsess-doesnotexist/submit", {"code": "x"})
    assert status == 404
    assert "error_class" not in body
    # And the 410 does NOT consume a submission slot (short-circuit before counting).
    _, recon = _request(f"{capped.url}/v1/judge/sessions?session_ids={sid}", None, method="GET")
    assert recon["sessions"][0]["submissions"] == 1  # only the pre-delete one
