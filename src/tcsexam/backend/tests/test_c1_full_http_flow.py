"""C1 acceptance: full HTTP flow end-to-end.

One sharded session driven ONLY over loopback HTTP (no internal function
calls): create (202, async) -> poll status to ready -> POST the solver tar.gz
(application/gzip) -> integer submission id -> poll GET submissions to the
terminal aggregated shape (five numbers + K-stripped records) -> archive with
the X-TCSEXAM-Archive-Token (instance_set / n_shards / shard_payloads /
failed_shards) -> payload endpoints (creation payload, submission index,
original pack download, byte-identical digest) -> DELETE -> the
?session_ids= reconciliation query still reports the accepted submission.

Infra: real backend app + LocalProcessAdapter (real agent subprocesses
dialing the tunnel back) + the synthetic judge worker. helpers_cde.py owns
the harness; this file holds the scenario.
"""
from __future__ import annotations

import base64
import io
import json
import tarfile

from helpers_cde import (
    ARCHIVE_TOKEN,
    create_session,
    delete_session,
    get_archive,
    get_payload,
    get_payload_submissions,
    get_submissions,
    make_tar_gz,
    service_factory,
    session_ids_query,
    session_status,
    sha256_hex,
    submit,
    synth,
    wait_ready,
    wait_until,
    windows,
)

# Re-export the imported fixtures so pytest registers them for this module.
__all__ = ["synth", "windows", "service_factory"]


def test_full_http_flow(service_factory):
    handle = service_factory()

    # 1. Create (asynchronous): 202 with status provisioning.
    #    (The judge_payload path is worker-absolute; the local adapter has no
    #    filesystem isolation, so the test payload lands under /tmp.)
    note = b"override-note-for-c1"
    resp = create_session(
        handle,
        n_shards=2,
        judge_payload={"/tmp/cde_c1/note.txt": base64.b64encode(note).decode()},
    )
    sid = resp["session_id"]
    assert sid.startswith("jsess-")
    assert resp["status"] == "provisioning"
    assert resp["n_shards"] == 2
    assert resp["instance_set"] == "hidden"

    # 2. Poll the status endpoint over HTTP until ready.
    ready = wait_ready(handle, sid)
    assert ready["n_shards"] == 2
    assert ready["live_shards"] == 2
    assert ready["failed_shards"] == 0
    assert ready["tunnel_connected"] is True

    # 3. Submit the raw solver tar.gz (application/gzip).
    pack = make_tar_gz({"solver/main.py": b"print('c1')", "solver/data.bin": b"\x00\x01\x02"})
    status, body = submit(handle, sid, pack)
    assert status == 202, body
    ack = json.loads(body.decode())
    assert ack["submission"] == 0 and isinstance(ack["submission"], int)
    assert ack["status"] == "running"
    assert ack["shards"] == 2

    # 4. Poll GET submissions to the terminal aggregated shape.
    def _terminal():
        st, merged = get_submissions(handle, sid)
        if st == 200 and merged["submissions"] and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    merged = wait_until(_terminal, timeout=30, what="terminal merged submission")
    assert merged["count"] == 1
    assert merged["shards"] == 2
    assert merged["failed_shards"] == 0
    assert merged["best"] == 0
    entry = merged["submissions"][0]
    assert entry["submission"] == 0
    assert entry["status"] == "ok"
    assert entry["failed_shards"] == 0
    # Five numbers: two live shards x 1 instance each (A=2 > B=1, MAX).
    assert (entry["better"], entry["equal"], entry["worse"]) == (2, 0, 0)
    assert entry["delta"] == 2
    assert entry["failed"] == 0
    # Per-instance records: K stripped structurally, B kept, sorted by name.
    assert len(entry["records"]) == 2
    for rec in entry["records"]:
        assert set(rec) == {"instance", "A", "B", "status", "detail"}
        assert rec["A"] == 2 and rec["B"] == 1 and rec["status"] == "ok"
    names = [rec["instance"] for rec in entry["records"]]
    assert names == sorted(names) and len(set(names)) == 2

    # 5. Archive (verifier credential): the raw-record layer.
    status, raw = get_archive(handle, sid, token=ARCHIVE_TOKEN)
    assert status == 200, raw
    archive = json.loads(raw.decode())
    assert archive["session_id"] == sid
    assert archive["instance_set"] == "hidden"
    assert archive["n_shards"] == 2
    assert archive["failed_shards"] == {}
    assert sorted(archive["shard_payloads"]) == ["0", "1"]
    for shard_payload in archive["shard_payloads"].values():
        sub0 = shard_payload["submissions"][0]
        # The raw archive keeps the anchors (K) and the pack digest.
        assert sub0["records"][0]["K"] == 4
        assert sub0["pack_sha256"] == sha256_hex(pack)

    # 6. Creation payload download: the judge_payload repacked as tar.gz.
    status, body = get_payload(handle, sid)
    assert status == 200
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as tf:
        assert tf.extractfile("tmp/cde_c1/note.txt").read() == note

    # 7./8. Submission payload index + verbatim download of the original pack.
    status, body = get_payload_submissions(handle, sid)
    assert status == 200
    index = json.loads(body.decode())
    assert index["session_id"] == sid
    assert index["submissions"] == [1]
    status, body = get_payload_submissions(handle, sid, 1)
    assert status == 200
    assert sha256_hex(body) == sha256_hex(pack), "downloaded pack must be byte-identical"

    # 9. DELETE (idempotent).
    status, resp = delete_session(handle, sid)
    assert status == 200 and resp["stopped"] is True

    # 10. The reconciliation query still reports the accepted submission.
    recon = session_ids_query(handle, [sid])
    assert recon["total_submissions"] == 1
    row = recon["sessions"][0]
    assert row["session_id"] == sid
    assert row["submissions"] == 1
    assert row["present"] is True

    # 11. Destroyed sessions answer 410 (terminal), never a hanging 404.
    status, body = session_status(handle, sid)
    assert status == 410 and body["error_class"] == "terminal"
