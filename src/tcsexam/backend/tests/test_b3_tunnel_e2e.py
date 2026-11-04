"""B3 acceptance: the reverse tunnel, end to end.

Real aiohttp service + real local-process adapter + the synthetic judge
worker (in-process shard apps). The store boots a local "worker", uploads
the agent bundle, and launches judge_session_agent.py as a REAL local
process that dials the service tunnel — the same code a production worker
runs. Covered:

* READY handshake: the agent's tunnel registers in the TunnelManager (app
  connected, ready_info recorded), the session flips ready;
* relay round trip: POST /submit fans out through the tunnel and GET
  /submissions comes back aggregated (five numbers, K stripped);
* judge kill (the synthetic worker's control kill): relayed requests fail
  with a transient 502 ("please try again");
* tunnel drop with an in-flight request: the caller gets a 502 abort, the
  session is HELD (not torn down on the spot), the agent redials, the
  shard's down-ticks reset and judging resumes;
* a drop that outlasts the down-grace: the shard is marked failed, the
  all-dead session flips failed, and the worker is reaped;
* the tunnel dial address comes from explicit config: agent_config.json's
  service_ws_url derives from public_base_url (two different values give two
  different URLs; http -> ws, https -> wss; unset falls back to the
  configured advertise address — never a baked-in default).

Everything stays on loopback: the agents dial 127.0.0.1, and the
https-derivation case points at a closed loopback port.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from helpers_b import (  # noqa: E402
    SyntheticPool,
    WORK_DIR,
    create_session,
    free_port,
    free_port_range,
    http_request,
    start_service,
    stop_service,
    wait_ready,
    wait_until,
)

IMAGE = "registry.example.com/b3-judge:1"


@pytest.fixture
def rig(tmp_path):
    """Service + synthetic-pool factory; everything started is torn down."""
    handles = []
    pools = []

    def _service(**kwargs):
        handle = start_service(tmp_path / f"state-{len(handles)}", **kwargs)
        handles.append(handle)
        return handle

    def _pool(handle, n_ports=1, base_port=None, with_slow=False):
        pool = SyntheticPool().start(handle, n_ports, base_port=base_port, with_slow=with_slow)
        pools.append(pool)
        return pool

    yield types.SimpleNamespace(service=_service, pool=_pool)
    for pool in pools:
        pool.cleanup()
    for handle in handles:
        stop_service(handle)


def _ready_session(handle, payload=None):
    body = create_session(handle, payload or {"judge_image": IMAGE})
    session = wait_ready(handle, body["session_id"])
    return body["session_id"], session


def test_ready_handshake_and_submit_roundtrip(rig) -> None:
    base = free_port_range(1)
    handle = rig.service(judge_port=base)
    pool = rig.pool(handle, 1, base_port=base)
    # The local adapter's first worker relays to judge_port == pool base.
    sid, session = _ready_session(handle)

    # READY handshake: the tunnel is registered service-side, with the
    # agent's READY payload recorded (app identity + label + judge port).
    # The store's ready flip fires on the tunnel CONNECT; the READY frame is
    # the next message, so poll for it (it normally lands within ms).
    assert handle.tunnels.is_connected(sid)
    wait_until(lambda: handle.tunnels.ready_info(sid) is not None, what="the agent's READY frame")
    info = handle.tunnels.ready_info(sid)
    assert info.get("app_name") == sid
    assert info.get("label") == "tcsexam-judge"  # the configured ready_label
    assert info.get("port") == pool.base_port

    # Session status endpoint agrees: ready, one live shard, tunnel up.
    status, raw = http_request(handle, "GET", f"/v1/judge/sessions/{sid}")
    assert status == 200
    view = json.loads(raw.decode())
    assert view["status"] == "ready" and view["tunnel_connected"] is True
    assert view["live_shards"] == 1 and view["failed_shards"] == 0

    # Relay round trip: submit through the tunnel, then the aggregated
    # history comes back (one synthetic shard: A=2, B=1, K=4 -> MAX ->
    # better=1, delta=+1; K never leaves the service).
    status, raw = http_request(
        handle, "POST", f"/v1/judge/sessions/{sid}/submit", body=b"fake-solver-tar"
    )
    assert status == 202, raw.decode()
    ack = json.loads(raw.decode())
    assert ack == {"submission": 0, "status": "running", "shards": 1}

    status, raw = http_request(handle, "GET", f"/v1/judge/sessions/{sid}/submissions")
    assert status == 200, raw.decode()
    merged = json.loads(raw.decode())
    assert merged["count"] == 1 and merged["shards"] == 1 and merged["best"] == 0
    entry = merged["submissions"][0]
    assert entry["status"] == "ok"
    assert (entry["better"], entry["equal"], entry["worse"]) == (1, 0, 0)
    assert entry["delta"] == 1 and entry["failed"] == 0
    (record,) = entry["records"]
    assert record["instance"].startswith("synthetic-")
    assert record["A"] == 2 and record["B"] == 1
    assert "K" not in record, "the hidden channel must never expose the K anchor"
    assert "excluded_records" not in entry, "the excluded side-channel stays out of hidden aggregation"

    # Teardown path: DELETE destroys the session and recycles the worker.
    status, _ = http_request(handle, "DELETE", f"/v1/judge/sessions/{sid}")
    assert status == 200
    wait_until(lambda: handle.adapter.long_lived_count() == 0, what="worker recycle after DELETE")
    wait_until(lambda: not handle.tunnels.is_connected(sid), what="tunnel teardown after DELETE")


def test_judge_listener_kill_gives_transient_502(rig) -> None:
    """Kill the judge listener (the synthetic worker's control kill): the
    agent's relay then gets an upstream failure and answers a 502 carrying
    the transient retry hint. Side effect pinned here: a 5xx from a live
    shard marks the shard failed, and with every shard dead the session
    flips failed (the caller learns the truth instead of retrying forever)."""
    base = free_port_range(1)
    handle = rig.service(judge_port=base)
    pool = rig.pool(handle, 1, base_port=base)
    sid, session = _ready_session(handle)

    pool.kill(pool.base_port)
    # The tunnel itself is still up (the agent only relays) — the failure
    # surfaces per request.
    assert handle.tunnels.is_connected(sid)
    status, raw = http_request(
        handle, "POST", f"/v1/judge/sessions/{sid}/submit", body=b"fake-solver-tar"
    )
    assert status == 502, f"expected the transient 502, got {status}: {raw.decode()}"
    assert b"502 Bad Gateway" in raw and b"please try again" in raw
    assert session.status == "failed" and session.failed_shards, (
        "a shard answering 5xx is marked failed; the all-dead session flips failed"
    )

    status, _ = http_request(handle, "DELETE", f"/v1/judge/sessions/{sid}")
    assert status == 200


def test_tunnel_drop_inflight_aborts_and_reconnect_recovers(rig) -> None:
    """A tunnel flap with judging in flight: the in-flight caller gets a 502
    abort; the session is NOT torn down on the spot (the down-grace owns the
    drop); the agent redials, and the session judges on, with its submission
    sequence intact."""
    base = free_port_range(1)
    handle = rig.service(judge_port=base, reaper_interval_seconds=0.2, shard_down_grace_ticks=60)
    pool = rig.pool(handle, 1, base_port=base, with_slow=True)
    sid, session = _ready_session(handle)

    # The relay works before the drop (submission 0).
    status, _ = http_request(handle, "POST", f"/v1/judge/sessions/{sid}/submit", body=b"tar-0")
    assert status == 202

    # Start a slow relayed request and wait until it is in flight on the tunnel.
    outcome: dict = {}

    def _slow_call():
        outcome["status"], outcome["body"] = http_request(
            handle, "GET", f"/v1/judge/sessions/{sid}/slow"
        )

    thread = threading.Thread(target=_slow_call, daemon=True)
    thread.start()
    wait_until(lambda: handle.tunnels.in_flight(sid) >= 1, what="the slow request in flight")

    # Drop the tunnel service-side (a gateway/proxy flap): the WebSocket
    # closes; the worker and the session must survive.
    tunnel = handle.tunnels._tunnels[sid]
    handle.run_async(tunnel.ws.close())

    thread.join(timeout=15)
    assert outcome["status"] == 502, f"in-flight request answered {outcome}"
    assert b"502 Bad Gateway" in outcome["body"] and b"aborted" in outcome["body"]
    # Note on wording: the abort path's marker for the task harness is the
    # "502 Bad Gateway" prefix (tunnel.py's _bad_gateway documents it as the
    # transient-failure marker); the explicit "please try again" hint rides
    # on the no-tunnel / write-failure / upstream-unreachable wordings (the
    # previous test pins those).

    # Held, not killed: still ready, worker still registered.
    assert session.status == "ready"
    assert handle.adapter.long_lived_count() == 1, "a dropped tunnel must not reap the worker"

    # The agent redials on its own (judge_session_agent's serve loop: the
    # first redial attempt is immediate, backoff only kicks in after a FAILED
    # dial round — so a healthy service sees the tunnel heal within a
    # fraction of the grace window, usually before the reaper's next tick;
    # the deterministic down-tick observation lives in the beyond-grace
    # test below, where nothing can reconnect).
    wait_until(lambda: handle.tunnels.is_connected(sid), timeout=15, what="the agent's redial")
    assert session.status == "ready"
    assert session.failed_shards == {}, "a drop inside the grace must never fail the shard"
    assert handle.adapter.long_lived_count() == 1, "the worker survived the whole flap"

    # Recovery: the relay carries on with the SAME submission sequence
    # (id 1 after 0) — the worker's judging state survived the flap.
    status, raw = http_request(handle, "POST", f"/v1/judge/sessions/{sid}/submit", body=b"tar-1")
    assert status == 202, raw.decode()
    assert json.loads(raw.decode())["submission"] == 1

    pool.slow_release.set()
    status, _ = http_request(handle, "DELETE", f"/v1/judge/sessions/{sid}")
    assert status == 200


def test_tunnel_drop_beyond_grace_marks_failed_and_reaps(rig) -> None:
    """A worker that never comes back: kill the agent process outright (no
    redial). The session survives the grace window, then the shard is marked
    failed, the all-dead session flips failed, and the worker is reaped off
    the adapter's long-lived table."""
    base = free_port_range(1)
    # Slow reaper on purpose: the grace window (~1.0-1.5s) stays observable
    # even when the test thread is descheduled under host load.
    handle = rig.service(judge_port=base, reaper_interval_seconds=0.5, shard_down_grace_ticks=3)
    pool = rig.pool(handle, 1, base_port=base)
    sid, session = _ready_session(handle)

    worker = handle.adapter.workers[0]
    died_at = time.time()
    asyncio.run(worker.delete())  # SIGKILLs the agent process: the tunnel drops hard
    wait_until(lambda: not handle.tunnels.is_connected(sid), what="tunnel down after the kill")

    # The down-grace is a real timer, not an instant verdict: at every
    # observed down-tick below the 3-tick grace the session is still ready
    # and the worker still registered. Nothing can reconnect here (the
    # process is dead), so the ticks climb deterministically; a failed shard
    # is popped from the tick table, ending the watch.
    saw_ticks = 0
    while session.status != "failed":
        ticks = session.shard_down_ticks.get(0, 0)
        if ticks > saw_ticks:
            saw_ticks = ticks
            assert ticks < 3, f"the down-ticks ran past the 3-tick grace: {ticks}"
            assert handle.adapter.long_lived_count() == 1, (
                f"worker reaped at down-tick {ticks}, inside the 3-tick grace"
            )
        time.sleep(0.02)
    assert saw_ticks >= 1, "the reaper's down-ticks never showed before the fail"

    # Past the grace: failed, with the worker reaped.
    assert time.time() - died_at >= 0.9, (
        "the session died faster than the 3-tick down-grace at a 0.5s reaper interval"
    )
    assert "all 1 shards are dead" in session.error, session.error
    assert session.failed_shards, "the dropped shard was never marked failed"
    wait_until(
        lambda: handle.adapter.long_lived_count() == 0,
        what="worker reaped after the grace expired",
    )

    status, raw = http_request(handle, "GET", f"/v1/judge/sessions/{sid}")
    view = json.loads(raw.decode())
    assert view["status"] == "failed" and view["error"]


def test_tunnel_ws_url_derived_from_public_base_url(rig) -> None:
    """agent_config.json's service_ws_url is built from the service's
    configured public URL — two deployments with different public_base_url
    hand their agents different dial addresses (no baked-in default)."""
    cases = []

    # Case A: explicit http public URL -> ws scheme. The URL points at a
    # closed loopback port: the agent's dial fails and retries (loopback
    # only), the session stays provisioning — the agent_config.json write
    # precedes the dial, so the derivation is readable without a connect.
    port_a = free_port()
    handle_a = rig.service(public_base_url=f"http://127.0.0.1:{port_a}")
    body_a = create_session(handle_a, {"judge_image": IMAGE})
    cases.append(("http-explicit", handle_a, body_a["session_id"], f"ws://127.0.0.1:{port_a}/v1/tunnel/{body_a['session_id']}"))

    # Case B: explicit https public URL -> wss scheme (closed loopback port:
    # the agent's dial fails and retries, everything stays on loopback).
    port_b = free_port()
    handle_b = rig.service(public_base_url=f"https://127.0.0.1:{port_b}")
    body_b = create_session(handle_b, {"judge_image": IMAGE})
    cases.append(("https-explicit", handle_b, body_b["session_id"], f"wss://127.0.0.1:{port_b}/v1/tunnel/{body_b['session_id']}"))

    # Case C: public_base_url unset -> the configured advertise address
    # (advertise_host:port), still config-derived, and the agent really
    # connects through it.
    handle_c = rig.service()
    sid_c, _ = _ready_session(handle_c)
    cases.append(("advertise-fallback", handle_c, sid_c, f"ws://127.0.0.1:{handle_c.config.port}/v1/tunnel/{sid_c}"))

    seen = set()
    for name, handle, sid, expected_ws in cases:
        worker = wait_until(
            lambda h=handle: h.adapter.workers[0] if h.adapter.workers else None,
            what=f"worker creation for case {name}",
        )
        config_path = Path(worker.root) / WORK_DIR.lstrip("/") / "agent_config.json"
        wait_until(config_path.exists, what=f"agent_config.json written for case {name}")
        agent_config = json.loads(config_path.read_text())
        ws_url = agent_config["service_ws_url"]
        assert ws_url == expected_ws, f"case {name}: service_ws_url {ws_url!r} != {expected_ws!r}"
        assert agent_config["app_name"] == sid
        seen.add(ws_url.split("/v1/tunnel/")[0])
        status, _ = http_request(handle, "DELETE", f"/v1/judge/sessions/{sid}")
        assert status == 200

    assert len(seen) == 3, (
        "three different public URL configs produced fewer than three dial bases — "
        "the dial address is not config-derived"
    )
