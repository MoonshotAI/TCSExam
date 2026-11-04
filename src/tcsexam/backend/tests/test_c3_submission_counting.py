"""C3 acceptance: submission counting.

The accounting unit is the relay-level accepted POST /submit, keyed by
session, journaled for restart-proofing. Covers (all over loopback HTTP):

- one accepted submission counts exactly once: repeated GET submissions
  fetches add nothing; a second submit increments by one; a 2-shard fan-out
  still counts ONE (shards are judging-internal parallelism)
- cap reached -> 429 carrying submission_cap_exceeded / cap / used; the
  rejected body never reaches the workers and is never counted
- submit while provisioning -> 503 transient, NOT counted, retriable after
  ready (counted exactly once then)
- hidden submissions count; public-channel (instance_set=public) submissions
  never touch the hidden counter nor the cap (journaled separately)
- disconnect ambiguity never double-counts: the server counts at accept
  (same synchronous block as the cap check, before forwarding), so a client
  that dies mid-submit is counted once and only once; a 4xx pass-through is
  counted once at the relay and is NOT retried (each shard saw it exactly
  once — the archive's per-shard bad_submits proves it)
- restart preservation: a fresh app over the same state_dir replays the
  journal — ?session_ids= counts are identical
"""
from __future__ import annotations

import json
import urllib.error

from helpers_cde import (
    AUTH,
    cleanup_app,
    create_session,
    delete_session,
    free_port_range,
    get_archive,
    get_submissions,
    hidden_count,
    service_factory,
    session_ids_query,
    submit,
    synth,
    wait_ready,
    wait_until,
    windows,
    make_tar_gz,
    write_recorder_judge,
)
from tcsexam.backend.config import SubmissionCapConfig

__all__ = ["synth", "windows", "service_factory"]


def _cap(n: int) -> SubmissionCapConfig:
    return SubmissionCapConfig(enabled=True, default=n)


def test_single_submit_counted_once(service_factory):
    handle = service_factory(submission_cap=_cap(5))
    resp = create_session(handle, n_shards=2)
    sid = resp["session_id"]
    wait_ready(handle, sid)

    status, body = submit(handle, sid, make_tar_gz({"s.py": b"1"}))
    assert status == 202
    assert hidden_count(handle, sid) == 1

    # Reads never count, however often the history is re-fetched.
    for _ in range(3):
        status, merged = get_submissions(handle, sid)
        assert status == 200
    assert hidden_count(handle, sid) == 1

    # A second submit increments by exactly one (the 2-shard fan-out is
    # judging-internal parallelism, never a counting unit).
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"2"}))
    assert status == 202
    assert hidden_count(handle, sid) == 2

    recon = session_ids_query(handle, [sid])
    assert recon["total_submissions"] == 2
    delete_session(handle, sid)


def test_cap_reached_429(service_factory):
    handle = service_factory(submission_cap=_cap(2))
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)

    for i in range(2):
        status, body = submit(handle, sid, make_tar_gz({"s.py": str(i).encode()}))
        assert status == 202, body
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"3"}))
    assert status == 429
    rejection = json.loads(body)
    assert rejection["error"] == "submission_cap_exceeded"
    assert rejection["cap"] == 2
    assert rejection["used"] == 2
    assert "identity" in rejection

    # The rejected submission was neither counted nor judged.
    assert hidden_count(handle, sid) == 2

    def _two():
        status, merged = get_submissions(handle, sid)
        if status == 200 and merged["count"] == 2 and all(
            e["status"] != "running" for e in merged["submissions"]
        ):
            return merged
        return None

    merged = wait_until(_two, timeout=30, what="two judged submissions")
    assert merged["count"] == 2, "the 429 body never reached the workers"
    delete_session(handle, sid)


def test_submit_during_provisioning_503_not_counted(service_factory):
    handle = service_factory(
        submission_cap=_cap(3),
        adapter_kwargs={"create_delay": 1.5},
    )
    resp = create_session(handle)
    sid = resp["session_id"]

    # The session is registered but still booting: 503 transient, not counted.
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"early"}))
    assert status == 503
    payload = json.loads(body)
    assert payload["error_class"] == "transient"
    assert "provisioning" in payload["error"]
    assert "please try again" in payload["error"]
    recon = session_ids_query(handle, [sid])
    assert recon["sessions"][0]["submissions"] == 0
    assert recon["sessions"][0]["present"] is True

    # After ready the retry lands and counts exactly once.
    wait_ready(handle, sid)
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"early"}))
    assert status == 202
    assert hidden_count(handle, sid) == 1
    delete_session(handle, sid)


def test_hidden_counts_public_does_not(service_factory):
    handle = service_factory(submission_cap=_cap(2))
    resp = create_session(handle, instance_set="public")
    pub = resp["session_id"]
    assert resp["instance_set"] == "public"
    wait_ready(handle, pub)

    # Three public submissions (more than the hidden cap of 2): all accepted,
    # none counted against the hidden cap counter.
    for i in range(3):
        status, body = submit(handle, pub, make_tar_gz({"s.py": str(i).encode()}))
        assert status == 202, body
    recon = session_ids_query(handle, [pub])
    row = recon["sessions"][0]
    assert row["submissions"] == 0, "public accepts never enter the hidden counter"
    assert row["public_submissions"] == 3
    assert recon["total_submissions"] == 0

    # The public channel answers per-instance full detail (B/K stripped),
    # including the excluded_records side channel with its reason.
    def _three():
        status, merged = get_submissions(handle, pub)
        if status == 200 and merged["count"] == 3 and all(
            e["status"] != "running" for e in merged["submissions"]
        ):
            return merged
        return None

    merged = wait_until(_three, timeout=30, what="three public submissions judged")
    entry = merged["submissions"][0]
    assert entry["pack_sha256"], "public entries carry the pack digest"
    reasons = {rec.get("reason") for rec in entry["records"]}
    assert "b_equals_k" in reasons
    for rec in entry["records"]:
        assert "B" not in rec and "K" not in rec

    # A hidden session in the same service counts normally.
    resp = create_session(handle)
    hid = resp["session_id"]
    wait_ready(handle, hid)
    status, body = submit(handle, hid, make_tar_gz({"s.py": b"h"}))
    assert status == 202
    recon = session_ids_query(handle, [pub, hid])
    assert recon["total_submissions"] == 1
    rows = {r["session_id"]: r for r in recon["sessions"]}
    assert rows[hid]["submissions"] == 1
    assert rows[pub]["submissions"] == 0

    delete_session(handle, pub)
    delete_session(handle, hid)


def test_disconnect_and_4xx_no_double_count(service_factory, tmp_path):
    script = write_recorder_judge(tmp_path)
    handle = service_factory(
        judge_port=free_port_range(8),
        command=f"python3 {script}",
        submission_cap=_cap(10),
    )
    resp = create_session(handle, n_shards=2)
    sid = resp["session_id"]
    wait_ready(handle, sid)

    # 4xx pass-through: the worker rejects the tar; the relay counted it once
    # at accept and the answer passes through untouched (no retry).
    status, body = submit(handle, sid, b"BADTAR not a tar")
    assert status == 400, body
    assert json.loads(body)["error"] == "bad submission tar (recorder)"
    assert hidden_count(handle, sid) == 1
    # Each shard validated the same tar exactly once (no shard-level retry).
    status, merged = get_submissions(handle, sid)
    assert status == 200
    status, raw = get_archive(handle, sid)
    assert status == 200
    archive = json.loads(raw)
    for shard in ("0", "1"):
        assert archive["shard_payloads"][shard]["bad_submits"] == 1

    # Disconnect ambiguity: the client dies mid-submit; the server counted at
    # accept, exactly once, and the worker still completes the judging.
    slow = b"SLOW " + make_tar_gz({"s.py": b"slow"})
    try:
        submit(handle, sid, slow, timeout=2)
        raise AssertionError("the slow submit should have timed out client-side")
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
    wait_until(lambda: hidden_count(handle, sid) == 2, timeout=5,
               what="disconnect submit counted once")
    # Repeated reads while the worker judges: still exactly 2.
    for _ in range(3):
        get_submissions(handle, sid)
    assert hidden_count(handle, sid) == 2

    def _judged():
        status, merged = get_submissions(handle, sid)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    merged = wait_until(_judged, timeout=30, what="slow submission judged")
    assert merged["count"] == 1, "the bad tar left no entry; the slow one completed once"

    # A good submit increments by exactly one again.
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"good"}))
    assert status == 202
    assert hidden_count(handle, sid) == 3
    delete_session(handle, sid)


def test_restart_preserves_counts(service_factory, tmp_path):
    state_dir = tmp_path / "restarted"
    handle = service_factory(state_dir=state_dir, submission_cap=_cap(5))
    resp = create_session(handle)
    hid = resp["session_id"]
    wait_ready(handle, hid)
    resp = create_session(handle, instance_set="public")
    pub = resp["session_id"]
    wait_ready(handle, pub)
    for i in range(2):
        status, _ = submit(handle, hid, make_tar_gz({"s.py": str(i).encode()}))
        assert status == 202
    status, _ = submit(handle, pub, make_tar_gz({"s.py": b"p"}))
    assert status == 202
    before = session_ids_query(handle, [hid, pub])

    # Simulate a service restart: full app shutdown (destroys sessions),
    # then a fresh app over the SAME state_dir (journal replay).
    cleanup_app(handle)
    restarted = service_factory(state_dir=state_dir, submission_cap=_cap(5))

    after = session_ids_query(restarted, [hid, pub])
    assert after["total_submissions"] == before["total_submissions"] == 2
    rows = {r["session_id"]: r for r in after["sessions"]}
    assert rows[hid]["submissions"] == 2
    assert rows[hid]["present"] is True
    assert rows[pub]["submissions"] == 0
    assert rows[pub]["public_submissions"] == 1
