"""C4 acceptance: records after release.

The verifier pulls records after the model's session is released — the
archive (raw per-instance records) and the payload layer (creation payload,
submission bodies) must outlive the session. Covers (all over loopback HTTP):

- after DELETE: the ?session_ids= count is still reported, the archive is
  still readable, and the persisted payloads still download byte-identically
- hibernate (small grace via config): workers are recycled while metadata
  and the archive are kept; the archived history stays readable while
  hibernated; a wake (submit -> 503 provisioning -> ready) keeps the
  submission-id era continuous (ids never collide, never lost)
- service restart (fresh app over the same state_dir): the journal replays
  (counts identical) and the on-disk record layers stay readable
"""
from __future__ import annotations

import base64
import io
import json
import tarfile

from helpers_cde import (
    cleanup_app,
    create_session,
    delete_session,
    get_archive,
    get_payload,
    get_payload_submissions,
    get_submissions,
    hidden_count,
    service_factory,
    service_status,
    session_ids_query,
    session_status,
    sha256_hex,
    submit,
    synth,
    wait_ready,
    wait_session_status,
    wait_until,
    windows,
    make_tar_gz,
)

__all__ = ["synth", "windows", "service_factory"]


def test_records_readable_after_delete(service_factory):
    handle = service_factory()
    note = b"c4-creation-payload"
    resp = create_session(
        handle,
        judge_payload={"/tmp/cde_c4/note.txt": base64.b64encode(note).decode()},
    )
    sid = resp["session_id"]
    wait_ready(handle, sid)
    tunnels = handle.app["tunnels"]
    assert tunnels.is_connected(sid)
    assert tunnels.connected_count() == 1
    pack = make_tar_gz({"solver/main.py": b"print('c4')"})
    status, body = submit(handle, sid, pack)
    assert status == 202

    def _terminal():
        status, merged = get_submissions(handle, sid)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    wait_until(_terminal, timeout=30, what="submission judged")

    status, resp = delete_session(handle, sid)
    assert status == 200 and resp["stopped"] is True
    assert not tunnels.is_connected(sid)
    assert tunnels.connected_count() == 0
    assert service_status(handle)["live"]["tunnels"] == 0
    status, gone = session_status(handle, sid)
    assert status == 410 and gone["error_class"] == "terminal"

    # The count survives release (journal-driven reconciliation).
    assert hidden_count(handle, sid) == 1

    # The archive survives release.
    status, raw = get_archive(handle, sid)
    assert status == 200, raw
    archive = json.loads(raw)
    assert archive["session_id"] == sid
    assert archive["shard_payloads"]["0"]["submissions"][0]["records"]

    # The payload layer survives release: creation payload, submission index,
    # and the verbatim submission body.
    status, body = get_payload(handle, sid)
    assert status == 200
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as tf:
        assert tf.extractfile("tmp/cde_c4/note.txt").read() == note
    status, body = get_payload_submissions(handle, sid)
    assert status == 200 and json.loads(body)["submissions"] == [1]
    status, body = get_payload_submissions(handle, sid, 1)
    assert status == 200 and sha256_hex(body) == sha256_hex(pack)

    status, resp = delete_session(handle, sid)
    assert status == 200 and resp["stopped"] is False
    status, resp = delete_session(handle, "jsess-does-not-exist")
    assert status == 404 and resp["error"] == "unknown judge session jsess-does-not-exist"


def test_hibernate_wake_era_continuity(service_factory):
    handle = service_factory(hibernate_enabled=True, hibernate_grace_seconds=0.8)
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)

    status, body = submit(handle, sid, make_tar_gz({"s.py": b"one"}))
    assert status == 202 and json.loads(body)["submission"] == 0

    def _terminal():
        status, merged = get_submissions(handle, sid)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    wait_until(_terminal, timeout=30, what="first submission judged")

    # Delivered + quiet past the grace: the reaper hibernates — the worker
    # group is recycled, metadata/archive kept.
    wait_session_status(handle, sid, "hibernated", timeout=15)
    assert handle.adapter.long_lived_count() == 0, "hibernation recycles the workers"

    # The archived history is readable while hibernated (no wake needed).
    status, merged = get_submissions(handle, sid)
    assert status == 200
    assert merged["count"] == 1
    assert merged["submissions"][0]["submission"] == 0
    assert merged["submissions"][0]["status"] == "ok"

    # The wake path: a submit on a hibernated session short-circuits 503
    # (provisioning) and re-boots the group.
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"two"}))
    assert status == 503
    assert json.loads(body)["error_class"] == "transient"
    wait_ready(handle, sid)

    # Era continuity: the fresh worker restarted its local ids at 0, but the
    # client-facing sequence continues (no collision, no loss).
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"two"}))
    assert status == 202, body
    assert json.loads(body)["submission"] == 1, "post-wake ids continue the era"

    def _two():
        status, merged = get_submissions(handle, sid)
        if status == 200 and merged["count"] == 2 and all(
            e["status"] != "running" for e in merged["submissions"]
        ):
            return merged
        return None

    merged = wait_until(_two, timeout=30, what="post-wake submission judged")
    ids = [e["submission"] for e in merged["submissions"]]
    assert ids == [0, 1], "pre-hibernate and post-wake submissions both present"
    assert all(e["status"] == "ok" for e in merged["submissions"])

    status, raw = get_archive(handle, sid)
    assert status == 200
    archive = json.loads(raw)
    archived_ids = [e["submission"] for e in archive["shard_payloads"]["0"]["submissions"]]
    assert archived_ids == [0, 1]

    delete_session(handle, sid)


def test_restart_restores_counts_and_records(service_factory, tmp_path):
    state_dir = tmp_path / "restarted"
    handle = service_factory(state_dir=state_dir)
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)
    pack = make_tar_gz({"s.py": b"restart"})
    status, body = submit(handle, sid, pack)
    assert status == 202

    def _terminal():
        status, merged = get_submissions(handle, sid)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    wait_until(_terminal, timeout=30, what="submission judged")

    # Full shutdown (the sessions are destroyed), then a fresh app over the
    # same state_dir: the journal replays, the disk layers survive.
    cleanup_app(handle)
    restarted = service_factory(state_dir=state_dir)

    recon = session_ids_query(restarted, [sid])
    assert recon["total_submissions"] == 1
    assert recon["sessions"][0]["submissions"] == 1
    assert recon["sessions"][0]["present"] is True

    status, raw = get_archive(restarted, sid)
    assert status == 200, raw
    archive = json.loads(raw)
    assert archive["session_id"] == sid
    assert archive["shard_payloads"]["0"]["submissions"][0]["status"] == "ok"

    status, body = get_payload_submissions(restarted, sid)
    assert status == 200 and json.loads(body)["submissions"] == [1]
    status, body = get_payload_submissions(restarted, sid, 1)
    assert status == 200 and sha256_hex(body) == sha256_hex(pack)
