#!/usr/bin/env python3
"""Serve one task's existing judging pipeline over HTTP.

``POST /submit`` accepts a tar or tar.gz containing the submitted ``/app``
tree. Each submission is unpacked and judged once, in arrival order.
``GET /submissions`` returns raw per-instance results, and ``GET /health``
is the readiness check. The service computes final scores separately.

The task supplies ``TESTS_DIR`` and ``JUDGE_CMD``. The worker supplies a new
``REWARD_PATH`` for every submission and stops the whole process group when
``JUDGE_TIMEOUT`` expires. ``INSTANCE_SET=public`` selects the separate
public instance tree; the default is ``hidden``. Any shard assignment in
``INSTANCE_SHARD`` is passed to the task checker, which owns the actual
selection and its budget semantics. Tasks with one shared time pool must not
be split.

Only Python's standard library is required.
"""
from __future__ import annotations

import io
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("PORT", "8082"))
BIND_HOST = os.environ.get("BIND_HOST", "127.0.0.1")
TESTS_DIR = os.environ.get("TESTS_DIR", "/tests")
APP_DIR = os.environ.get("APP_DIR", "/app")
WORK_DIR = Path(os.environ.get("WORK_DIR", "/work"))
JUDGE_CMD = os.environ.get("JUDGE_CMD", "").strip()  # default: bash $TESTS_DIR/test.sh
JUDGE_TIMEOUT = float(os.environ.get("JUDGE_TIMEOUT", "3600"))
MAX_BODY = 256 * 1024 * 1024
INSTANCE_SET = os.environ.get("INSTANCE_SET", "hidden").strip() or "hidden"

_STATE_LOCK = threading.Lock()
_QUEUE: "queue.SimpleQueue[int]" = None  # set in main

_STATE: dict = {
    "next_id": 0,
    "submissions": [],  # {submission, ts, status, records, detail}
}


def _log(msg: str) -> None:
    print(f"[judge_worker {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _persist() -> None:
    try:
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        tmp = WORK_DIR / "submissions.json.tmp"
        tmp.write_text(json.dumps(_STATE["submissions"], indent=1))
        tmp.replace(WORK_DIR / "submissions.json")
    except OSError:
        pass


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _build_records(out: dict):
    """Return scoring records, excluded names, complete excluded records and a note.

    A valid result has numeric anchors and an ``ok`` status or a verdict.
    Invalid submissions have no numeric result. Missing anchors, status or
    result indicate a judging error. A checker may explicitly mark a missing
    baseline with ``anchor_baseline_unsolved``; that case retains the result
    and is excluded by score aggregation.

    Equal baseline and known-best values stay in excluded_records, outside the hidden mean. Public feedback reports their computed result. The
    ``all-keys-solve-rate-260917`` format keeps them for solve-rate scoring.
    A reward without a per-instance table returns no records and a note.
    """
    keep_b_equals_k = (
        out.get("scoring_caliber") == "all-keys-solve-rate-260917"
    )
    table = None
    for key in ("per_instance", "per_instance_detail"):
        candidate = out.get(key)
        if isinstance(candidate, dict) and candidate:
            table = candidate
            break
    if table is None:
        return None, [], [], "reward JSON carries no per-instance records (per_instance/per_instance_detail)"
    records = []
    excluded = []
    excluded_records = []
    for name in sorted(table):
        rec = table[name]
        if not isinstance(rec, dict):
            records.append(
                {"instance": name, "A": None, "B": None, "K": None,
                 "status": "error", "detail": "malformed per-instance record"}
            )
            continue
        a, b, k = rec.get("A"), rec.get("B"), rec.get("K")
        label = str(rec.get("status") or rec.get("verdict") or "")
        extra = str(rec.get("detail") or "")
        detail = f"{label}: {extra}" if extra and extra != label else label
        if not _is_num(b) or not _is_num(k):
            if (b is None and _is_num(k)
                    and rec.get("anchor_baseline_unsolved") is True):
                entry = _normalize_status(name, rec, a, None, k, detail)
                entry["anchor_baseline_unsolved"] = True
                records.append(entry)
            else:
                records.append(
                    {"instance": name, "A": a if _is_num(a) else None,
                     "B": b if _is_num(b) else None, "K": k if _is_num(k) else None,
                     "status": "error", "detail": detail or "record carries no numeric anchors"}
                )
            continue
        entry = _normalize_status(name, rec, a, b, k, detail)
        if float(b) == float(k) and not keep_b_equals_k:
            excluded.append(name)
            entry["reason"] = "b_equals_k"
            excluded_records.append(entry)
        else:
            records.append(entry)
    return records, excluded, excluded_records, ""


def _normalize_status(name: str, rec: dict, a, b, k, detail: str) -> dict:
    """One per-instance record's status spine (design 260910 §4.1), shared
    by the ``records`` path and the ``excluded_records`` side channel."""
    if rec.get("status") is None and rec.get("verdict") is None:
        return {"instance": name, "A": a if _is_num(a) else None, "B": b, "K": k,
                "status": "error", "detail": "record carries no status/verdict"}
    if rec.get("status") is not None and not str(rec.get("status")).startswith("ok"):
        # Objective-problem failure strings ("invalid solution (...)",
        # "timeout after Ns", crash markers): the model's own fault.
        # Accept any "ok..." prefix — scorings legitimately write
        # "ok (matches reference)"-style status with a reason suffix
        # (260911 iccma: every solved instance was misread as invalid).
        return {"instance": name, "A": None, "B": b, "K": k,
                "status": "invalid", "detail": detail}
    if not _is_num(a):
        return {"instance": name, "A": None, "B": b, "K": k,
                "status": "error", "detail": detail or "ok record without a numeric A"}
    return {"instance": name, "A": a, "B": b, "K": k,
            "status": "ok", "detail": detail}


def _safe_unpack(data: bytes, dest: Path) -> None:
    """Unpack a (gzipped) tar into dest, rejecting path escapes."""
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
        for member in tar:
            name = member.name
            if name.startswith("/") or ".." in Path(name).parts or member.isdev():
                raise ValueError(f"unsafe tar member: {name!r}")
            tar.extract(member, dest, filter="data")


def _judge_one(sub_id: int) -> None:
    """Run the full judging pipeline for one submission (background thread)."""
    sub_dir = WORK_DIR / "submissions" / str(sub_id)
    entry = _STATE["submissions"][sub_id]
    try:
        # Reset /app to EXACTLY the submitted tree (no leftovers from the
        # previous submission, no baseline files the image shipped).
        app = Path(APP_DIR)
        staging = sub_dir / "app"
        shutil.rmtree(app, ignore_errors=True)
        shutil.copytree(staging, app, symlinks=True)

        reward_path = sub_dir / "reward.json"
        env = dict(os.environ)
        env["REWARD_PATH"] = str(reward_path)
        cmd = JUDGE_CMD or f"bash {TESTS_DIR}/test.sh"
        log_path = sub_dir / "judge.log"
        with open(log_path, "wb") as log:
            proc = subprocess.Popen(
                cmd, shell=True, env=env,
                stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,  # own process group: the timeout
                # path kills the WHOLE group (solver + anything it forks)
            )
            try:
                rc = proc.wait(timeout=JUDGE_TIMEOUT)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                # The solver did not let the pipeline finish — the model's
                # own fault; the service folds the slice's instances into
                # ``worse`` (design 260910 §3.1).
                entry.update(status="timeout", records=None, detail=f"judging exceeded {JUDGE_TIMEOUT:g}s")
                return
        if not reward_path.exists():
            tail = log_path.read_text(errors="replace")[-300:]
            entry.update(
                status="judge_error", records=None,
                detail=f"judge exited rc={rc} without a reward file",
            )
            _log(f"submission {sub_id}: no reward file (rc={rc}); judge.log tail: {tail}")
            return
        out = json.loads(reward_path.read_text())
        if out.get("build_error"):
            # A build failure is the model's own crash class: no per-instance
            # data exists, and the service folds the slice into ``worse``.
            entry.update(status="ok", records=None, detail="build_error")
        else:
            records, excluded, excluded_records, note = _build_records(out)
            entry.update(status="ok", records=records, detail=note)
            if excluded:
                entry["excluded_no_signal"] = excluded
            if excluded_records:
                entry["excluded_records"] = excluded_records
            if records is None:
                _log(f"submission {sub_id}: {note} — judging-pipeline regression")
    except Exception as exc:  # noqa: BLE001 - one bad submission must not kill the worker
        _log(f"submission {sub_id} judging crashed:\n{traceback.format_exc()}")
        entry.update(status="judge_error", records=None, detail=f"{type(exc).__name__}: {exc}"[:200])
    finally:
        _persist()
        n_records = len(entry["records"]) if entry.get("records") is not None else "-"
        _log(f"submission {sub_id} done: status={entry['status']} records={n_records}")


def _queue_loop() -> None:
    while True:
        sub_id = _QUEUE.get()
        _judge_one(sub_id)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # quieter logs
        _log("http " + (fmt % args))

    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if self.path == "/submissions":
            with _STATE_LOCK:
                subs = [dict(s) for s in _STATE["submissions"]]
            self._send_json(
                200,
                {
                    "submissions": subs,
                    "count": len(subs),
                },
            )
            return
        self._send_json(404, {"error": f"unknown path {self.path}"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/submit":
            self._send_json(404, {"error": f"unknown path {self.path}"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self._send_json(400, {"error": "empty body: expected a (gzipped) tar of the solver tree"})
            return
        if length > MAX_BODY:
            self._send_json(413, {"error": f"body too large ({length} > {MAX_BODY})"})
            return
        data = self.rfile.read(length)
        with _STATE_LOCK:
            sub_id = _STATE["next_id"]
            _STATE["next_id"] += 1
            entry = {
                "submission": sub_id,
                "ts": time.time(),
                "status": "running",
                "records": None,
                "detail": "",
            }
            _STATE["submissions"].append(entry)
        try:
            sub_dir = WORK_DIR / "submissions" / str(sub_id)
            shutil.rmtree(sub_dir, ignore_errors=True)
            _safe_unpack(data, sub_dir / "app")
        except (tarfile.TarError, ValueError, OSError) as exc:
            entry.update(status="judge_error", detail=f"bad submission tar: {exc}"[:200])
            _persist()
            self._send_json(400, {"submission": sub_id, "status": "judge_error", "error": entry["detail"]})
            return
        _persist()
        _QUEUE.put(sub_id)
        _log(f"submission {sub_id} accepted ({length} bytes)")
        self._send_json(202, {"submission": sub_id, "status": "running"})


def main() -> int:
    global _QUEUE
    if INSTANCE_SET == "public":
        public_dir = os.environ.get("INSTANCES_PUBLIC_DIR", f"{TESTS_DIR}/instances_public")
        if not os.path.isdir(public_dir):
            _log(f"FATAL: INSTANCE_SET=public but the public instance dir {public_dir} is missing")
            return 2
        os.environ["INSTANCES_DIR"] = public_dir
    elif INSTANCE_SET != "hidden":
        _log(f"FATAL: unknown INSTANCE_SET {INSTANCE_SET!r} (expected hidden|public)")
        return 2
    _QUEUE = queue.SimpleQueue()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=_queue_loop, daemon=True).start()
    server = ThreadingHTTPServer((BIND_HOST, PORT), Handler)
    _log(
        f"listening on {BIND_HOST}:{PORT} (tests={TESTS_DIR} app={APP_DIR} work={WORK_DIR} "
        f"timeout={JUDGE_TIMEOUT:g}s instance_set={INSTANCE_SET})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
