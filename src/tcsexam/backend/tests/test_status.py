"""/v1/status tests: payload aggregation, the request-counting ring buffer
(including over real HTTP through the auth middleware), and the image-family
bucketing.

No real workers, no network beyond localhost.
"""
from __future__ import annotations

import json
import time
import types
import urllib.error
import urllib.request

import pytest

from conftest import ARCHIVE_TOKEN, TOKEN_ID, TOKEN_SECRET, wait_session_ready

from tcsexam.backend.config import BaseServiceConfig, JudgeSessionsConfig
from tcsexam.backend.status import (
    RequestCounter,
    StatusCollector,
    classify_path,
    image_family,
)


# --------------------------------------------------------------------------- #
# Pure-function units
# --------------------------------------------------------------------------- #
def test_image_family() -> None:
    assert image_family("registry.example.com/family-judge:1.0.0") == "family"
    assert (
        image_family("registry.example.com/public/bench-knn-judge:v3")
        == "bench-knn"
    )
    # A registry port colon must not be mistaken for the tag colon.
    assert image_family("registry.example.com:5000/ns/abc-judge:v1") == "abc"

    # tag-style: variants judge images keep the family in the tag
    assert (
        image_family(
            "registry.example.com/platform/bench:abc-aig-prove-edge11-judge-svc-0.1.0"
        )
        == "abc-aig-prove-edge11"
    )
    assert (
        image_family("platform/bench:zydis-decode-throughput-judge-1.0.1")
        == "zydis-decode-throughput"
    )
    # non-judge image: name passes through
    assert image_family("library/ubuntu-24.04-sbx-v1:latest") == "ubuntu-24.04-sbx-v1"
    # No -judge suffix: the basename passes through.
    assert image_family("registry.example.com/ns/plain-image:latest") == "plain-image"
    assert image_family("bare-judge") == "bare"


def test_classify_path() -> None:
    assert classify_path("/v1/judge/sessions") == "/v1/judge/sessions"
    assert classify_path("/v1/judge/sessions/jsess-abc") == "/v1/judge/sessions/{sid}"
    assert (
        classify_path("/v1/judge/sessions/jsess-abc/submissions")
        == "/v1/judge/sessions/{sid}"
    )
    assert classify_path("/v1/tunnel/my-app") == "/v1/tunnel/{app}"
    assert classify_path("/v1/status") is None  # probes are not counted
    assert classify_path("/v1/health") is None
    assert classify_path("/apps/my-app/evaluate") == "other"


# --------------------------------------------------------------------------- #
# RequestCounter
# --------------------------------------------------------------------------- #
class _Clock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def test_request_counter_windows_and_top_paths() -> None:
    clock = _Clock()
    counter = RequestCounter(now=clock)
    counter.record("/v1/judge/sessions")
    counter.record("/v1/judge/sessions")
    clock.t += 70  # the two above are now 70s old: inside 300s, outside 60s
    counter.record("/v1/judge/sessions/jsess-1")
    counter.record("/v1/tunnel/app-a")
    counter.record("/v1/calls")
    snap = counter.snapshot()
    by_60 = snap["last_60s"]["by_path"]
    assert snap["last_60s"]["total"] == 3
    assert by_60 == {
        "/v1/judge/sessions/{sid}": 1,
        "/v1/tunnel/{app}": 1,
        "other": 1,
    }
    assert snap["last_300s"]["total"] == 5
    assert snap["last_300s"]["by_path"]["/v1/judge/sessions"] == 2
    assert snap["top_paths"][0] == {"path": "/v1/judge/sessions", "count": 2}
    # Deterministic order for ties (path name ascending).
    assert [p["path"] for p in snap["top_paths"]] == [
        "/v1/judge/sessions",
        "/v1/judge/sessions/{sid}",
        "/v1/tunnel/{app}",
        "other",
    ]


def test_request_counter_prunes_beyond_window() -> None:
    clock = _Clock()
    counter = RequestCounter(now=clock)
    counter.record("/v1/calls")
    clock.t += 301  # beyond the 300s window
    counter.record("/v1/calls")
    snap = counter.snapshot()
    assert snap["last_300s"]["total"] == 1
    assert snap["last_60s"]["total"] == 1
    assert snap["last_300s"]["by_path"] == {"other": 1}


def test_request_counter_empty() -> None:
    snap = RequestCounter().snapshot()
    assert snap == {
        "last_60s": {"total": 0, "by_path": {}},
        "last_300s": {"total": 0, "by_path": {}},
        "top_paths": [],
    }


# --------------------------------------------------------------------------- #
# StatusCollector
# --------------------------------------------------------------------------- #
class _FakeSession:
    def __init__(self, image: str) -> None:
        self.image = image


class _FakeStore:
    def __init__(self, sessions) -> None:
        self._sessions = sessions

    def live_sessions(self):
        return list(self._sessions)


class _FakeTunnels:
    def __init__(self, count: int) -> None:
        self._count = count

    def connected_count(self) -> int:
        return self._count


class _FakeExecutor:
    def __init__(self, count: int, memory_mb: int = 0) -> None:
        self._count = count
        self._memory_mb = memory_mb

    def long_lived_count(self) -> int:
        return self._count

    def long_lived_memory_mb(self) -> int:
        return self._memory_mb


def _collector(**overrides) -> StatusCollector:
    kwargs = {
        "config": BaseServiceConfig(service_name="tcsexam-backend"),
        "sessions_config": JudgeSessionsConfig(max_sessions=16),
        "sessions_store": _FakeStore([]),
        "tunnels": _FakeTunnels(0),
        "executor": _FakeExecutor(0),
        "request_counter": RequestCounter(),
        "started_at": 1000.0,
        "now": lambda: 1060.0,
    }
    kwargs.update(overrides)
    return StatusCollector(**kwargs)


def test_status_payload_keys_and_values() -> None:
    store = _FakeStore(
        [
            _FakeSession("reg/public/knn-judge:v3"),
            _FakeSession("reg/public/knn-judge:v3"),
            _FakeSession("reg/public/stability-judge:v1"),
        ]
    )
    collector = _collector(
        sessions_store=store, tunnels=_FakeTunnels(2), executor=_FakeExecutor(3, 24576)
    )
    snap = collector.snapshot()
    # Every top-level key is present (the slim extracted shape).
    assert set(snap) == {
        "service",
        "live",
        "sessions_by_family",
        "requests",
        "callers",
        "submission_cap",
    }
    assert snap["service"]["name"] == "tcsexam-backend"
    assert snap["service"]["started_at"] == 1000.0
    assert snap["service"]["uptime_seconds"] == 60.0
    assert isinstance(snap["service"]["version"], str)
    assert snap["live"] == {
        "sessions": 3,
        "tunnels": 2,
        "workers": 3,
        "worker_memory_mb": 24576,
    }
    assert snap["sessions_by_family"] == [
        {"family": "knn", "count": 2},
        {"family": "stability", "count": 1},
    ]
    assert snap["callers"] == []
    # sessions_config present: the submission_cap section is populated.
    assert snap["submission_cap"]["enabled"] is False
    assert snap["submission_cap"]["journaled_sessions"] == 0


def test_status_sessions_by_family_top20() -> None:
    store = _FakeStore(
        [_FakeSession(f"reg/fam-{i:02d}-judge:v1") for i in range(25)]
        + [_FakeSession("reg/fam-00-judge:v1")]  # fam-00 gets count 2 -> first
    )
    families = _collector(sessions_store=store).snapshot()["sessions_by_family"]
    assert len(families) == 20
    assert families[0] == {"family": "fam-00", "count": 2}
    assert all(f["count"] == 1 for f in families[1:])


def test_status_missing_sources_are_null_not_missing() -> None:
    config = BaseServiceConfig(service_name=None)  # no display name, no sources anywhere
    snap = StatusCollector(config=config).snapshot()
    assert snap["service"]["name"] is None
    assert snap["live"] == {
        "sessions": None,
        "tunnels": None,
        "workers": None,
        "worker_memory_mb": None,
    }
    assert snap["sessions_by_family"] == []
    assert snap["callers"] == []
    assert snap["requests"]["last_60s"]["total"] == 0
    assert snap["submission_cap"] is None


# --------------------------------------------------------------------------- #
# Over real HTTP: auth-middleware counting + the wired /v1/status endpoint
# --------------------------------------------------------------------------- #
def _request(url: str, body=None, *, method: str = "POST", auth: bool = True):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["X-TCSEXAM-Token-Id"] = TOKEN_ID
        headers["X-TCSEXAM-Token-Secret"] = TOKEN_SECRET
        if isinstance(body, dict) and body.get("instance_set", "hidden") == "hidden":
            headers["X-TCSEXAM-Archive-Token"] = ARCHIVE_TOKEN
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_status_endpoint_and_request_counting(jservice) -> None:
    url = jservice.url
    # 1. A rejected request (no token): counted too — a 401 storm is load.
    status, _ = _request(f"{url}/v1/judge/sessions", {"judge_image": "x"}, auth=False)
    assert status == 401
    # 2. A session create (fake adapter, real tunnel client connects):
    # creation answers 202 immediately; readiness is awaited via the store so
    # this stays exactly one HTTP request.
    status, created = _request(
        f"{url}/v1/judge/sessions", {"judge_image": "registry.example.com/family-judge:1.0.0"}
    )
    assert status == 202, created
    sid = created["session_id"]
    wait_session_ready(jservice, sid)
    # 3. A per-session status read (the {sid} bucket).
    status, _ = _request(f"{url}/v1/judge/sessions/{sid}", method="GET")
    assert status == 200

    status, snap = _request(f"{url}/v1/status", method="GET")
    assert status == 200

    assert isinstance(snap["service"]["version"], str)
    assert snap["service"]["name"] == "tcsexam-backend"
    assert snap["service"]["uptime_seconds"] >= 0
    assert snap["live"]["sessions"] == 1
    assert snap["live"]["tunnels"] == 1
    assert snap["live"]["workers"] == 1
    assert snap["sessions_by_family"] == [{"family": "family", "count": 1}]
    assert snap["sessions_by_status"] == {
        "ready": 1,
        "provisioning": 0,
        "failed": 0,
        "hibernated": 0,
        "destroyed": 0,
    }
    # This traffic carries no run-id headers, so every non-exempt request
    # aggregates under run_id="" (the adoption-gap bucket; agent_name
    # likewise ""). The /v1/status read above is probe traffic — counted in
    # requests/min but not in the callers table (4 requests -> 3 caller
    # hits). The sharded session carries its caller identity (run_id "",
    # token id, no agent name), so it lands in the same bucket
    # (sessions: 1).
    assert snap["callers"] == [
        {
            "token_id": TOKEN_ID,
            "run_id": "",
            "agent_name": "",
            "sessions": 1,
            "requests_300s": 3,
        },
        {
            "token_id": "-",
            "run_id": "",
            "agent_name": "",
            "sessions": 0,
            "requests_300s": 1,
        },
    ]

    by_path = snap["requests"]["last_300s"]["by_path"]
    assert by_path["/v1/judge/sessions"] == 2  # the 401 + the create
    assert by_path["/v1/judge/sessions/{sid}"] == 1
    assert by_path["/v1/tunnel/{app}"] == 1  # the session agent's WS connect
    assert "other" not in by_path  # this very /v1/status read is not counted
    assert snap["requests"]["last_60s"]["total"] == 4
    assert snap["requests"]["top_paths"][0] == {"path": "/v1/judge/sessions", "count": 2}


def test_status_endpoint_requires_auth(jservice) -> None:
    status, body = _request(f"{jservice.url}/v1/status", method="GET", auth=False)
    assert status == 401
    assert "unauthorized" in body["error"]
