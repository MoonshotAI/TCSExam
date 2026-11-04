#!/usr/bin/env python3
"""TCSExam judge worker — the in-image judging face of a Solver problem.

Baked into the problem's judge image at /judge/judge_worker.py and started by
the judge-session agent on localhost:$PORT (default 8082). Endpoints:

* ``POST /submit``      — body is a (gzipped) tar of the solver code tree
  (what becomes /app). Returns immediately with ``{"submission": n,
  "status": "running"}``; the judging runs serialized in the background
  (async submit + poll — never hold one HTTP request open for a whole
  judging).
* ``GET /submissions``  — the submission history ``[{submission, ts, status,
  records, detail}]``. RAW PER-INSTANCE RECORDS ONLY (raw-feedback protocol,
  design 260910): every finished ``ok`` entry carries ``records`` — one
  ``{instance, A, B, K, status, detail}`` per judged instance, where ``A`` is
  the solver's own objective value (1/0 for solve-type problems), ``B``/``K``
  the judging anchors, and ``status`` is ``ok`` | ``invalid`` (the model's
  own fault: invalid solution, timeout, crash) | ``error`` (a judging-
  pipeline fault — never blamed on the model). No scores, no aggregate: the
  service archives these records and itself answers the caller with the
  five-number summary (hidden sessions) or the anchor-stripped per-instance
  detail (public sessions). The final metric lives in the verifier.
* ``GET /health``       — liveness.

Sharding (env ``INSTANCE_SHARD=i/N``, injected by the service for sharded
sessions): this worker does NOT slice anything itself — the variable flows
through to the judge command's environment, and the problem's judging logic
(test.sh / checker) restricts itself to slice i of the sorted instance list.
SEMANTIC BOUNDARY: only problems with a PER-INSTANCE time budget may shard —
slicing then just scales the total work by 1/N with the per-instance budget
unchanged. Problems whose solver allocates one global time pool across
instances must migrate to per-instance budgets before they can shard (smt
did so on 2026-09-06, SMT-COMP 1200 s per instance; the shared-pool caliber
survives only in its retired v1 judge image). Whether a problem shards is
decided by whether its in-image checker implements INSTANCE_SHARD slicing.

Instance sets (env ``INSTANCE_SET=hidden|public``, injected by the service):
``hidden`` (default) judges the hidden set exactly as before. ``public``
redirects the judging to the public instance set baked into the image by
exporting ``INSTANCES_DIR`` (default ``$TESTS_DIR/instances_public``,
overridable via the ``INSTANCES_PUBLIC_DIR`` env) for the judge command —
the problem's checker already honors ``INSTANCES_DIR``; a missing public
directory is an image build error and the worker refuses to boot. The
per-instance judging budget is identical across the two sets, so "does
public-set performance transfer to the hidden set" stays a strict check.

Judging one submission: wipe $APP_DIR, unpack the tar into it, run
``$JUDGE_CMD`` (default ``bash $TESTS_DIR/test.sh`` — the problem's real
judging pipeline, unmodified) with ``REWARD_PATH`` pointed at a per-submission
file, kill the process group at $JUDGE_TIMEOUT, read the reward JSON.
注意（869b0837 后）：镜像里 /tests/test.sh 的来源必须是题目
tests/test_local.sh.bak（checker 判分版留档）——题目 tests/test.sh 已改为
verifier(fetch_final) 版，判分镜像拷它会整链崩（无 reward 文件）。
prepare-build-context.sh 按此组装。

Record construction (the ONLY transformation this worker applies — the
judging logic itself, computing A and checking validity, is untouched): the
reward JSON's per-instance table (``per_instance`` for objective problems,
``per_instance_detail`` for solve-count problems) is normalized into
records. Instances with B == K carry no signal for the hidden five numbers
(judging discipline: they stay out of ``records``), but the caller still
deserves their A (260922 ruling: every public instance the model can see
must be run AND reported) — the full normalized record lands in the entry's
``excluded_records`` side channel (reason ``b_equals_k``; the legacy
``excluded_no_signal`` name list is kept alongside for compatibility), and
the public-channel aggregation forwards it stripped of B/K. A reward JSON
without any per-instance table is a judging-pipeline regression: the entry
gets ``records: null`` with a flag in ``detail`` — NO SILENT DEGRADATION
into made-up numbers. See ``_build_records`` for the status normalization
rules.

Stdlib only (the judge image guarantees nothing else).
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
# Production workers accept connections from their local agent on 127.0.0.1.
# Local Docker mocks publish the port on the container's external interface.
BIND_HOST = os.environ.get("BIND_HOST", "127.0.0.1")
TESTS_DIR = os.environ.get("TESTS_DIR", "/tests")
APP_DIR = os.environ.get("APP_DIR", "/app")
WORK_DIR = Path(os.environ.get("WORK_DIR", "/work"))
JUDGE_CMD = os.environ.get("JUDGE_CMD", "").strip()  # default: bash $TESTS_DIR/test.sh
JUDGE_TIMEOUT = float(os.environ.get("JUDGE_TIMEOUT", "3600"))
MAX_BODY = 256 * 1024 * 1024
# hidden|public（服务端经 agent env 注入）；public 在 main() 里把判分重定向
# 到公开实例集（INSTANCES_DIR 导出给判分命令）。
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
    """Normalize the reward JSON's per-instance table into raw records.

    Returns ``(records, excluded, excluded_records, note)``; ``records`` is
    ``None`` (and ``note`` the flag) when the JSON carries no per-instance
    table at all — the no-silent-degradation path: the entry surfaces the
    regression instead of inventing numbers. ``excluded`` is the legacy
    B==K instance-name list (compatibility, unchanged semantics);
    ``excluded_records`` is the 260922 side channel: the FULL normalized
    record (``{instance, A, B, K, status, detail, reason}``) of every key
    diverted out of ``records`` — B==K keys (reason ``b_equals_k``) and
    marked no-anchor practice keys (reason ``practice_no_anchors``). The
    hidden channel never reads it; the public channel forwards it stripped
    of B/K so the model sees an A for every instance it can see.

    Per-instance status normalization (design 260910 §4.1 — the status
    separates the model's own fault from infrastructure's):

    * ``ok`` — the instance was judged normally. Objective problems:
      ``status == "ok"`` with a numeric A. Solve-type problems: a ``verdict``
      is present (solved or not — "not solved" is a normal outcome whose
      A = 0/1 then drives the three-way comparison against B; a refuted
      UNSAT claim is already folded to "not solved" by the judging logic).
    * ``invalid`` — the model's own fault: invalid solution / solver
      timeout / crash (the objective-problem non-ok status strings). A is
      forced to null — the service counts these as ``worse``.
    * ``error`` — the judging pipeline's own fault: a record with no
      status/verdict, missing anchors, or an "ok" record without a numeric
      A. Never blamed on the model — the service counts these as ``failed``.
      Exception (2026-09-13, judge images >= cgshop-socg v8): a record whose
      B anchor is null with a numeric K AND an explicit
      ``anchor_baseline_unsolved`` marker from the judging logic is NOT an
      anchor error — B=null is the sanctioned baseline-unsolved anchor form
      (260912 ruling); the original outcome is normalized without changing its validity; A is preserved for
      the archive, and the aggregation layer excludes it from the five
      numbers (temporary caliber, 拍板③). An anchor miss WITHOUT the
      marker stays a pipeline error as before (safety net unchanged).
      Second sanctioned form (260922 ruling, 乙类 practice instances): a
      record whose B AND K are both null with an explicit
      ``practice_no_anchors`` marker is NOT an error either — it goes to
      ``excluded_records`` (reason ``practice_no_anchors``) with its status
      normalized by the same rules and A preserved.

    Instances with B == K carry no signal for the five numbers (judging
    discipline: excluded from the judging set) — they are diverted from
    ``records`` into ``excluded_records`` (reason ``b_equals_k``) with the
    instance name listed in ``excluded``. Exception (2026-09-17, iccma-arg
    all-keys caliber): when the reward JSON carries
    ``scoring_caliber == "all-keys-solve-rate-260917"``, B == K instances
    are scorable (solve=1/fail=0 over every judged key) and are KEPT as
    records.
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
            # B=null + K 数值 + 判分逻辑显式打标（anchor_baseline_unsolved）
            # = 260912 拍板的基线未解出锚形态：按 ok 放行、A 原样保留进存
            # 档；无标记的锚缺失仍是管线错误（安全网不松）。
            if (b is None and _is_num(k)
                    and rec.get("anchor_baseline_unsolved") is True):
                entry = _normalize_status(name, rec, a, None, k, detail)
                entry["anchor_baseline_unsolved"] = True
                records.append(entry)
            elif (b is None and k is None
                    and rec.get("practice_no_anchors") is True):
                # B=K=null + 判分逻辑显式打标（practice_no_anchors）=
                # 260922 裁定的无锚练习键形态（乙类题：模型可见但参照暂无
                # 锚的实例）：合法放行——status 按同一套规则归一、A 原样保
                # 留，进 excluded_records 侧通道，公开通道剥锚后照报 A。
                entry = _normalize_status(name, rec, a, None, None, detail)
                entry["reason"] = "practice_no_anchors"
                excluded_records.append(entry)
            else:
                records.append(
                    {"instance": name, "A": a if _is_num(a) else None,
                     "B": b if _is_num(b) else None, "K": k if _is_num(k) else None,
                     "status": "error", "detail": detail or "record carries no numeric anchors"}
                )
            continue
        entry = _normalize_status(name, rec, a, b, k, detail)
        if float(b) == float(k) and not keep_b_equals_k:
            # B==K 无信号键：不进 records（隐藏五数口径不动），完整记录进
            # excluded_records 侧通道（260922：公开实例全部跑、全部报 A）；
            # 旧 excluded_no_signal 名单字段原样保留。
            excluded.append(name)
            entry["reason"] = "b_equals_k"
            excluded_records.append(entry)
            continue
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
        try:
            tar.extractall(dest, filter="data")  # py3.12+: strips .., abs, devices
        except TypeError:  # older python: manual member check
            for member in tar.getmembers():
                name = member.name
                if name.startswith("/") or ".." in Path(name).parts:
                    raise ValueError(f"unsafe tar member: {name!r}")
            tar.extractall(dest)


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
        # 公开自测通道（设计稿 260910 §3.6）：判分重定向到镜像内烘焙的公开
        # 实例集——checker 读 INSTANCES_DIR，逐实例判分预算与隐藏判分同口径。
        # 目录缺失是镜像构建错误，直接拒起（比判出全 failed 更早暴露）。
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
