"""C2 acceptance: sharding.

Covers (all over loopback HTTP, real local workers + synthetic judge):
- single shard (n_shards=1): merged shape without failed_shards keys
- 3 shards: fan-out submit, five-number sums, merged health, archive layout
- partial failure (deterministic injection on shard 1): degraded-ready
  surface (status/failed_shards/live_shards), surviving shards keep judging,
  the dead slice folds into `failed`, archive records the failure verbatim
- all shards fail at create: session failed; submissions/submit answer 502
  transient — total infrastructure failure is NEVER folded into a legal
  zero score (no 200 with an all-zero five-numbers entry)
- all shards killed mid-judging: 502 + session flips failed + archive keeps
  the pre-kill records (and stays readable after the session is reaped)
- cancel in flight: DELETE while provisioning recycles every worker
- pool semantics: n_shards=1 keeps the whole instance set on one shard —
  the in-worker env carries NO INSTANCE_SHARD (and no INSTANCE_SET for
  hidden); sharded/public sessions get INSTANCE_SHARD=i/N / INSTANCE_SET
  (asserted from the judge server's own dumped environment)
"""
from __future__ import annotations

import json

from helpers_cde import (
    AUTH,
    create_session,
    delete_session,
    free_port_range,
    get_archive,
    get_health,
    get_submissions,
    http,
    read_worker_env,
    service_factory,
    session_status,
    submit,
    synth,
    wait_gone,
    wait_ready,
    wait_session_status,
    wait_until,
    windows,
    make_tar_gz,
    write_recorder_judge,
)

__all__ = ["synth", "windows", "service_factory"]


def _terminal_entry(handle, sid, k=0, timeout=30):
    """Poll GET submissions until entry k reaches a terminal status."""
    def _poll():
        st, merged = get_submissions(handle, sid)
        if st == 200 and len(merged["submissions"]) > k:
            entry = merged["submissions"][k]
            if entry["status"] != "running":
                return merged
        return None

    return wait_until(_poll, timeout=timeout, what=f"terminal entry {k}")


def test_single_shard(service_factory):
    handle = service_factory()
    resp = create_session(handle, n_shards=1)
    sid = resp["session_id"]
    assert resp["n_shards"] == 1
    wait_ready(handle, sid)

    status, body = submit(handle, sid, make_tar_gz({"s.py": b"1"}))
    assert status == 202 and json.loads(body)["submission"] == 0

    merged = _terminal_entry(handle, sid)
    assert merged["shards"] == 1
    assert merged["count"] == 1
    # n_shards == 1 omits the failed_shards keys (== 0 by definition).
    assert "failed_shards" not in merged
    entry = merged["submissions"][0]
    assert "failed_shards" not in entry
    assert entry["status"] == "ok"
    assert (entry["better"], entry["equal"], entry["worse"], entry["failed"]) == (1, 0, 0, 0)
    assert entry["delta"] == 1
    assert len(entry["records"]) == 1

    status, health = get_health(handle, sid)
    assert status == 200
    # Unsharded /health relays straight through: the worker's own answer
    # (the merged shards/failed_shards keys exist on the sharded path only).
    assert health == {"status": "ok"}

    delete_session(handle, sid)


def test_three_shards(service_factory):
    handle = service_factory()
    resp = create_session(handle, n_shards=3)
    sid = resp["session_id"]
    ready = wait_ready(handle, sid)
    assert ready["n_shards"] == 3 and ready["live_shards"] == 3
    tunnels = handle.app["tunnels"]
    apps = [f"{sid}-s{i}" for i in range(3)]
    assert all(tunnels.is_connected(app) for app in apps)
    assert tunnels.connected_count() == 3

    status, body = submit(handle, sid, make_tar_gz({"s.py": b"3"}))
    assert status == 202 and json.loads(body)["shards"] == 3

    merged = _terminal_entry(handle, sid)
    assert merged["shards"] == 3 and merged["failed_shards"] == 0
    entry = merged["submissions"][0]
    assert entry["failed_shards"] == 0
    assert entry["status"] == "ok"
    # Shard statistics simply add up: 3 shards x 1 instance each.
    assert (entry["better"], entry["equal"], entry["worse"], entry["failed"]) == (3, 0, 0, 0)
    assert entry["delta"] == 3
    names = [rec["instance"] for rec in entry["records"]]
    assert len(names) == 3 and names == sorted(names) and len(set(names)) == 3

    status, health = get_health(handle, sid)
    assert status == 200 and health == {"status": "ok", "shards": 3, "failed_shards": 0}

    status, raw = get_archive(handle, sid)
    assert status == 200
    archive = json.loads(raw)
    assert archive["n_shards"] == 3
    assert archive["failed_shards"] == {}
    assert sorted(archive["shard_payloads"]) == ["0", "1", "2"]

    status, body = delete_session(handle, sid)
    assert status == 200 and body["stopped"] is True
    assert all(not tunnels.is_connected(app) for app in apps)
    assert tunnels.connected_count() == 0


def test_partial_failure_degraded(service_factory):
    # floor = ceil(0.34 x 3) = 2: one dead shard still goes ready (degraded).
    handle = service_factory(
        min_ready_ratio=0.34,
        ready_timeout_seconds=3,
        adapter_kwargs={"should_fail": lambda app: app.endswith("-s1")},
    )
    resp = create_session(handle, n_shards=3)
    sid = resp["session_id"]
    ready = wait_ready(handle, sid)
    assert ready["status"] == "ready"
    assert ready["failed_shards"] == 1
    assert ready["live_shards"] == 2
    assert ready["tunnel_connected"] is True

    # The surviving shards judge as usual; the dead slice folds into failed.
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"p"}))
    assert status == 202, body
    merged = _terminal_entry(handle, sid)
    assert merged["failed_shards"] == 1
    entry = merged["submissions"][0]
    assert entry["status"] == "ok"
    assert entry["failed_shards"] == 1
    assert (entry["better"], entry["worse"], entry["failed"]) == (2, 0, 1)
    assert entry["delta"] == 2
    names = [rec["instance"] for rec in entry["records"]]
    assert len(names) == 2, "the dead shard's slice contributes no records"

    status, health = get_health(handle, sid)
    assert status == 200 and health == {"status": "ok", "shards": 3, "failed_shards": 1}

    status, raw = get_archive(handle, sid)
    assert status == 200
    archive = json.loads(raw)
    assert sorted(archive["failed_shards"]) == ["1"]
    assert "did not connect" in archive["failed_shards"]["1"]
    assert sorted(archive["shard_payloads"]) == ["0", "2"]

    # A second submission keeps the sequence continuous on the live shards.
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"p2"}))
    assert status == 202 and json.loads(body)["submission"] == 1
    merged = _terminal_entry(handle, sid, k=1)
    assert merged["count"] == 2
    assert merged["submissions"][1]["failed_shards"] == 1

    delete_session(handle, sid)


def test_all_shards_fail_at_create(service_factory):
    handle = service_factory(
        ready_timeout_seconds=3,
        adapter_kwargs={"should_fail": lambda app: True},
    )
    resp = create_session(handle, n_shards=3)
    sid = resp["session_id"]
    failed = wait_session_status(handle, sid, "failed", timeout=30)
    assert failed["failed_shards"] == 3
    assert failed["live_shards"] == 0
    assert failed["error"].startswith("judge session create failed:")
    assert "please try again" in failed["error"]

    # Total infrastructure failure is an error class, never a legal 0-score:
    # GET submissions must NOT answer 200 with an all-zero five-numbers entry.
    status, body = http(
        "GET", f"{handle.url}/v1/judge/sessions/{sid}/submissions", headers=AUTH
    )
    assert status == 502, body
    assert b"please try again" in body
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"x"}))
    assert status == 502, body
    assert b"no live shard accepted the submission" in body
    assert b"please try again" in body

    delete_session(handle, sid)


def test_all_shards_killed_mid_judging(service_factory, synth):
    handle = service_factory(failed_retention_seconds=1.0)
    resp = create_session(handle, n_shards=2)
    sid = resp["session_id"]
    wait_ready(handle, sid)
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"k"}))
    assert status == 202
    _terminal_entry(handle, sid)

    # Kill both shards' judge servers (control port); the agents (and the
    # tunnels) stay up, the relay legs start answering 502.
    base = handle.config.backend.judge_sessions.judge_port
    for port in (base, base + 1):
        synth.kill_port(port)

    status, body = http(
        "GET", f"{handle.url}/v1/judge/sessions/{sid}/submissions", headers=AUTH
    )
    assert status == 502 and b"every shard is unavailable" in body
    assert b"please try again" in body

    failed = wait_session_status(handle, sid, "failed", timeout=10)
    assert "all 2 shards are dead" in failed["error"]
    assert failed["failed_shards"] == 2

    # The archive keeps the pre-kill records (history never rewritten). The
    # failure markers land in the archive on the next successful aggregated
    # fetch; with every shard dead no fetch succeeds again, so this archive's
    # value is the records layer (failure truth lives on the status endpoint
    # and, for the partial-kill case, in the archive — covered below).
    status, raw = get_archive(handle, sid)
    assert status == 200
    archive = json.loads(raw)
    for shard_payload in archive["shard_payloads"].values():
        assert shard_payload["submissions"][0]["records"], "pre-kill records archived"

    # Past the failed-retention window the session is destroyed; the archive
    # stays readable for the verifier (records survive release).
    wait_gone(handle, sid, timeout=10)
    status, raw = get_archive(handle, sid)
    assert status == 200, raw
    archive = json.loads(raw)
    assert archive["shard_payloads"]["0"]["submissions"][0]["status"] == "ok"


def test_shard_killed_mid_judging_partial(service_factory, synth):
    """One shard dies mid-judging: entries it judged BEFORE dying keep their
    archived records (history is never rewritten backwards); entries it never
    judged count toward `failed`; the archive records the failure marker."""
    handle = service_factory()
    resp = create_session(handle, n_shards=3)
    sid = resp["session_id"]
    wait_ready(handle, sid)
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"pk"}))
    assert status == 202
    _terminal_entry(handle, sid)

    # Kill shard 1's judge server; the relay leg to it starts answering 502.
    base = handle.config.backend.judge_sessions.judge_port
    synth.kill_port(base + 1)

    # Entry 0 was judged by every shard before the kill: full credit kept.
    merged = _terminal_entry(handle, sid, k=0)
    assert merged["failed_shards"] == 1
    entry0 = merged["submissions"][0]
    assert entry0["failed_shards"] == 0, "shard 1 judged entry 0 before dying"
    assert (entry0["better"], entry0["failed"]) == (3, 0)
    assert len(entry0["records"]) == 3

    # Entry 1: shard 1 is absent — its slice folds into failed (not worse).
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"pk2"}))
    assert status == 202, body
    merged = _terminal_entry(handle, sid, k=1)
    entry1 = merged["submissions"][1]
    assert entry1["status"] == "ok"
    assert entry1["failed_shards"] == 1
    assert (entry1["better"], entry1["worse"], entry1["failed"]) == (2, 0, 1)
    assert len(entry1["records"]) == 2

    status, raw = get_archive(handle, sid)
    assert status == 200
    archive = json.loads(raw)
    assert sorted(archive["failed_shards"]) == ["1"]
    assert archive["failed_shards"]["1"], "the failure reason is recorded"
    # The dead shard's last fetched payload is retained in the archive.
    assert sorted(archive["shard_payloads"]) == ["0", "1", "2"]
    assert archive["shard_payloads"]["1"]["submissions"][0]["records"]

    delete_session(handle, sid)


def test_cancel_mid_provisioning(service_factory):
    handle = service_factory(adapter_kwargs={"create_delay": 2.0})
    resp = create_session(handle, n_shards=3)
    sid = resp["session_id"]
    # Delete while the shard boots are still in their creation latency.
    status, body = delete_session(handle, sid)
    assert status == 200 and body["stopped"] is True
    wait_gone(handle, sid, timeout=10)
    # The background create was cancelled and boot-midway workers recycled.
    handle.adapter.assert_no_leaks("cancel mid-provisioning")


def test_pool_semantics_single_shard_env(service_factory, tmp_path):
    """A pool-semantics task runs unsharded: the single worker receives the
    WHOLE instance set — the slice selector INSTANCE_SHARD must be absent
    from the judge server's environment (it is only injected when
    n_shards > 1), and INSTANCE_SET only rides on public sessions."""
    script = write_recorder_judge(tmp_path)
    handle = service_factory(
        judge_port=free_port_range(8),
        command=f"python3 {script}",
    )

    # Unsharded hidden session: no INSTANCE_SHARD, no INSTANCE_SET.
    resp = create_session(handle, n_shards=1)
    sid = resp["session_id"]
    wait_ready(handle, sid)
    env = read_worker_env(handle, sid)
    assert env["PORT"], "the agent passes the judge port as PORT"
    assert env["INSTANCE_SHARD"] is None, "n_shards=1: full set on the one shard"
    assert env["INSTANCE_SET"] is None, "hidden is the default; no export"

    # Sharded public session: each shard gets its slice selector + the
    # public redirect.
    resp = create_session(handle, n_shards=3, instance_set="public")
    sid2 = resp["session_id"]
    wait_ready(handle, sid2)
    for i in range(3):
        env = read_worker_env(handle, f"{sid2}-s{i}")
        assert env["INSTANCE_SHARD"] == f"{i}/3"
        assert env["INSTANCE_SET"] == "public"

    delete_session(handle, sid)
    delete_session(handle, sid2)
