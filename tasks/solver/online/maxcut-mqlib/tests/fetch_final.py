#!/usr/bin/env python3
"""maxcut-mqlib verifier (form 1, raw-feedback protocol, design 260910; public
self-test history merge added 260912 per next-steps-260911.md §E; violation
accounting switched to the declared session chain 260912 per the session-
chain attribution ruling in next-steps-260911.md §74 — the client_ip caliber
is retired to ops telemetry): the run is
over; this script judges the final solver tree the agent left in /app exactly
once on the judged instances, through the SAME tcsexam judging chain the
async (form 2) packages use, then recomputes the score LOCALLY from the
archived per-instance raw records.

This package renders in one of two branches (HISTORY_BEST below):
* HISTORY_BEST=False (final-judging-only tasks): the run's score is the
  verifier's one judging, full stop. The agent's public self-test
  submissions (submit.sh, unlimited, on a public practice set) never score;
  their sessions are still pulled into the artifact for the record
  (next-steps-260911.md §E: every channel's submissions go into the
  archived history; scoring calibers are computed from it after the fact).
* HISTORY_BEST=True (no-hidden-set tasks): every judged instance is public
  and shipped in the agent's environment, and the agent's submit.sh judged
  its solver on those SAME instances without limit. The run's score is
  best(public self-test history, the final judging): each submission found
  in the declared session chain's PUBLIC archives is scored with the same
  metric engine and the same anchors as the final judging, and the reward
  is the max. Public self-test submissions never enter any violation
  accounting — there is no hidden set to protect, so the submission cap
  does not apply to them; the reconciliation in step 5 watches the hidden
  lane only, told apart from the public lane by each session's accepted
  hidden-submission count in the chain reconciliation (and cross-checked
  against each archive's instance_set at merge time).

Flow:
 1. Pack /app into a tar.gz (same exclusion rules as the task's async
    submit.sh: the shipped public assets the judge does not need, plus the
    session-record dotfiles).
 2. Create ONE hidden-set judge session (instance_set defaults to hidden;
    judge_image / n_shards / resources mirror the task's async submit.sh;
    TTL below — one judging plus margin; the session is destroyed by this
    script when done, not left to the reaper). Every request carries
    X-TCSEXAM-Client-Id (the container-stable run id): the session-create
    singleflight key's third element — without it the key degrades to the
    NAT-shared egress IP and a concurrent same-token+same-image create
    (e.g. this task's async sibling judging at the same time) merges into
    one shared session, whose later teardown then kills the other run's
    in-flight judging (the 3658 incident). In a no-hidden-set task the
    "hidden" channel only names the verifier-only judging lane: the judged
    instances themselves are public, but this lane stays the one the agent
    must not call itself.
 3. Upload the tar (POST .../submit) and poll .../submissions until judging
    finishes.
 4. Pull the raw-record archive (GET .../archive with the X-TCSEXAM-Archive-Token
    credential from tests/archive_token, mounted only at verify time) and
    merge the shard payloads into per-instance records.
 5. Hidden-channel reconciliation (contract v1.2, BEFORE any metric
    computation): the accounting unit is the run's DECLARED session chain
    (/app/.judge_sessions) plus this verifier's own fresh session — NOT
    the source IP. The fleet egresses through a NAT-shared pool, so the
    retired client_ip total merged neighbors' submissions into this run's
    count (the 3658 incident: a clean oracle run of a no-hidden-set
    package false-tripped on the fleet-wide total). The verifier's own
    session joins the accounting unit in memory (never in the chain
    FILE — the file keeps its agent-declared meaning, so a re-run of
    this verifier can never mistake a previous verifier session for
    agent evidence), so a clean run's reconciled total is EXACTLY 1
    (the single final judging). The per-session
    accepted hidden-submission counts come from GET
    /v1/judge/sessions?session_ids=a,b,c (same query shape as
    fetch_best's chain reconciliation). In form 1 the agent's only
    judging-service access is the public self-test channel — every
    form-1 submit.sh is public-only in both branches, and the task
    statement rules creating or using any other judging session a
    violation — so ANY accepted hidden submission on a DECLARED agent
    session is the agent calling the hidden channel itself: scoring
    violation, reward 0.0 with "violation": "hidden_channel_used_by_agent"
    (exit 0). This zero-tolerance caliber holds in both branches; the
    server-side 10-cap is per-session (v0.6.14) and only bounds how many
    agent submissions a single session can hold — it is NOT an allowance
    (an agent-side hidden submission never scores in form 1, whatever
    the count). Sessions the agent did NOT declare are invisible to this
    query by design (undeclared = forfeited — the same structural
    position as fetch_best): their submissions can never score in
    form 1, and the task statement's command-trace audit is the
    deterrent for them. A failed reconciliation query never voids the
    run ("hidden_channel_check": "skipped_service_unreachable"). The
    retired client_ip total is still queried best-effort and recorded
    as ops telemetry ("client_ip_total_observed", printed) — never a
    verdict.
 6. Public self-test history: the DECLARED session chain
    /app/.judge_sessions (submit.sh appends every judge session it
    creates) is already read for step 5 — the same reconciliation result
    doubles as the audit trail here — and each declared session's archive
    is pulled. A
    session the service no longer knows (uniform 404: reaped/unknown) or
    reports destroyed (410 terminal, v0.6.18) is noted and skipped: history
    loss never voids the final judging, because the history merge can only
    RAISE the reward. Public archives merge into per-submission candidates
    by the same rules as the verifier's own; an archive whose instance_set
    is hidden (possible only when the agent called the hidden channel
    itself) is never scored — its submissions are exactly what step 5
    counts as violation evidence.
 7. Score the candidates with the unified metric engine (tests/metric/,
    anchors from tests/anchors.json per tests/metric_config.json): the
    verifier's own submission gives the final score; with HISTORY_BEST the
    public-history candidates score alongside and the reward is the max
    ("score_source" in score-details.json says which side won), otherwise the
    final score alone is the reward. Write a numeric-only reward.json;
    preserve the complete per-instance contribution detail in score-details.json.

Reward contract (harbor):
* Normal completion           -> the judged score (a fully invalid /
                                 timed-out solver honestly scores 0.0).
* Agent used the hidden       -> reward 0.0, "violation" set, exit 0.
  channel itself
* Session create / submit /   -> infrastructure failure: exit nonzero WITHOUT
  poll / archive unreachable    writing a reward file, so the platform reports
  or broken                   an env problem instead of a fake 0.
* Session destroyed           -> same infrastructure failure, at once: the
  server-side (HTTP 410 +     terminal face (v0.6.18) is final, no retry or
  error_class=terminal)       poll against it can succeed. A DECLARED
                              self-test session gone/destroyed is NOT this
                              case: noted and skipped (step 6).

Submit exactly-once discipline: the relay counts an accepted submission the
moment it arrives. A blind retry after an ambiguous submit failure could
double-count the verifier's own upload — the chain accounting requires the
verifier's own session to read EXACTLY one accepted submission — so the
submit is retried ONLY on the never-counted provisioning 503;
any other failure is an infrastructure failure without retry. (A 429 means
this session's per-session cap was already exhausted before our first
upload — our session is fresh and unique to this container, so those
accepted submissions are agent-side evidence — handled as the violation
it is.)

The merged raw records (the verifier's own submission AND the reachable
declared self-test sessions' submissions) plus the full metric detail
(per-instance contributions, exclusions, zeroed instances) are archived to
/logs/verifier/submissions.json for later harvest and replay; every
session's persisted submission bodies (the exact solver tars each /submit
uploaded) are dumped verbatim to /logs/verifier/submission_payloads/
(best-effort, manifest in the artifact) for offline audit. (Path note
260914: harbor collects /logs/artifacts from the AGENT env right after the
agent phase, so anything the verifier writes there is lost; /logs/verifier
is the proven collected channel — reward.json lands the same way.)
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

TESTS_DIR = os.environ.get("TCSEXAM_TESTS_DIR") or os.path.dirname(os.path.abspath(__file__))
SERVICE_BASE = os.environ.get("TCSEXAM_BASE_URL", "").rstrip("/")
APP_DIR = os.environ.get("TCSEXAM_APP_DIR", "/app")
REWARD_JSON = os.environ.get("REWARD_JSON", "/logs/verifier/reward.json")
REWARD_TXT = os.environ.get("REWARD_TXT", "/logs/verifier/reward.txt")
ARTIFACT = os.environ.get("SUBMISSIONS_ARTIFACT", "/logs/verifier/submissions.json")

TOKEN_ID = os.environ.get("TCSEXAM_TOKEN_ID")
TOKEN_SECRET = os.environ.get("TCSEXAM_TOKEN_SECRET")

# Judging-chain parameters (rendered per task from the async submit.sh).
JUDGE_IMAGE = os.environ["TCSEXAM_JUDGE_IMAGE"]
N_SHARDS = int(os.environ.get("TCSEXAM_N_SHARDS", "10"))
RESOURCES = {"cpu": int(os.environ.get("TCSEXAM_WORKER_CPUS", "16")), "mem": int(os.environ.get("TCSEXAM_WORKER_MEMORY_MB", "16384"))}
if "TCSEXAM_WORKER_STORAGE_MB" in os.environ:
    _storage = os.environ["TCSEXAM_WORKER_STORAGE_MB"].strip().lower()
    RESOURCES["storage_mb"] = None if _storage in {"none", "null"} else int(_storage)

TAR_EXCLUDES = (".git", ".svn", ".hg", "__pycache__", ".pytest_cache", ".mypy_cache", ".ipynb_checkpoints", "node_modules", ".venv", "venv", "*.o", "*.obj", "*.pyc", "*.pyo", "*.log", "*.tmp", "*.txt.xz", "./instances", "./solutions", "./.session_public_id", "./.judge_sessions", "./.submit_keepalive.pid", "./.submit_public_keepalive.pid")

# Scoring branch (rendered per task): True only for the no-hidden-set branch
# (official-form-assignment-260911.md), where the run's score is best(public
# self-test history, final judging). See the module docstring.
HISTORY_BEST = False

SESSION_TTL = int(os.environ.get("TCSEXAM_SESSION_TTL", "14400"))  # one judging plus margin (rendered per task from
                            # the task's judging wall-clock); destroyed on use
CREATE_RETRIES = 5          # session create attempts (submit.sh caliber)
CREATE_RETRY_BACKOFF = 60.0
READY_POLLS = 120           # wait_ready: 120 x 15 s = 30 min (submit.sh caliber)
READY_INTERVAL = 15.0
SUBMIT_TIMEOUT = 600        # one upload can be large (submit.sh --max-time 600)
SUBMIT_503_RETRIES = 5      # provisioning 503 is never counted: safe to retry
SUBMIT_503_BACKOFF = 60.0
POLL_INTERVAL = float(os.environ.get("TCSEXAM_POLL_INTERVAL", "60"))
POLL_TIMEOUT = float(os.environ.get("TCSEXAM_POLL_TIMEOUT", "14400"))
ARCHIVE_RETRIES = 3
# Number of times to retry the entire judging run in a new session after a shard dies mid-run (merged entry has failed_shards>0).
# Service semantics: a mid-run shard failure is not retried and history is not rewritten; the failed bucket is recorded explicitly.
# However, accepting results with failed buckets silently distorts the score because missing keys do not enter the denominator (260917 iccma
# oracle v2 demonstrated 17 missing keys). A retry starts a new session and, by service design, does not count against the model submission limit.
FAILED_SHARD_RETRIES = 2
ARCHIVE_RETRY_BACKOFF = 2.0  # seconds, linear

# Public self-test history (step 6): the declared session chain submit.sh
# appends to, plus the per-session count query and archive-pull calibers
# (same shapes as fetch_best's chain reconciliation).
CHAIN_FILE = os.environ.get("TCSEXAM_CHAIN_FILE", "/app/.judge_sessions")
CHAIN_QUERY_RETRIES = 4
CHAIN_QUERY_BACKOFF = 5.0     # seconds, linear
CHAIN_QUERY_TIMEOUT = 90      # seconds per attempt
HISTORY_ARCHIVE_RETRIES = 3
HISTORY_ARCHIVE_RETRY_BACKOFF = 2.0   # seconds, linear
HISTORY_ARCHIVE_TIMEOUT = 120  # seconds per attempt; big chains answer slowly

# Submission-body archiving (260918): every session's persisted submission
# bodies (the exact bytes each /submit uploaded — the solver tars) are
# dumped verbatim into PAYLOAD_DIR for offline audit/replay. Audit
# evidence, never a scoring input.
PAYLOAD_DIR = os.environ.get("SUBMISSIONS_PAYLOAD_DIR",
                             "/logs/verifier/submission_payloads")
PAYLOAD_TOTAL_CAP = 256 * 1024 * 1024  # bytes; evidence must not bloat collection
PAYLOAD_FETCH_RETRIES = 2
PAYLOAD_FETCH_TIMEOUT = 120  # seconds per attempt


def infra_fail(msg):
    print(f"[verifier] INFRASTRUCTURE FAILURE: {msg}", file=sys.stderr)
    print("[verifier] not writing a reward file so this is not scored as an honest 0", file=sys.stderr)
    sys.exit(1)


def terminal_destroyed(exc):
    """True when an HTTPError is the service's terminal face (v0.6.18): a
    session destroyed server-side answers HTTP 410 Gone with body
    {"error_class":"terminal"}. That is final, not transient — no retry or
    poll against it can ever succeed."""
    if not isinstance(exc, urllib.error.HTTPError):
        return False
    if exc.code == 410:
        return True
    try:
        body = exc.read().decode("utf-8", "replace")
    except Exception:
        return False
    return '"error_class"' in body and '"terminal"' in body


def terminal_answer(code, body):
    """terminal_destroyed for http_call sites, which already hold the
    (status, body-bytes) pair instead of an exception."""
    if code == 410:
        return True
    try:
        text = bytes(body).decode("utf-8", "replace")
    except Exception:
        return False
    return '"error_class"' in text and '"terminal"' in text


def terminal_fail(context):
    infra_fail(f"{context}: the judging session was destroyed server-side "
               "(The judging session was destroyed by the service; this submission is void); this is final, not transient")


def _std_headers(req):
    """Attach TCSEXAM credentials and a stable, per-attempt client identity."""
    req.add_header("X-TCSEXAM-Token-Id", TOKEN_ID or "")
    req.add_header("X-TCSEXAM-Token-Secret", TOKEN_SECRET or "")
    run_id = (os.environ.get("TCSEXAM_RUN_ID") or os.environ.get("HOSTNAME")
              or socket.gethostname())
    if run_id:
        req.add_header("X-TCSEXAM-Run-Id", run_id)
        req.add_header("X-TCSEXAM-Client-Id", run_id)
    agent_name = os.environ.get("TCSEXAM_AGENT_NAME")
    if agent_name:
        req.add_header("X-TCSEXAM-Agent-Name", agent_name)


def http_get_json(url, extra_headers=None, timeout=60):
    """One GET with the standard verifier headers; returns the decoded JSON
    body. Raises urllib.error.HTTPError on any non-2xx status so callers can
    branch on the code."""
    req = urllib.request.Request(url)
    _std_headers(req)
    for key, val in (extra_headers or {}).items():
        req.add_header(key, val)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def http_call(method, url, body=None, extra_headers=None, timeout=60):
    """One non-GET call (POST/DELETE) with the standard headers. Returns
    (status, body-bytes) for ANY HTTP answer (no raise on 4xx/5xx); raises
    only on network-level failures (URLError/TimeoutError/OSError)."""
    req = urllib.request.Request(url, data=body, method=method)
    _std_headers(req)
    for key, val in (extra_headers or {}).items():
        req.add_header(key, val)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def client_ip_total_observed(archive_token):
    """Ops telemetry ONLY (retired contract v1.1 reconciliation): the run
    identity's accepted hidden submissions as resolved by source identity —
    NAT-dirty by construction (the fleet shares one egress pool, so this
    number accumulates fleet-wide). Printed and recorded for the operators,
    NEVER used as a verdict: the chain reconciliation below is the
    accounting unit. Returns the service-reported total_submissions, or
    None when the query itself fails (its failure is as unactionable as
    the number itself)."""
    try:
        data = http_get_json(
            f"{SERVICE_BASE}/v1/judge/sessions?client_ip=self",
            extra_headers={"X-TCSEXAM-Archive-Token": archive_token})
        total = int(data.get("total_submissions") or 0)
        print(f"[verifier] client_ip total_submissions (ops telemetry, "
              f"NAT-dirty, not a verdict): {total}")
        return total
    except Exception as exc:
        print(f"[verifier] client_ip telemetry query failed (ignored): {exc}",
              file=sys.stderr)
        return None


def chain_hidden_reconciliation(declared, own_sid, archive_token):
    """Hidden-channel reconciliation over the DECLARED session chain plus
    this verifier's own session (contract v1.2 — the accounting unit that
    replaced the client_ip total). Returns None when the underlying chain
    query keeps failing (check skipped, never voids); otherwise
    {"agent_hidden": int, "own_counted": int, "total": int, "sessions": ...}
    where agent_hidden sums the accepted hidden submissions over the
    DECLARED AGENT sessions (own_sid excluded) — in form 1 any value > 0
    is the violation (see the module docstring step 5) — and own_counted
    is how many accepted submissions the journal holds on the verifier's
    own session (telemetry; exactly 1 in a clean run)."""
    sids = list(dict.fromkeys(list(declared or []) + [own_sid]))
    recon = chain_reconcile(sids, archive_token)
    if recon is None:
        return None
    agent_hidden = sum(row["submissions"] for sid, row in recon["sessions"].items()
                       if sid != own_sid)
    own_row = recon["sessions"].get(own_sid) or {}
    return {"agent_hidden": agent_hidden,
            "own_counted": int(own_row.get("submissions") or 0),
            "total": recon["total"], "sessions": recon["sessions"]}


def read_declared_sessions():
    """Read the run's declared session chain (/app/.judge_sessions): submit.sh
    appends every judge session it creates — in form 1 those are public
    self-test sessions. Returns the deduped sid list (order kept), or None
    when the file does not exist (the agent never self-tested; undeclared
    sessions are forfeited by design and invisible here)."""
    if not os.path.isfile(CHAIN_FILE):
        return None
    with open(CHAIN_FILE) as f:
        sids = [ln.strip() for ln in f if ln.strip()]
    return list(dict.fromkeys(sids))


def chain_reconcile(sids, archive_token):
    """Query the per-session submission counts over the given sessions
    (GET /v1/judge/sessions?session_ids=a,b,c — the query/retry scaffold of
    fetch_best's chain reconciliation). The counts distinguish each
    session's lane (hidden ``submissions`` vs ``public_submissions``). This
    is BOTH the step-5 violation verdict's data source and the step-6
    audit trail; its failure (including the terminal face: retrying a
    destroyed session is pointless, but the history merge must not die
    with it) returns None ("check skipped"), never a run outcome.

    Returns {"total": int, "sessions": {sid: {...per-session counts...}}},
    or None when the query keeps failing.
    """
    url = f"{SERVICE_BASE}/v1/judge/sessions?session_ids={','.join(sids)}"
    last_exc = None
    for attempt in range(1, CHAIN_QUERY_RETRIES + 1):
        try:
            data = http_get_json(
                url, extra_headers={"X-TCSEXAM-Archive-Token": archive_token},
                timeout=CHAIN_QUERY_TIMEOUT)
            rows = data.get("sessions")
            if not isinstance(rows, list):
                raise ValueError(f"malformed chain reconciliation payload: {data!r}")
            per = {}
            for row in rows:
                per[row.get("session_id")] = {
                    "submissions": int(row.get("submissions") or 0),
                    "public_submissions": int(row.get("public_submissions") or 0),
                    "present": bool(row.get("present")),
                }
            if data.get("total_submissions") is not None:
                total = int(data["total_submissions"])
            else:
                total = sum(r["submissions"] for r in per.values())
            return {"total": total, "sessions": per}
        except Exception as exc:
            if terminal_destroyed(exc):
                print(f"[verifier] chain count query answered the terminal face; "
                      "recording the check as skipped", file=sys.stderr)
                return None
            last_exc = exc
            print(f"[verifier] chain count query attempt "
                  f"{attempt}/{CHAIN_QUERY_RETRIES} failed: {exc}", file=sys.stderr)
            if attempt < CHAIN_QUERY_RETRIES:
                time.sleep(CHAIN_QUERY_BACKOFF * attempt)
    print(f"[verifier] chain count query skipped: failed "
          f"{CHAIN_QUERY_RETRIES}x: {last_exc}", file=sys.stderr)
    return None


def fetch_history_archive(sid, archive_token):
    """Pull one DECLARED self-test session's raw-record archive for the
    history merge. Returns ("ok", body) / ("gone", None): a uniform 404
    (reaped session / unknown sid) and the terminal 410 face (destroyed
    server-side, v0.6.18) both mean this session's history is unrecoverable
    — noted and skipped, NEVER an infrastructure failure: the history merge
    can only raise the reward, so losing a piece of it must not void the
    final judging (the verifier's own fresh session is the load-bearing
    one — it infra-fails on the same faces in fetch_archive). 401/403
    infra-fail at once: a broken credential would break the verifier's own
    archive fetch identically, so it is not a history-local problem. Other
    failures retry HISTORY_ARCHIVE_RETRIES times, then the session is
    skipped as unreachable."""
    url = f"{SERVICE_BASE}/v1/judge/sessions/{sid}/archive"
    headers = {"X-TCSEXAM-Archive-Token": archive_token}
    last_exc = None
    for attempt in range(1, HISTORY_ARCHIVE_RETRIES + 1):
        try:
            return "ok", http_get_json(url, extra_headers=headers,
                                       timeout=HISTORY_ARCHIVE_TIMEOUT)
        except urllib.error.HTTPError as exc:
            if terminal_destroyed(exc):
                print(f"[verifier] declared session {sid} was destroyed "
                      "server-side; its self-test history is skipped", file=sys.stderr)
                return "gone", None
            if exc.code == 404:
                return "gone", None
            if exc.code in (401, 403):
                infra_fail(f"auth rejected by the judging service (HTTP {exc.code})")
            last_exc = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
        if attempt < HISTORY_ARCHIVE_RETRIES:
            time.sleep(HISTORY_ARCHIVE_RETRY_BACKOFF * attempt)
    print(f"[verifier] WARNING: cannot pull the archive of declared session "
          f"{sid} after {HISTORY_ARCHIVE_RETRIES} attempts ({last_exc}); "
          "its self-test history is skipped", file=sys.stderr)
    return "gone", None


def http_get_bytes(url, extra_headers=None, timeout=60):
    """One GET with the standard verifier headers; returns the raw body
    bytes. Raises urllib.error.HTTPError on any non-2xx status (same
    discipline as http_get_json)."""
    req = urllib.request.Request(url)
    _std_headers(req)
    for key, val in (extra_headers or {}).items():
        req.add_header(key, val)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def archive_submission_payloads(sessions, archive_token):
    """Best-effort verbatim dump of every session's persisted submission
    bodies (the exact bytes each /submit uploaded — the solver tars) into
    PAYLOAD_DIR, via the service's audit endpoints
    (/v1/judge/sessions/{sid}/payload/submissions[/seq], same gate as the
    archive endpoint). Audit evidence, NOT a scoring input — nothing here
    infra-fails: a session whose bodies are gone (reaped/hibernated/never
    persisted server-side) is noted in the manifest and skipped. Returns
    the manifest dict."""
    manifest = {"dir": PAYLOAD_DIR, "sessions": {}, "total_bytes": 0,
                "truncated": False}
    try:
        os.makedirs(PAYLOAD_DIR, exist_ok=True)
    except OSError as exc:
        manifest["error"] = f"cannot create {PAYLOAD_DIR}: {exc}"
        return manifest
    for sid in sessions:
        entry = {"archived": [], "unavailable": []}
        manifest["sessions"][sid] = entry
        index_url = f"{SERVICE_BASE}/v1/judge/sessions/{sid}/payload/submissions"
        headers = {"X-TCSEXAM-Archive-Token": archive_token}
        try:
            index = http_get_json(index_url, extra_headers=headers,
                                  timeout=PAYLOAD_FETCH_TIMEOUT)
            seqs = list(index.get("submissions") or [])
        except Exception as exc:  # gone session / unreachable: noted, skipped
            entry["unavailable"].append({"seq": None, "reason": f"index: {exc}"})
            continue
        for seq in seqs:
            if manifest["total_bytes"] >= PAYLOAD_TOTAL_CAP:
                manifest["truncated"] = True
                entry["unavailable"].append({"seq": seq,
                                             "reason": "total byte cap reached"})
                continue
            body_url = f"{index_url}/{seq}"
            body = None
            last_exc = None
            for attempt in range(1, PAYLOAD_FETCH_RETRIES + 1):
                try:
                    body = http_get_bytes(body_url, extra_headers=headers,
                                          timeout=PAYLOAD_FETCH_TIMEOUT)
                    last_exc = None
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code in (404, 410) or terminal_destroyed(exc):
                        last_exc = (f"HTTP {exc.code}: body not persisted "
                                    "or session gone")
                        break
                    last_exc = exc
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    last_exc = exc
                if attempt < PAYLOAD_FETCH_RETRIES:
                    time.sleep(2.0 * attempt)
            if last_exc is not None:
                entry["unavailable"].append({"seq": seq, "reason": str(last_exc)})
                continue
            path = os.path.join(PAYLOAD_DIR, f"{sid}-{seq}.tar")
            try:
                with open(path, "wb") as f:
                    f.write(body)
            except OSError as exc:
                entry["unavailable"].append({"seq": seq, "reason": f"write: {exc}"})
                continue
            manifest["total_bytes"] += len(body)
            entry["archived"].append({"seq": seq, "bytes": len(body), "path": path})
    return manifest


def pack_app():
    """Pack APP_DIR into a tar.gz with the task's exclusion rules (same flags
    as submit.sh: -h dereferences symlinks)."""
    fd, tarball = tempfile.mkstemp(prefix="fetch-final-", suffix=".tar.gz")
    os.close(fd)
    cmd = ["tar", "-chzf", tarball, "-C", APP_DIR]
    cmd += [f"--exclude={pat}" for pat in TAR_EXCLUDES]
    cmd.append(".")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        infra_fail(f"packing {APP_DIR} failed (rc={proc.returncode}): {proc.stderr.strip()}")
    size = os.path.getsize(tarball)
    print(f"[verifier] packed {APP_DIR} ({size} bytes, {len(TAR_EXCLUDES)} exclude rules)")
    # Archive the exact /app pack into the container artifact (best effort):
    # the judge session's payload copy dies with the session and the agent
    # sandbox is reclaimed, so without this file the model's final tree is
    # unrecoverable and a broken-chain run can only be redone, not re-judged
    # (260923 sygus lesson). /logs/verifier ships inside the artifact;
    # /logs/artifacts is collected right after the agent phase and would
    # lose anything the verifier writes there.
    try:
        os.makedirs("/logs/verifier", exist_ok=True)
        shutil.copy(tarball, "/logs/verifier/app-final.tar.gz")
    except Exception as exc:  # noqa: BLE001 — archiving must never break judging
        print(f"[verifier] app pack archive skipped: {exc}")
    return tarball


def create_session(archive_token):
    """Create the one hidden-set judge session (instance_set defaults to
    hidden server-side, exactly like the async submit.sh hidden path) and
    wait for it to become usable."""
    payload = json.dumps({
        "judge_image": JUDGE_IMAGE,
        "ttl": SESSION_TTL,
        "n_shards": N_SHARDS,
        "resources": RESOURCES,
    }).encode()
    url = f"{SERVICE_BASE}/v1/judge/sessions"
    last = None
    for attempt in range(1, CREATE_RETRIES + 1):
        try:
            code, body = http_call("POST", url, body=payload,
                                   extra_headers={"Content-Type": "application/json",
                                                  "X-TCSEXAM-Archive-Token": archive_token},
                                   timeout=2400)
            if terminal_answer(code, body):
                terminal_fail("session create rejected")
            if code in (200, 201, 202):
                sid = json.loads(body.decode())["session_id"]
                print(f"[verifier] judge session {sid} created "
                      f"(image={JUDGE_IMAGE}, n_shards={N_SHARDS}, ttl={SESSION_TTL})")
                wait_ready(sid)
                return sid
            last = f"HTTP {code}: {body[:300]!r}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
        print(f"[verifier] session create attempt {attempt} failed ({last}); "
              f"retrying in {CREATE_RETRY_BACKOFF:.0f}s...", file=sys.stderr)
        time.sleep(CREATE_RETRY_BACKOFF)
    infra_fail(f"could not create a judge session after {CREATE_RETRIES} attempts: {last}")


def wait_ready(sid):
    """Poll until the session is usable (submit.sh's logic: this service
    creates sessions synchronously, so a 200 without a status key means
    ready; tolerate the core-package async-provisioning states if they ever
    appear)."""
    for _ in range(READY_POLLS):
        try:
            body = http_get_json(f"{SERVICE_BASE}/v1/judge/sessions/{sid}", timeout=30)
        except urllib.error.HTTPError as exc:
            if terminal_destroyed(exc):
                terminal_fail(f"judge session {sid} poll during provisioning rejected")
            if exc.code == 404:
                infra_fail(f"judge session {sid} vanished during provisioning")
            body = None
        except (urllib.error.URLError, TimeoutError, OSError):
            body = None
        if body is not None:
            status = body.get("status")
            if status is None:
                if body.get("tunnel_connected", True):
                    print(f"[verifier] session {sid} ready")
                    return
            elif status in ("ready", "running"):
                print(f"[verifier] session {sid} ready")
                return
            elif status in ("failed", "dead", "error"):
                infra_fail(f"judge session {sid} entered {status} "
                           f"({body.get('detail') or body.get('error') or ''})")
        time.sleep(READY_INTERVAL)
    infra_fail(f"judge session {sid} still not ready after "
               f"{int(READY_POLLS * READY_INTERVAL) // 60} min")


def submit_once(sid, tarball):
    """Upload the packed solver tree EXACTLY once (see the module docstring
    for the exactly-once discipline). Returns the accepted submission id."""
    with open(tarball, "rb") as f:
        payload = f.read()
    url = f"{SERVICE_BASE}/v1/judge/sessions/{sid}/submit"
    for attempt in range(1, SUBMIT_503_RETRIES + 1):
        try:
            code, body = http_call("POST", url, body=payload,
                                   extra_headers={"Content-Type": "application/gzip"},
                                   timeout=SUBMIT_TIMEOUT)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            infra_fail(
                f"submit got no server answer ({exc}); NOT retrying: the relay "
                "counts accepted submissions, and a blind retry could double-count "
                "the verifier's own upload and falsely trip the agent-violation "
                "check"
            )
        if terminal_answer(code, body):
            terminal_fail("submit rejected")
        if code in (200, 201, 202):
            sub_id = int(json.loads(body.decode())["submission"])
            print(f"[verifier] submission {sub_id} accepted; judging may take a while, polling...")
            return sub_id
        if code == 503:
            # Provisioning short-circuit: never counted as a submission.
            print(f"[verifier] session still provisioning (503); retry "
                  f"{attempt}/{SUBMIT_503_RETRIES} in {SUBMIT_503_BACKOFF:.0f}s...",
                  file=sys.stderr)
            time.sleep(SUBMIT_503_BACKOFF)
            continue
        if code == 429:
            # The hidden channel caps at 10 accepted submissions per run
            # identity. The verifier submits once — a 429 here means the
            # agent already used the hidden channel itself. Confirm via the
            # reconciliation count and void the run as the violation it is.
            print("[verifier] submit rejected with HTTP 429 submission_cap_exceeded: "
                  "the hidden-channel cap was already exhausted by the agent", file=sys.stderr)
            return None
        infra_fail(f"submit rejected (HTTP {code}): {body[:500]!r}")
    infra_fail(f"session still provisioning after {SUBMIT_503_RETRIES} submit attempts")


def poll_until_done(sid, sub_id):
    """Poll .../submissions until our submission leaves the running state.
    502 / network errors are transient by the service contract (retry); our
    submission vanishing from the history is not."""
    url = f"{SERVICE_BASE}/v1/judge/sessions/{sid}/submissions"
    deadline = time.time() + POLL_TIMEOUT
    while True:
        time.sleep(POLL_INTERVAL)
        try:
            data = http_get_json(url)
        except Exception as exc:
            if terminal_destroyed(exc):
                terminal_fail(f"poll of session {sid} rejected")
            print(f"[verifier] poll error (transient, retrying): {exc}", file=sys.stderr)
            data = None
        if data is not None:
            subs = data.get("submissions") or []
            me = next((s for s in subs if int(s.get("submission", -1)) == sub_id), None)
            if me is None:
                infra_fail(f"submission {sub_id} vanished from the session history "
                           "(session restarted?)")
            if str(me.get("status")) != "running":
                print(f"[verifier] submission {sub_id} finished: status={me.get('status')} "
                      f"detail={me.get('detail', '')}")
                return me
            print(f"[verifier] submission {sub_id} still judging...")
        if time.time() >= deadline:
            infra_fail(f"judging did not finish within {POLL_TIMEOUT:.0f}s")


def fetch_archive(sid, archive_token):
    """Pull this session's raw-record archive. A 404 here is NOT a 'gone'
    case like in fetch_best: the session is fresh, held by our TTL, and the
    polling above already aggregated its /submissions (which is what writes
    the archive) — so a 404 means a broken credential or a service defect,
    i.e. infrastructure. 401/403 likewise. A terminal 410 (session destroyed
    server-side, v0.6.18) infra-fails at once. Other failures retry 3 times."""
    url = f"{SERVICE_BASE}/v1/judge/sessions/{sid}/archive"
    headers = {"X-TCSEXAM-Archive-Token": archive_token}
    last_exc = None
    for attempt in range(1, ARCHIVE_RETRIES + 1):
        try:
            return http_get_json(url, extra_headers=headers)
        except urllib.error.HTTPError as exc:
            if terminal_destroyed(exc):
                terminal_fail(f"archive for the verifier session {sid} unattainable")
            if exc.code == 404:
                infra_fail(f"archive for the fresh verifier session {sid} answered 404 "
                           "(a wrong archive credential presents exactly like this)")
            if exc.code in (401, 403):
                infra_fail(f"auth rejected by the judging service (HTTP {exc.code})")
            last_exc = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
        if attempt < ARCHIVE_RETRIES:
            time.sleep(ARCHIVE_RETRY_BACKOFF * attempt)
    infra_fail(f"cannot pull the archive for session {sid} after "
               f"{ARCHIVE_RETRIES} attempts: {last_exc}")


def destroy_session(sid):
    """Best-effort teardown: the session's work is done (records archived
    service-side), so it is destroyed here instead of being left to the
    reaper. The submission journal entry — the reconciliation evidence —
    lives in the service's append-only ledger and survives the destroy."""
    try:
        code, _ = http_call("DELETE", f"{SERVICE_BASE}/v1/judge/sessions/{sid}", timeout=30)
        if code == 200:
            print(f"[verifier] session {sid} destroyed")
        else:
            print(f"[verifier] WARNING: destroy of session {sid} answered HTTP {code}; "
                  "the reaper will collect it at TTL", file=sys.stderr)
    except Exception as exc:
        print(f"[verifier] WARNING: destroy of session {sid} failed ({exc}); "
              "the reaper will collect it at TTL", file=sys.stderr)


def _is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def merge_submissions(archives, include_public=False):
    """Merge the session archives' shard payloads into per-submission
    candidates — same rules as fetch_best: submissions align across shards by
    index; a timeout / build_error entry (the model's own fault) folds its
    whole shard slice in as invalid records; a judge_error / records-less
    entry (infrastructure) is skipped so its slice simply does not vote. A
    submission whose slices are ALL missing to infrastructure is skipped
    outright; one lost entirely to the model's own faults scores as an
    all-invalid 0.0 candidate.

    Archives whose instance_set is not "hidden" are skipped UNLESS
    include_public — the verifier's own session is merged with
    include_public=False (never score public judging as the final run), the
    declared self-test chain with include_public=True. Every candidate
    carries "channel" (the session's instance_set) so the scoring step can
    tell the final judging, public self-tests, and agent-side hidden
    sessions apart."""
    candidates = []
    notes = []
    for sid, body in sorted(archives.items()):
        if not isinstance(body, dict):
            notes.append(f"{sid}: malformed archive body (not an object); session skipped")
            continue
        instance_set = str(body.get("instance_set") or "hidden")
        if instance_set != "hidden" and not include_public:
            # This verifier only ever creates hidden-set sessions; a public
            # archive here would mean the judging service crossed sessions —
            # never score public judging as the final run.
            notes.append(f"{sid}: archive instance_set={body.get('instance_set')!r} is not "
                         "hidden; session skipped")
            continue
        payloads = body.get("shard_payloads") or {}
        n_shards = int(body.get("n_shards") or len(payloads) or 1)
        failed_shards = body.get("failed_shards") or {}
        worker_payloads = {}
        for key, payload in sorted(payloads.items(), key=lambda kv: int(kv[0])):
            if isinstance(payload, dict) and isinstance(payload.get("submissions"), list):
                worker_payloads[int(key)] = payload["submissions"]
        # Learn each shard's constant judging slice from its first records.
        slice_cache = {}
        for idx, subs in worker_payloads.items():
            for entry in subs:
                recs = entry.get("records") if isinstance(entry, dict) else None
                if isinstance(recs, list):
                    slice_cache[idx] = [str(r.get("instance")) for r in recs
                                        if isinstance(r, dict)]
                    break
        count = max((len(subs) for subs in worker_payloads.values()), default=0)
        if count == 0:
            notes.append(f"{sid}: archive carries no submissions")
        for k in range(count):
            cand = {"key": f"{sid}#{k}", "channel": instance_set, "records": [],
                    "synthesized_invalid": 0,
                    "infra_missing": [], "model_fault_missing": 0}
            for idx in range(n_shards):
                subs = worker_payloads.get(idx)
                entry = subs[k] if subs is not None and k < len(subs) else None
                if idx in failed_shards and entry is None:
                    cand["infra_missing"].append(
                        {"shard": idx, "reason": f"failed shard ({failed_shards[idx]}), "
                                                 "no archived entry for this submission"})
                    continue
                if entry is None:
                    cand["infra_missing"].append(
                        {"shard": idx, "reason": "no archived entry for this submission"})
                    continue
                status = str(entry.get("status"))
                recs = entry.get("records")
                detail = str(entry.get("detail") or "")
                if status == "ok" and isinstance(recs, list):
                    cand["records"].extend(r for r in recs if isinstance(r, dict))
                elif status == "timeout" or (status == "ok" and detail == "build_error"):
                    # The model's own overrun / build crash: the whole slice
                    # folds in as invalid (mirrors the service's five-number
                    # fold into ``worse``).
                    instances = slice_cache.get(idx)
                    if instances is None:
                        cand["model_fault_missing"] += 1
                        cand["infra_missing"].append(
                            {"shard": idx, "reason": f"{status or detail}: slice instances "
                                                     "unknowable (shard never reported records)"})
                    else:
                        cand["records"].extend(
                            {"instance": name, "A": None, "status": "invalid",
                             "detail": f"slice fold-in: {detail or status}"}
                            for name in instances)
                        cand["synthesized_invalid"] += len(instances)
                elif status == "running":
                    cand["infra_missing"].append(
                        {"shard": idx, "reason": "submission still judging when the "
                                                 "archive was pulled"})
                else:
                    # judge_error, or an ok entry without records that is not
                    # a build error: a judging-pipeline fault — never blamed
                    # on the model.
                    cand["infra_missing"].append(
                        {"shard": idx, "reason": f"judging-pipeline fault ({status}: {detail})"})
            _finalize_candidate(cand)
            candidates.append(cand)
    return candidates, notes


def _finalize_candidate(cand):
    """A submission with zero usable records is still a candidate (score
    0.0) when the loss is entirely the model's own fault; it is skipped when
    infrastructure swallowed (part of) it."""
    if cand["records"]:
        cand["skipped"] = False
        cand["skip_reason"] = None
    elif cand["model_fault_missing"] or cand["synthesized_invalid"]:
        cand["skipped"] = False
        cand["skip_reason"] = None
    else:
        cand["skipped"] = True
        cand["skip_reason"] = ("no usable records: " +
                               "; ".join(m["reason"] for m in cand["infra_missing"])) \
            if cand["infra_missing"] else "no submissions in archive"


def adapt_anchors(anchors, config):
    """Drop anchors the metric cannot place, with reasons
    (anchor_not_numeric / anchor_inverted / anchor_direction_mismatch).
    B==K anchors are KEPT: the engine itself excludes them with an explicit
    record, which doubles as a cross-check against the worker's exclusion."""
    adapted = {"B": {}, "K": {}}
    issues = []
    shape = config["shape"]
    direction = config.get("direction")
    for inst in sorted(set(anchors["B"]) | set(anchors["K"])):
        b = anchors["B"].get(inst)
        k = anchors["K"].get(inst)
        if not _is_num(b) or not _is_num(k):
            issues.append({"instance": inst, "reason": "anchor_not_numeric", "B": b, "K": k})
            continue
        if b != k:
            if shape == "solve_rate" and int(bool(k)) < int(bool(b)):
                issues.append({"instance": inst, "reason": "anchor_inverted", "B": b, "K": k})
                continue
            # solve_rate_all_keys (since 260917): anchors are reference information only and do not enter the formula.
            # Inverted items are scored as usual (solved=1); there is no anchor_inverted exclusion.
            if shape == "gap_ratio" and ((direction == "max" and k < b)
                                         or (direction == "min" and k > b)):
                issues.append({"instance": inst, "reason": "anchor_direction_mismatch",
                               "B": b, "K": k})
                continue
        adapted["B"][inst] = b
        adapted["K"][inst] = k
    return adapted, issues


def clean_records(records, adapted_anchors, anchor_check=True):
    """Normalize raw records for the engine and drop ones without a usable
    anchor. A record whose B/K contradicts the verifier-side anchors is kept
    but flagged (anchor_mismatch) — the local anchors win, the flag catches a
    judging-side anchor drift."""
    clean = []
    issues = []
    for rec in records:
        inst = rec.get("instance")
        if inst is None or str(inst) not in adapted_anchors["B"]:
            issues.append({"instance": inst, "reason": "record_without_anchor"})
            continue
        inst = str(inst)
        status = str(rec.get("status") or "ok")
        a = rec.get("A")
        if status == "ok" and not _is_num(a):
            status = "error"
        out = {"instance": inst, "A": a if _is_num(a) else None,
               "status": status if status in ("ok", "invalid", "error") else "invalid",
               "detail": str(rec.get("detail") or "")}
        if anchor_check and status == "ok":
            b, k = adapted_anchors["B"][inst], adapted_anchors["K"][inst]
            rb, rk = rec.get("B"), rec.get("K")
            if (_is_num(rb) and _is_num(rk)) and (rb != b or rk != k):
                issues.append({"instance": inst, "reason": "anchor_mismatch",
                               "record_B": rb, "record_K": rk, "anchor_B": b, "anchor_K": k})
        clean.append(out)
    return clean, issues


def load_metric_stack():
    """Import the task's vendored metric engine (tests/metric/), keeping the
    import out of module scope so unit tests can stub it."""
    metric_dir = os.path.join(TESTS_DIR, "metric")
    if not os.path.isdir(metric_dir):
        infra_fail(f"metric engine copy missing at {metric_dir} (packaging defect)")
    sys.path.insert(0, metric_dir)
    import engine as metric_engine
    import config as metric_config
    return metric_engine, metric_config


def load_metric_task(metric_config_module):
    """Read tests/metric_config.json + the anchors file it points at."""
    config_path = os.path.join(TESTS_DIR, "metric_config.json")
    if not os.path.isfile(config_path):
        infra_fail(f"metric config missing at {config_path}: this task has no "
                   "per-instance anchors to recompute a score from")
    try:
        return metric_config_module.load_task(config_path)
    except Exception as exc:
        infra_fail(f"metric config/anchors invalid: {exc}")


def reap_agent_keepalive():
    """Terminate the agent-phase session keepalive left over from submit.sh.

    260916 (fcs root-cause correction): submit.sh's `start_keepalive` runs
    `setsid bash -c 'KAUTH=...'` — detached from the task lifecycle, it keeps
    pinging /submissions every 10 minutes even after the container finishes,
    which refreshes last_active and defeats the service-side idle reaper
    (stale sessions accumulate sandboxes; hit 63 TB once). The verifier phase
    starting means the agent phase is over, so the keepalive's job is done;
    reap it here so the session's idle clock becomes honest again. The match
    string combines two literals that only co-occur in the keepalive's
    `bash -c` command line (the unexpanded ${...} form), so it cannot hit
    this verifier, test.sh, or anything else in the container.
    """
    try:
        proc = subprocess.run(
            ["pkill", "-f", "KAUTH.*X-TCSEXAM-Token-Id"],
            check=False, capture_output=True, text=True, timeout=15)
        note = "reaped" if proc.returncode == 0 else "none found"
        print(f"[verifier] agent-phase keepalive: {note}", file=sys.stderr)
    except Exception as exc:  # pkill missing or failed: harmless, keep going
        print(f"[verifier] keepalive reaping skipped ({exc})", file=sys.stderr)


def main():
    reap_agent_keepalive()
    os.makedirs(os.path.dirname(REWARD_JSON), exist_ok=True)
    os.makedirs(os.path.dirname(ARTIFACT), exist_ok=True)

    if not SERVICE_BASE:
        infra_fail("TCSEXAM_BASE_URL is not set; configure your TCSEXAM judge backend")

    if not TOKEN_ID or not TOKEN_SECRET:
        infra_fail("TCSEXAM_TOKEN_ID/TCSEXAM_TOKEN_SECRET not set in the verifier phase")

    token_path = os.path.join(TESTS_DIR, "archive_token")
    archive_token = os.environ.get("TCSEXAM_ARCHIVE_TOKEN", "").strip()
    if not archive_token:
        try:
            with open(token_path) as f:
                archive_token = f.read().strip()
        except OSError as exc:
            infra_fail(f"archive credential unreadable at {token_path}: {exc}")
    if not archive_token:
        infra_fail(f"archive credential empty at {token_path} (packaging defect)")

    if not os.path.isdir(APP_DIR):
        infra_fail(f"{APP_DIR} missing: the agent tree to judge does not exist")

    tarball = pack_app()
    sid = None
    own_submissions = 0  # hidden submissions THIS verifier got accepted (0 or 1)
    # The accounting unit (contract v1.2): the run's DECLARED session
    # chain plus this verifier's own session — the chain is read once
    # here (the agent phase is over, so the file is final) and our own
    # session is added in memory at reconciliation time; the chain file
    # itself keeps its agent-declared meaning.
    declared = read_declared_sessions()
    if os.environ.get("TCSEXAM_CLOSE_AGENT_SESSIONS") == "1":
        # Archives and the ownership ledger survive DELETE. Release this
        # run's declared public workers before the serial final session.
        for previous_session in declared or []:
            destroy_session(previous_session)
    try:
        for shard_attempt in range(FAILED_SHARD_RETRIES + 1):
            sid = create_session(archive_token)
            sub_id = submit_once(sid, tarball)
            if sub_id is None:
                # 429: this session's per-session cap was already exhausted
                # before our first upload. Our session is fresh and unique to
                # this container (X-TCSEXAM-Client-Id disambiguates the create
                # singleflight), so the accepted submissions the cap counted
                # are agent-side evidence — the agent flooded submissions into
                # the verifier's session or merged its own into it. Our
                # submission was NOT accepted, so every hidden submission the
                # chain reconciliation counts (declared agent sessions plus
                # this one) is agent-side: any count at all is the violation.
                recon = chain_hidden_reconciliation(declared, sid, archive_token)
                if recon is not None and recon["total"] > 0:
                    write_violation(recon["total"], own_submissions,
                                    note="agent exhausted the hidden-channel submission cap",
                                    chain=recon["sessions"],
                                    agent_hidden=recon["agent_hidden"])
                else:
                    infra_fail("submit was cap-rejected (429) but the chain "
                               "reconciliation shows total_submissions="
                               f"{recon['total'] if recon is not None else None}: "
                               "judging-service state inconsistent")
                return
            own_submissions = 1
            merged_entry = poll_until_done(sid, sub_id)
            failed_shards = int(merged_entry.get("failed_shards") or 0)
            if failed_shards == 0:
                break
            if shard_attempt < FAILED_SHARD_RETRIES:
                print(f"[verifier] {failed_shards} shard(s) died mid-judging; "
                      f"restarting the whole judging in a fresh session "
                      f"(retry {shard_attempt + 1}/{FAILED_SHARD_RETRIES})",
                      file=sys.stderr)
                destroy_session(sid)
                sid = None
                own_submissions = 0
                continue
            infra_fail(f"judging lost {failed_shards} shard(s) mid-judging on "
                       f"{FAILED_SHARD_RETRIES + 1} consecutive attempts")
        body = fetch_archive(sid, archive_token)

        final_candidates, merge_notes = merge_submissions({sid: body})
        archive = {
            "sessions": {sid: body},
            "merge_notes": merge_notes,
            "merged_submissions": [
                {"key": c["key"], "channel": c["channel"], "records": c["records"],
                 "synthesized_invalid": c["synthesized_invalid"],
                 "infra_missing": c["infra_missing"], "skipped": c["skipped"],
                 "skip_reason": c["skip_reason"]}
                for c in final_candidates
            ],
        }
        with open(ARTIFACT, "w") as f:
            json.dump(archive, f, indent=1, sort_keys=True)
        print(f"[verifier] archived raw submission records to {ARTIFACT}")

        # Hidden-channel reconciliation (contract v1.2, BEFORE any metric
        # computation): in form 1 the only legitimate hidden submission is
        # this verifier's one, so any accepted hidden submission on a
        # DECLARED agent session means the agent called the hidden channel
        # itself — a scoring verdict (reward 0.0, exit 0), never an
        # infrastructure failure; a failed reconciliation query never voids
        # the run. The retired client_ip total is queried afterwards as
        # ops telemetry only.
        recon = chain_hidden_reconciliation(declared, sid, archive_token)
        if recon is not None and recon["agent_hidden"] > 0:
            write_violation(recon["total"], own_submissions,
                            chain=recon["sessions"],
                            agent_hidden=recon["agent_hidden"])
            return
        channel_check = "ok" if recon is not None else "skipped_service_unreachable"
        client_ip_total = client_ip_total_observed(archive_token)

        if not final_candidates:
            infra_fail(f"the archive of verifier session {sid} carries no submissions "
                       "though our submission completed; the raw records are "
                       "unrecoverable")

        # Public self-test history (step 6 of the module docstring): the
        # declared chain and its reconciliation are already in hand from
        # the violation check (the reconciliation doubles as the audit
        # trail); pull each declared session's archive. Nothing in this
        # phase voids the run — the history merge can only raise the reward.
        chain_recon = recon
        history_archives = {}
        history_gone = []
        if declared:
            print(f"[verifier] {len(declared)} declared self-test session(s): {declared}")
            for hsid in declared:
                if hsid == sid:
                    continue  # impossible (fresh id); never re-read our own
                outcome, hbody = fetch_history_archive(hsid, archive_token)
                if outcome == "gone":
                    history_gone.append(hsid)
                else:
                    history_archives[hsid] = hbody
            if history_gone:
                print(f"[verifier] {len(history_gone)} declared session(s) gone from "
                      f"the service: {history_gone}")
        else:
            print("[verifier] no session chain file: the agent never self-tested; "
                  "the final judging alone decides the score")
        history_candidates, history_notes = merge_submissions(history_archives,
                                                              include_public=True)
        merge_notes = merge_notes + history_notes

        # Rewrite the artifact with the history archives folded in (the
        # full-channel record next-steps-260911.md §E mandates).
        archive["sessions"].update(history_archives)
        archive["gone_history_sessions"] = history_gone
        if chain_recon is not None:
            archive["history_chain"] = chain_recon
        archive["merged_submissions"].extend(
            {"key": c["key"], "channel": c["channel"], "records": c["records"],
             "synthesized_invalid": c["synthesized_invalid"],
             "infra_missing": c["infra_missing"], "skipped": c["skipped"],
             "skip_reason": c["skip_reason"]}
            for c in history_candidates
        )
        with open(ARTIFACT, "w") as f:
            json.dump(archive, f, indent=1, sort_keys=True)

        metric_engine, metric_config_module = load_metric_stack()
        config, anchors = load_metric_task(metric_config_module)
        adapted, anchor_issues = adapt_anchors(anchors, config)

        def score_candidates(cands, lane):
            """Score merged candidates with the metric engine. lane "final":
            the verifier's own judging. lane "history": the declared chain's
            submissions — public self-tests score only under HISTORY_BEST;
            an agent-side hidden session never scores (its submissions are
            step-5 violation evidence)."""
            entries = []
            lane_best = None
            lane_best_detail = None
            scored = 0
            for cand in cands:
                if cand["skipped"]:
                    entries.append({"key": cand["key"], "channel": cand["channel"],
                                    "skipped": True, "skip_reason": cand["skip_reason"]})
                    continue
                if lane == "history" and cand["channel"] != "public":
                    entries.append({"key": cand["key"], "channel": cand["channel"],
                                    "skipped": True,
                                    "skip_reason": "agent-side hidden session: its submissions "
                                                   "are hidden-channel reconciliation evidence, "
                                                   "never scored"})
                    continue
                if lane == "history" and not HISTORY_BEST:
                    entries.append({"key": cand["key"], "channel": cand["channel"],
                                    "skipped": True,
                                    "skip_reason": "public self-test history (this task's score "
                                                   "is the final judging only)"})
                    continue
                records, record_issues = clean_records(cand["records"], adapted)
                if not records:
                    if cand["synthesized_invalid"] or cand["model_fault_missing"]:
                        result = {"score": 0.0, "detail": {"all_model_fault": True}}
                    else:
                        entries.append({"key": cand["key"], "channel": cand["channel"],
                                        "skipped": True,
                                        "skip_reason": "no scorable records after anchor filtering"})
                        continue
                else:
                    try:
                        result = metric_engine.compute_metric(records, adapted, config)
                    except metric_engine.MetricConfigError as exc:
                        infra_fail(f"metric engine rejected the inputs for {cand['key']}: {exc}")
                score = float(result["score"])
                scored += 1
                entry = {"key": cand["key"], "channel": cand["channel"], "score": score}
                if isinstance(result.get("detail"), dict) and result["detail"].get("counts"):
                    entry["counts"] = result["detail"]["counts"]
                if cand["synthesized_invalid"]:
                    entry["synthesized_invalid"] = cand["synthesized_invalid"]
                if cand["infra_missing"]:
                    entry["infra_missing"] = cand["infra_missing"]
                if record_issues:
                    entry["record_issues"] = record_issues
                entries.append(entry)
                cand["metric_result"] = result
                if lane_best is None or score > lane_best:
                    lane_best = score
                    lane_best_detail = (result.get("detail")
                                        if isinstance(result.get("detail"), dict) else None)
            return entries, lane_best, lane_best_detail, scored

        final_entries, final_best, final_best_detail, final_scored = \
            score_candidates(final_candidates, "final")
        if final_scored == 0:
            infra_fail("the submission produced no scorable records (every slice was lost "
                       "to judging-pipeline faults); the score is unrecoverable")
        history_entries, history_best, history_best_detail, history_scored = \
            score_candidates(history_candidates, "history")
        per_submission = final_entries + history_entries

        # The merge caliber: best(public self-test history, final judging)
        # when HISTORY_BEST; the final judging alone otherwise.
        if HISTORY_BEST and history_best is not None and history_best > final_best:
            reward = history_best
            reward_detail = history_best_detail
            score_source = "public_history"
        else:
            reward = final_best
            reward_detail = final_best_detail
            score_source = "final"

        # Rewrite the artifact with the metric detail appended so the full
        # scoring trail is replayable offline.
        for entry, cand in zip(archive["merged_submissions"],
                               final_candidates + history_candidates):
            if cand.get("metric_result") is not None:
                entry["metric_result"] = cand["metric_result"]
        with open(ARTIFACT, "w") as f:
            json.dump(archive, f, indent=1, sort_keys=True)

        # Archive every session's submission bodies verbatim (the exact
        # solver tars each side uploaded) and fold the manifest into the
        # artifact — best-effort audit evidence, never affects the reward.
        archive["submission_payloads"] = archive_submission_payloads(
            list(archive["sessions"].keys()), archive_token)
        with open(ARTIFACT, "w") as f:
            json.dump(archive, f, indent=1, sort_keys=True)
        print(f"[verifier] submission payloads: "
              f"{sum(len(e['archived']) for e in archive['submission_payloads']['sessions'].values())} archived, "
              f"{sum(len(e['unavailable']) for e in archive['submission_payloads']['sessions'].values())} unavailable")

        history_info = {
            "declared_sessions": len(declared or []),
            "sessions_reached": len(history_archives),
            "submissions": len(history_candidates),
            "gone_sessions": history_gone,
            "chain_check": ("no_declared_chain" if not declared
                            else "ok" if chain_recon is not None
                            else "skipped_service_unreachable"),
        }
        if chain_recon is not None:
            history_info["chain"] = chain_recon["sessions"]
        if HISTORY_BEST:
            history_info["score"] = (None if history_best is None
                                     else float(history_best))
        extra = {
            "hidden_channel_check": channel_check,
            "client_ip_total_observed": client_ip_total,
            "history_best": HISTORY_BEST,
            "score_source": score_source,
            "final_score": float(final_best),
            "history": history_info,
            "shape": config["shape"],
            "metric_version": getattr(metric_engine, "METRIC_VERSION", "unknown"),
            "provisional": bool(getattr(metric_engine, "PROVISIONAL", False)),
            "per_submission": per_submission,
            "anchor_issues": anchor_issues,
            "merge_notes": merge_notes,
        }
        # Per-instance contribution detail of the winning submission,
        # straight from the metric engine (instances / excluded / zeroed /
        # counts).
        if isinstance(reward_detail, dict):
            for key in ("instances", "excluded", "zeroed", "counts"):
                if key in reward_detail:
                    extra["per_instance" if key == "instances" else key] = reward_detail[key]
        write_reward(reward, note="ok", extra=extra)
    finally:
        if sid is not None:
            destroy_session(sid)
        try:
            os.remove(tarball)
        except OSError:
            pass


def _write_json_atomic(path, payload):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=directory, prefix=".tcsexam-reward-", delete=False) as stream:
            temporary = stream.name
            json.dump(payload, stream, indent=1, sort_keys=True)
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.remove(temporary)


def _write_harbor_result(out):
    """Keep Harbor's reward numeric and preserve the complete judging detail."""
    import math
    reward = out.get("reward")
    if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward):
        raise ValueError("Harbor reward must be a finite number")
    detail_path = os.environ.get("SCORE_DETAILS_JSON") or os.path.join(
        os.path.dirname(os.path.abspath(REWARD_JSON)), "score-details.json")
    if os.path.abspath(detail_path) in {os.path.abspath(REWARD_JSON), os.path.abspath(REWARD_TXT)}:
        raise ValueError("Score details and numeric reward must use separate paths")
    # Write full provenance first. A detail-write failure cannot create a zero reward.
    _write_json_atomic(detail_path, out)
    directory = os.path.dirname(os.path.abspath(REWARD_TXT))
    os.makedirs(directory, exist_ok=True)
    with open(REWARD_TXT, "w") as stream:
        stream.write(str(float(reward)))
    # Harbor 0.22 treats every top-level reward value as a separate numeric metric.
    _write_json_atomic(REWARD_JSON, {"reward": float(reward)})


def write_violation(total, own_submissions, note=None, chain=None, agent_hidden=None):
    out = {
        "reward": 0.0,
        "violation": "hidden_channel_used_by_agent",
        "total_submissions": total,
        "verifier_submissions": float(own_submissions),
    }
    if agent_hidden is not None:
        out["agent_hidden_submissions"] = agent_hidden
    if chain is not None:
        out["chain"] = chain
    if note:
        out["note"] = note
    _write_harbor_result(out)
    print(f"[verifier] VIOLATION hidden_channel_used_by_agent: declared-chain "
          f"total_submissions={total} (agent-side hidden={agent_hidden}) > the "
          f"verifier's own {own_submissions}; reward 0.0")


def write_reward(best, note, extra=None):
    out = {
        "reward": float(best),
        "best": float(best),
        "note": note,
    }
    if extra:
        out.update(extra)
    _write_harbor_result(out)
    print(f"[verifier] reward={best} (note={note})")

if __name__ == "__main__":
    main()
