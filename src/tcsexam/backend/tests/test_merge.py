"""Five-number aggregation unit tests (no service, no workers).

Covers aggregate_submissions / aggregate_public / five_numbers semantics:
- five_numbers three-way and delta direction normalization (max problems
  sum(A-B), min problems sum(B-A), solve-type A,B in {0,1}; invalid counts
  worse, error counts failed)
- shard sums (plain addition, no weights)
- running propagation, non-ok status propagation, best by (better, delta)
- hidden-channel records: per-instance {instance, A, B, status, detail}
  (K stripped, B kept), concatenated and sorted by instance name, None while
  running, empty list for record-less entries, dead shards absent, detail
  text K-scrubbing (_scrub_k two layers: comparison parentheticals + the
  record's own K token, flag K in {0,1} untouched)
- dead shards: entries judged before dying keep archived records (history
  never rewritten backwards), absent slices count failed, per-shard
  judging-set size learning
- submission-level fold-ins: timeout/build_error count worse,
  judge_error/record-less ok count failed, unknown sizes count 0
- public channel: per-instance detail with B/K stripped, concatenation, dead
  shards; the excluded_records side channel (B==K / practice_no_anchors)
  merged with anchors stripped and reason kept; old workers without the
  field treated as empty; hidden aggregation untouched by the side channel
- _merged_submissions: all-shards-failed 502, archive write, hidden/public
  split, hidden response carries five numbers + K-stripped records while the
  archive keeps the raw records
"""
from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from tcsexam.backend.sessions import (
    JudgeSession,
    Shard,
    _hidden_record,
    _merged_submissions,
    _scrub_k,
    aggregate_public,
    aggregate_submissions,
    five_numbers,
)


def rec(i, A, B, K, status="ok", detail=""):
    return {"instance": i, "A": A, "B": B, "K": K, "status": status, "detail": detail}


def payload(subs):
    return {"submissions": subs, "count": len(subs)}


def sub(i, records, status="ok", detail="", ts=None, excluded_records=None):
    e = {"submission": i, "ts": ts if ts is not None else 100.0 + i,
         "status": status, "records": records, "detail": detail}
    if excluded_records is not None:
        e["excluded_records"] = excluded_records
    return e


def test_five_numbers_max_direction() -> None:
    f = five_numbers([rec("a", 5, 3, 10), rec("b", 3, 3, 10), rec("c", 1, 3, 10),
                      rec("d", None, 3, 10, "invalid"), rec("e", 7, 3, 10, "error")])
    assert (f["better"], f["equal"], f["worse"], f["failed"]) == (1, 1, 2, 1)
    assert f["delta"] == 0  # (5-3)+(3-3)+(1-3)


def test_five_numbers_min_direction() -> None:
    f = five_numbers([rec("a", 2, 5, 1), rec("b", 6, 5, 1), rec("c", 5, 5, 1)])
    assert (f["better"], f["worse"], f["equal"]) == (1, 1, 1)
    assert f["delta"] == 2  # (5-2)+(5-6)+(5-5)


def test_five_numbers_solve_type() -> None:
    # Solve-type problems: A,B in {0,1} — "I solved and the baseline didn't"
    # is better, "both solved or neither did" is equal.
    f = five_numbers([rec("a", 1, 0, 1), rec("b", 0, 0, 1)])
    assert (f["better"], f["equal"], f["worse"]) == (1, 1, 0)
    assert f["delta"] == 1


def test_shard_sums_add_up_without_weights() -> None:
    m = aggregate_submissions([
        payload([sub(0, [rec("a", 5, 3, 10), rec("b", 3, 3, 10)])]),
        payload([sub(0, [rec("c", 1, 3, 10)])]),
    ])
    e = m["submissions"][0]
    assert (e["better"], e["equal"], e["worse"], e["delta"], e["failed"]) == (1, 1, 1, 0, 0)
    assert m["best"] == 0
    assert e["failed_shards"] == 0 and m["failed_shards"] == 0


def test_shard_sums_match_whole_set_aggregation() -> None:
    whole = five_numbers([rec("a", 5, 3, 10)] * 6 + [rec("b", 3, 3, 10)] * 5 + [rec("c", 1, 3, 10)] * 5)
    m = aggregate_submissions([
        payload([sub(0, [rec("a", 5, 3, 10)] * 6)]),
        payload([sub(0, [rec("b", 3, 3, 10)] * 5)]),
        payload([sub(0, [rec("c", 1, 3, 10)] * 5)]),
    ])
    e = m["submissions"][0]
    assert all(e[k] == whole[k] for k in ("better", "equal", "worse", "delta", "failed"))


def test_running_propagates() -> None:
    m = aggregate_submissions([
        payload([sub(0, [rec("a", 5, 3, 10)])]),
        payload([sub(0, None, status="running")]),
    ])
    e = m["submissions"][0]
    assert e["status"] == "running" and e["better"] is None
    assert m["best"] is None


def test_missing_shard_entry_counts_as_running() -> None:
    m = aggregate_submissions([
        payload([sub(0, [rec("a", 5, 3, 10)]), sub(1, [rec("a", 5, 3, 10)])]),
        payload([sub(0, [rec("b", 3, 3, 10)])]),
    ])
    assert m["count"] == 2 and m["submissions"][1]["status"] == "running"


def test_non_ok_status_propagates() -> None:
    m = aggregate_submissions([
        payload([sub(0, [rec("a", 5, 3, 10)])]),
        payload([sub(0, None, status="timeout")]),
    ])
    assert m["submissions"][0]["status"] == "timeout"


def test_best_lexicographic_better_then_delta() -> None:
    m = aggregate_submissions([
        payload([
            sub(0, [rec("a", 5, 3, 10)]),                # better=1 delta=2
            sub(1, [rec("a", 8, 3, 10), rec("b", 9, 3, 10)]),  # better=2 delta=11
            sub(2, [rec("a", 6, 3, 10), rec("b", 4, 3, 10)]),  # better=2 delta=4
        ]),
    ])
    assert m["best"] == 1
    m = aggregate_submissions([
        payload([
            sub(0, [rec("a", 6, 3, 10), rec("b", 4, 3, 10)]),  # better=2 delta=4
            sub(1, [rec("a", 8, 3, 10), rec("b", 9, 3, 10)]),  # better=2 delta=11
        ]),
    ])
    assert m["best"] == 1


def test_dead_shard_keeps_archived_records_absent_counts_failed() -> None:
    cache: dict[int, int] = {}
    snap1 = payload([sub(0, [rec("b", 3, 3, 10)])])  # shard 1 judged only sub0 before dying
    m = aggregate_submissions(
        [
            payload([sub(0, [rec("a", 5, 3, 10)]), sub(1, [rec("a", 9, 3, 10)])]),
            snap1,
        ],
        n_shards=2,
        failed={1: "shard tunnel down"},
        size_cache=cache,
    )
    e0, e1 = m["submissions"]
    assert e0["failed"] == 0 and e0["failed_shards"] == 0 and e0["better"] == 1
    assert e1["failed"] == 1 and e1["failed_shards"] == 1 and e1["better"] == 1 and e1["delta"] == 6
    assert cache.get(1) == 1  # size learned from the snapshot
    assert m["failed_shards"] == 1


def test_history_never_rewritten_backwards() -> None:
    m_before = aggregate_submissions([
        payload([sub(0, [rec("a", 5, 3, 10), rec("x", 4, 4, 9)])]),
        payload([sub(0, [rec("b", 3, 3, 10)])]),
    ])
    m_after = aggregate_submissions(
        [
            payload([sub(0, [rec("a", 5, 3, 10), rec("x", 4, 4, 9)]), sub(1, [rec("a", 9, 3, 10)])]),
            payload([sub(0, [rec("b", 3, 3, 10)])]),
        ],
        n_shards=2,
        failed={1: "dead"},
        size_cache={},
    )
    keys = ("better", "equal", "worse", "delta", "failed", "status")
    assert all(m_before["submissions"][0][k] == m_after["submissions"][0][k] for k in keys)


def test_submission_level_fold_ins() -> None:
    m = aggregate_submissions([
        payload([
            sub(0, None, status="timeout"),
            sub(1, None, status="judge_error"),
            sub(2, None, status="ok", detail="build_error"),
            sub(3, None, status="ok", detail="reward JSON carries no per-instance records"),
            sub(4, [rec("a", 3, 3, 10)]),  # shard 0 size=1 learned here
        ]),
        payload([
            sub(0, [rec("b", 3, 3, 10)]), sub(1, [rec("b", 3, 3, 10)]),
            sub(2, [rec("b", 3, 3, 10)]), sub(3, [rec("b", 3, 3, 10)]),
            sub(4, [rec("b", 3, 3, 10)]),
        ]),
    ])
    es = m["submissions"]
    assert es[0]["worse"] == 1 and es[0]["failed"] == 0, "timeout counts worse (the model's own overrun)"
    assert es[1]["failed"] == 1 and es[1]["worse"] == 0, "judge_error counts failed (infrastructure)"
    assert es[2]["worse"] == 1 and es[2]["failed"] == 0, "build_error counts worse (model crash class)"
    assert es[3]["failed"] == 1 and es[3]["worse"] == 0, "record-less ok counts failed (pipeline regression)"


def test_unknown_size_counts_zero() -> None:
    m = aggregate_submissions([payload([sub(0, None, status="timeout")])], size_cache={})
    assert m["submissions"][0]["worse"] == 0, "unknown judging-set size: under-count, never mis-count"


def test_never_reported_shard_estimated_from_known_mean() -> None:
    m = aggregate_submissions(
        [
            payload([sub(0, [rec("a", 5, 3, 10)] * 6), sub(1, [rec("a", 5, 3, 10)] * 6)]),
            payload([sub(0, [rec("b", 3, 3, 10)] * 5), sub(1, [rec("b", 3, 3, 10)] * 5)]),
            None,  # shard 2 never reported
        ],
        n_shards=3,
        failed={2: "dead"},
        size_cache={},
    )
    e = m["submissions"][1]
    # shard 2 absent from sub1: estimated size = round((6+5)/2) = 6 (round-half-even)
    assert e["failed"] == 6


def test_single_shard_omits_failed_shards_keys() -> None:
    m = aggregate_submissions([payload([sub(0, [rec("a", 5, 3, 10)])])])
    assert "failed_shards" not in m["submissions"][0]
    assert "failed_shards" not in m


# --------------------------------------------------------------------------- #
# Hidden-channel records: strip K keep B, concatenation
# --------------------------------------------------------------------------- #
def test_hidden_records_strip_k_keep_b_sorted() -> None:
    m = aggregate_submissions([
        payload([sub(0, [rec("b-inst", 5, 3, 10),
                         rec("a-inst", None, 3, 10, "invalid", "invalid solution (cycle remains)")])]),
        payload([sub(0, [rec("c-inst", 2, 3, 10)])]),
    ])
    e = m["submissions"][0]
    assert [r["instance"] for r in e["records"]] == ["a-inst", "b-inst", "c-inst"]
    assert all(set(r) == {"instance", "A", "B", "status", "detail"} for r in e["records"])
    assert [r["B"] for r in e["records"]] == [3, 3, 3]
    assert (e["better"], e["equal"], e["worse"], e["delta"], e["failed"]) == (1, 0, 2, 1, 0)


def test_hidden_records_running_none_recordless_empty() -> None:
    m = aggregate_submissions([payload([sub(0, None, status="running"), sub(1, None, status="timeout")])])
    assert m["submissions"][0]["status"] == "running" and m["submissions"][0]["records"] is None
    assert m["submissions"][1]["records"] == []


def test_hidden_records_dead_shard_absent_from_later_entries() -> None:
    m = aggregate_submissions(
        [
            payload([sub(0, [rec("a", 5, 3, 10)]), sub(1, [rec("a", 9, 3, 10)])]),
            payload([sub(0, [rec("z", 1, 3, 10)])]),
        ],
        n_shards=2,
        failed={1: "dead"},
        size_cache={},
    )
    e0, e1 = m["submissions"]
    assert [r["instance"] for r in e0["records"]] == ["a", "z"] and e0["failed_shards"] == 0
    assert [r["instance"] for r in e1["records"]] == ["a"] and e1["failed_shards"] == 1


def test_hidden_records_history_not_rewritten() -> None:
    m_before = aggregate_submissions([
        payload([sub(0, [rec("a", 5, 3, 10)])]),
        payload([sub(0, [rec("z", 1, 3, 10)])]),
    ])
    m_after = aggregate_submissions(
        [
            payload([sub(0, [rec("a", 5, 3, 10)]), sub(1, [rec("a", 9, 3, 10)])]),
            payload([sub(0, [rec("z", 1, 3, 10)])]),
        ],
        n_shards=2,
        failed={1: "dead"},
        size_cache={},
    )
    assert m_before["submissions"][0]["records"] == m_after["submissions"][0]["records"]


def test_scrub_k_comparison_parentheticals() -> None:
    assert _scrub_k("valid but above optimum (15 > 12)", 1) == "valid but above optimum (? > ?)"
    assert _scrub_k("VALID COVER BELOW K (11 < 12); re-check the K table", 1) == \
        "VALID COVER BELOW K (? < ?); re-check the K table"
    assert _scrub_k("edge 3 -> 5 duplicated", 7) == "edge 3 -> 5 duplicated"
    assert _scrub_k("ok (matches reference)", 10) == "ok (matches reference)"


def test_scrub_k_own_k_token() -> None:
    assert _scrub_k("reference says 263 here", 263) == "reference says ? here"
    assert _scrub_k("timeout after 1200s", 12) == "timeout after 1200s"
    assert _scrub_k("code 26 and 263", 263) == "code 26 and ?"
    assert _scrub_k("solver exited with code 1", 1) == "solver exited with code 1"


def test_hidden_record_five_keys_and_scrubbed_detail() -> None:
    h = _hidden_record(rec("x", 1, 0, 1, "invalid", "valid but above optimum (15 > 12)"))
    assert set(h) == {"instance", "A", "B", "status", "detail"}
    assert h == {"instance": "x", "A": 1, "B": 0, "status": "invalid",
                 "detail": "valid but above optimum (? > ?)"}


# --------------------------------------------------------------------------- #
# Public channel
# --------------------------------------------------------------------------- #
def test_public_records_strip_anchors_sorted() -> None:
    m = aggregate_public([
        payload([sub(0, [rec("b-inst", 5, 3, 10), rec("a-inst", None, 3, 10, "invalid")])]),
        payload([sub(0, [rec("c-inst", 2, 3, 10)])]),
    ])
    e = m["submissions"][0]
    assert [r["instance"] for r in e["records"]] == ["a-inst", "b-inst", "c-inst"]
    assert all(set(r.keys()) == {"instance", "A", "status", "detail"} for r in e["records"])
    assert "better" not in e and "best" not in m


def test_public_dead_shard_absent_slices() -> None:
    m = aggregate_public(
        [
            payload([sub(0, [rec("a", 5, 3, 10)]), sub(1, [rec("a", 6, 3, 10)])]),
            payload([sub(0, [rec("z", 1, 3, 10)])]),
        ],
        n_shards=2,
        failed={1: "dead"},
    )
    e0, e1 = m["submissions"]
    assert [r["instance"] for r in e0["records"]] == ["a", "z"] and e0["failed_shards"] == 0
    assert [r["instance"] for r in e1["records"]] == ["a"] and e1["failed_shards"] == 1


def test_public_running_and_timeout_records_null() -> None:
    m = aggregate_public([
        payload([sub(0, [rec("a", 5, 3, 10)]), sub(1, None, status="timeout")]),
        payload([sub(0, None, status="running"), sub(1, [rec("z", 1, 3, 10)])]),
    ])
    e0, e1 = m["submissions"]
    assert e0["status"] == "running" and e0["records"] is None
    assert e1["status"] == "timeout" and e1["records"] is None


def test_public_side_channel_excluded_records_merged() -> None:
    m = aggregate_public([
        payload([sub(0, [rec("b-inst", 5, 3, 10)],
                    excluded_records=[
                        dict(rec("a-flat", 2, 3, 3), reason="b_equals_k"),
                        dict(rec("d-flat", None, 7, 7, "invalid", "timeout after 300.0s"),
                             reason="b_equals_k"),
                    ])]),
        payload([sub(0, [rec("e-inst", 1, 3, 10)],
                    excluded_records=[
                        dict(rec("c-prac", 42, None, None), reason="practice_no_anchors"),
                    ])]),
    ])
    e = m["submissions"][0]
    assert [r["instance"] for r in e["records"]] == ["a-flat", "b-inst", "c-prac", "d-flat", "e-inst"]
    side = {r["instance"]: r for r in e["records"] if "reason" in r}
    assert side["a-flat"] == {"instance": "a-flat", "A": 2, "status": "ok", "detail": "",
                              "reason": "b_equals_k"}
    assert side["c-prac"]["reason"] == "practice_no_anchors"
    assert side["c-prac"]["A"] == 42 and "B" not in side["c-prac"] and "K" not in side["c-prac"]
    assert side["d-flat"]["status"] == "invalid"
    assert side["d-flat"]["detail"] == "timeout after 300.0s"
    assert {r["instance"] for r in e["records"] if "reason" not in r} == {"b-inst", "e-inst"}


def test_public_side_channel_old_workers_treated_as_empty() -> None:
    m = aggregate_public([
        payload([sub(0, [rec("a", 5, 3, 10)])]),  # old worker: no side-channel field
        payload([sub(0, [rec("b", 1, 3, 10)],
                    excluded_records=[dict(rec("c", 2, 3, 3), reason="b_equals_k")])]),
    ])
    e = m["submissions"][0]
    assert [r["instance"] for r in e["records"]] == ["a", "b", "c"]
    assert e["records"][2]["reason"] == "b_equals_k"


def test_hidden_channel_ignores_the_side_channel() -> None:
    m = aggregate_submissions([
        payload([sub(0, [rec("a", 5, 3, 10)],
                    excluded_records=[dict(rec("x-flat", 9, 3, 3), reason="b_equals_k")])]),
        payload([sub(0, [rec("b", 3, 3, 10)],
                    excluded_records=[dict(rec("y-prac", 1, None, None),
                                           reason="practice_no_anchors")])]),
    ])
    e = m["submissions"][0]
    assert (e["better"], e["equal"], e["worse"], e["delta"], e["failed"]) == (1, 1, 0, 2, 0)
    assert [r["instance"] for r in e["records"]] == ["a", "b"]
    assert m["best"] == 0


# --------------------------------------------------------------------------- #
# _merged_submissions endpoint level: all-failed 502, archive write,
# hidden/public split
# --------------------------------------------------------------------------- #
class _FakeTunnels:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    async def call(self, app_name, method, path, body=b""):
        self.calls.append((app_name, method, path))
        return self.reply


def _fake_store(tunnels, state_dir=""):
    return SimpleNamespace(
        _tunnels=tunnels,
        _fanout_sem=asyncio.Semaphore(64),
        cfg=SimpleNamespace(shard_call_timeout_seconds=2.0),
        _config=SimpleNamespace(state_dir=state_dir),
        # _mark_shard_failed calls the store's all-shards-dead check.
        _fail_session_if_all_shards_dead=lambda session: None,
    )


def _session(failed, instance_set="hidden"):
    s = JudgeSession(
        session_id="jsess-fake", image="mock://x", created=0.0, last_active=0.0, expires=0.0,
        shards=[Shard(0, "jsess-fake-s0"), Shard(1, "jsess-fake-s1")],
        instance_set=instance_set,
    )
    s.failed_shards.update(failed)
    return s


def test_merged_submissions_all_shards_failed_is_502() -> None:
    resp = asyncio.run(_merged_submissions(_fake_store(_FakeTunnels(None)), _session({0: "d", 1: "d"})))
    assert resp.status == 502
    assert b"please try again" in resp.body


def test_merged_submissions_live_shards_all_5xx_marked_failed() -> None:
    tun = _FakeTunnels((502, {}, b"502 Bad Gateway: no live tunnel (please try again)"))
    sess = _session({})
    resp = asyncio.run(_merged_submissions(_fake_store(tun), sess))
    assert resp.status == 502
    assert sess.failed_shards.get(0, "") != "" and sess.failed_shards.get(1, "") != ""


def test_merged_submissions_hidden_happy_path_and_archive() -> None:
    worker_payload = payload([sub(0, [rec("inst", 5, 3, 10)])])
    tun = _FakeTunnels((200, {}, json.dumps(worker_payload).encode()))
    sess = _session({})
    with tempfile.TemporaryDirectory() as td:
        resp = asyncio.run(_merged_submissions(_fake_store(tun, state_dir=td), sess))
        body = json.loads(resp.body)
        assert resp.status == 200 and body["submissions"][0]["better"] == 2
        assert body["submissions"][0]["records"] == [
            {"instance": "inst", "A": 5, "B": 3, "status": "ok", "detail": ""},
            {"instance": "inst", "A": 5, "B": 3, "status": "ok", "detail": ""},
        ]
        assert set(sess.shard_payloads) == {0, 1}
        assert sess.shard_sizes == {0: 1, 1: 1}
        archive = Path(td) / "judge_archive" / "jsess-fake.json"
        assert archive.exists()
        arc = json.loads(archive.read_text())
        assert arc["n_shards"] == 2 and arc["instance_set"] == "hidden"
        assert set(arc["shard_payloads"]) == {"0", "1"}
        assert arc["shard_payloads"]["0"]["submissions"][0]["records"][0]["B"] == 3
        assert arc["failed_shards"] == {}
        # The archive keeps the raw records (anchors intact — the ingredient layer).
        assert arc["shard_payloads"]["1"]["submissions"][0]["records"][0]["K"] == 10


def test_merged_submissions_hidden_scrubs_k_from_response_not_archive() -> None:
    leak_payload = payload([sub(0, [rec("inst", 0, 0, 1, "invalid", "valid but above optimum (15 > 12)")])])
    tun = _FakeTunnels((200, {}, json.dumps(leak_payload).encode()))
    sess = _session({})
    with tempfile.TemporaryDirectory() as td:
        resp = asyncio.run(_merged_submissions(_fake_store(tun, state_dir=td), sess))
        body = json.loads(resp.body)
        r = body["submissions"][0]["records"][0]
        assert r["detail"] == "valid but above optimum (? > ?)"
        assert set(r) == {"instance", "A", "B", "status", "detail"}
        assert "12" not in r["detail"] and "15" not in r["detail"]
        arc = json.loads((Path(td) / "judge_archive" / "jsess-fake.json").read_text())
        assert arc["shard_payloads"]["0"]["submissions"][0]["records"][0]["detail"] == \
            "valid but above optimum (15 > 12)"


def test_merged_submissions_public_split() -> None:
    worker_payload = payload([sub(0, [rec("inst", 5, 3, 10)])])
    tun = _FakeTunnels((200, {}, json.dumps(worker_payload).encode()))
    sess = _session({}, instance_set="public")
    with tempfile.TemporaryDirectory() as td:
        resp = asyncio.run(_merged_submissions(_fake_store(tun, state_dir=td), sess))
        body = json.loads(resp.body)
        recs = body["submissions"][0]["records"]
        assert recs is not None and all(set(r.keys()) == {"instance", "A", "status", "detail"} for r in recs)
        assert "best" not in body
        arc = json.loads((Path(td) / "judge_archive" / "jsess-fake.json").read_text())
        assert arc["instance_set"] == "public"
        assert arc["shard_payloads"]["0"]["submissions"][0]["records"][0]["B"] == 3


def test_merged_submissions_public_side_channel() -> None:
    side_payload = payload([
        sub(0, [rec("inst", 5, 3, 10)],
            excluded_records=[
                dict(rec("flat", 2, 3, 3), reason="b_equals_k"),
                dict(rec("prac", 42, None, None), reason="practice_no_anchors"),
            ]),
    ])
    tun = _FakeTunnels((200, {}, json.dumps(side_payload).encode()))
    sess = _session({}, instance_set="public")
    with tempfile.TemporaryDirectory() as td:
        resp = asyncio.run(_merged_submissions(_fake_store(tun, state_dir=td), sess))
        body = json.loads(resp.body)
        recs = body["submissions"][0]["records"]
        assert [r["instance"] for r in recs] == ["flat", "flat", "inst", "inst", "prac", "prac"]
        assert all("B" not in r and "K" not in r for r in recs)
        assert [r.get("reason") for r in recs] == [
            "b_equals_k", "b_equals_k", None, None,
            "practice_no_anchors", "practice_no_anchors",
        ]
        arc = json.loads((Path(td) / "judge_archive" / "jsess-fake.json").read_text())
        entry = arc["shard_payloads"]["0"]["submissions"][0]
        assert entry["excluded_records"][0]["B"] == 3
        assert entry["excluded_records"][1]["reason"] == "practice_no_anchors"


def test_execution_cleanup_failure_archives_records_and_stops_real_worker_path():
    worker_payload = payload([sub(0, [rec('inst', 5, 3, 10)]),
                              sub(1, None, status='judge_error')])
    worker_payload['worker_error'] = 'descendant cleanup deadline exceeded'
    stopped = []
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / 'judge_archive/jsess-fake.json'
        class Executor:
            async def stop_app(self, app_name):
                # The teardown path must retain records before removing workers.
                saved = json.loads(archive.read_text())
                assert saved['shard_payloads']['0']['submissions'][0]['records']
                assert saved['shard_payloads']['0']['submissions'][1]['status'] == 'judge_error'
                stopped.append(app_name)
        async def scenario():
            store = _fake_store(_FakeTunnels((200, {}, json.dumps(worker_payload).encode())), directory)
            store._executor = Executor()
            session = _session({})
            response = await _merged_submissions(store, session)
            await asyncio.sleep(0)
            assert set(session.failed_shards) == {0, 1}
            assert sorted(stopped) == ['jsess-fake-s0', 'jsess-fake-s1']
            result = json.loads(response.body)
            assert result['submissions'][1]['status'] == 'judge_error'
            assert result['submissions'][1]['worse'] == 0
            assert result['submissions'][1]['failed'] == 2
        asyncio.run(scenario())
