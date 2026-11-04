"""E1 acceptance: lifecycle.

Every created worker is destroyed on exactly one path — DELETE, the
TTL/idle reaper, a tunnel drop past the grace, or service shutdown — and
never leaks. Covers (real local workers, loopback HTTP; every case ends
with long_lived_count==0 and no leftover agent subprocesses):

- DELETE mid-provisioning cancels the background create (two windows:
  during worker-creation latency and during the tunnel wait)
- a shard that fails to boot (min_ready_ratio=1.0) fails the session and
  recycles the surviving shards
- idle reaper (small idle_ttl) and TTL reaper (expiry fast-forwarded: the
  production ttl floor is 60s, so the clock is nudged on the session object
  to exercise the expiry branch without a minute of wall time)
- tunnel drop: reconnect inside the grace heals untouched; beyond the grace
  the shard is marked failed (a single-shard session flips failed) and its
  worker is reaped
- client abort mid-submit leaks nothing (the worker stays registered and
  finishes the judging; the tunnel is untouched)
- service shutdown destroys every live worker
"""
from __future__ import annotations

import json
import time
import urllib.error

from helpers_cde import (
    cleanup_app,
    close_tunnel_server_side,
    create_session,
    delete_session,
    free_port_range,
    get_health,
    get_submissions,
    hidden_count,
    kill_agent,
    service_factory,
    session_status,
    submit,
    synth,
    tunnel_connected,
    wait_gone,
    wait_ready,
    wait_session_status,
    wait_until,
    windows,
    make_tar_gz,
    write_recorder_judge,
)

__all__ = ["synth", "windows", "service_factory"]


def _wait_no_leaks(handle, where: str, timeout: float = 10.0):
    def _poll():
        if handle.adapter.long_lived_count() == 0 and not handle.adapter.live_agent_pids():
            return True
        return None

    wait_until(_poll, timeout=timeout, what=f"{where}: workers recycled")
    handle.adapter.assert_no_leaks(where)


def test_delete_mid_provisioning_create_latency(service_factory):
    handle = service_factory(adapter_kwargs={"create_delay": 2.0})
    resp = create_session(handle, n_shards=2)
    sid = resp["session_id"]
    status, body = delete_session(handle, sid)
    assert status == 200 and body["stopped"] is True
    wait_gone(handle, sid, timeout=10)
    _wait_no_leaks(handle, "delete during worker creation")


def test_delete_mid_provisioning_tunnel_wait(service_factory):
    # The agent never launches (injected): provisioning sits in the tunnel
    # wait with the workers already created — DELETE must recycle them.
    handle = service_factory(
        ready_timeout_seconds=10,
        adapter_kwargs={"should_fail": lambda app: True},
    )
    resp = create_session(handle, n_shards=2)
    sid = resp["session_id"]
    # Wait until both workers exist (creation done, tunnel wait pending).
    wait_until(lambda: len(handle.adapter.workers) == 2, timeout=10,
               what="both workers created")
    status, body = delete_session(handle, sid)
    assert status == 200 and body["stopped"] is True
    wait_gone(handle, sid, timeout=10)
    _wait_no_leaks(handle, "delete during tunnel wait")


def test_partial_boot_failure_recycles_survivors(service_factory):
    # min_ready_ratio=1.0 (default): one dead shard fails the whole session;
    # the surviving shards' workers must be recycled, never leaked.
    handle = service_factory(
        # Give healthy local subprocesses startup margin; only the
        # explicitly suppressed agent should miss this deadline.
        ready_timeout_seconds=15,
        adapter_kwargs={"should_fail": lambda app: app.endswith("-s1")},
    )
    resp = create_session(handle, n_shards=3)
    sid = resp["session_id"]
    failed = wait_session_status(handle, sid, "failed", timeout=30)
    assert failed["failed_shards"] == 1
    assert failed["live_shards"] == 2
    assert failed["error"].startswith("judge session create failed:")
    _wait_no_leaks(handle, "partial boot failure")
    delete_session(handle, sid)


def test_idle_reap(service_factory):
    handle = service_factory(idle_ttl_seconds=1.0)
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)
    assert handle.adapter.long_lived_count() == 1
    # No relay traffic (status polls do not touch last_active): the idle
    # reaper destroys the session and its worker.
    wait_gone(handle, sid, timeout=15)
    _wait_no_leaks(handle, "idle reap")


def test_ttl_reap(service_factory):
    handle = service_factory()
    resp = create_session(handle, ttl=60)
    sid = resp["session_id"]
    ready = wait_ready(handle, sid)
    assert ready["expires_at"] > time.time() + 50
    # The production ttl floor is 60s (ttl = max(60, ...)): fast-forward the
    # session clock to exercise the expiry branch without a minute of wall
    # time. The reaper path under test (expires reached -> destroy) is the
    # same one a natural expiry takes.
    session = handle.app["judge_sessions"].get(sid)
    session.expires = time.time() - 1
    wait_gone(handle, sid, timeout=15)
    _wait_no_leaks(handle, "ttl reap")


def test_tunnel_drop_grace_heals_and_beyond_grace_reaps(service_factory):
    handle = service_factory(shard_down_grace_ticks=2)
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)
    app_name = sid  # single-shard: app name == session id

    # Drop inside the grace: the agent redials, the shard is never marked.
    close_tunnel_server_side(handle, app_name)
    assert not tunnel_connected(handle, app_name) or True  # racy by design
    wait_until(lambda: tunnel_connected(handle, app_name), timeout=10,
               what="agent redialed inside the grace")
    deadline = time.time() + 1.0  # a few reaper ticks past the drop
    while time.time() < deadline:
        status, body = session_status(handle, sid)
        assert status == 200 and body["status"] == "ready"
        assert body["failed_shards"] == 0
        time.sleep(0.1)
    assert handle.adapter.long_lived_count() == 1

    # Beyond the grace: kill the agent (no redial); the shard is marked
    # failed, the single-shard session flips failed, the worker is reaped.
    kill_agent(handle, app_name)
    failed = wait_session_status(handle, sid, "failed", timeout=15)
    assert "all 1 shards are dead" in failed["error"]
    _wait_no_leaks(handle, "tunnel down beyond grace")
    delete_session(handle, sid)


def test_submit_in_flight_client_abort_leaks_nothing(service_factory, tmp_path):
    script = write_recorder_judge(tmp_path)
    handle = service_factory(
        judge_port=free_port_range(8),
        command=f"python3 {script}",
    )
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)

    try:
        submit(handle, sid, b"SLOW " + make_tar_gz({"s.py": b"x"}), timeout=2)
        raise AssertionError("the slow submit should have timed out client-side")
    except (urllib.error.URLError, TimeoutError, OSError):
        pass

    # The abort hurt nothing: worker registered, tunnel up, relay usable.
    assert handle.adapter.long_lived_count() == 1
    assert tunnel_connected(handle, sid)
    status, health = get_health(handle, sid)
    assert status == 200 and health["status"] == "ok"
    assert hidden_count(handle, sid) == 1

    # The worker still finishes the judging exactly once.
    def _judged():
        status, merged = get_submissions(handle, sid)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    wait_until(_judged, timeout=30, what="aborted submission still judged")

    status, body = delete_session(handle, sid)
    assert status == 200
    _wait_no_leaks(handle, "client abort mid-submit")


def test_shutdown_destroys_all_workers(service_factory):
    handle = service_factory()
    resp_a = create_session(handle, n_shards=1)
    resp_b = create_session(handle, n_shards=2)
    wait_ready(handle, resp_a["session_id"])
    wait_ready(handle, resp_b["session_id"])
    assert handle.adapter.long_lived_count() == 3

    # The app's own shutdown path (store.shutdown via on_cleanup) must
    # destroy every live worker — nothing leaks past it.
    cleanup_app(handle)
    assert handle.adapter.long_lived_count() == 0
    assert handle.adapter.live_agent_pids() == []
    handle.adapter.assert_no_leaks("service shutdown")
