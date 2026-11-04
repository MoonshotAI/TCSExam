#!/bin/bash
# submit.sh — coloring-dimacs: self-test client for the TCSExam judging service
# (form 2: 168 public practice instances + 72 hidden judged instances).
# This script judges your solver on the PUBLIC practice set — unlimited
# use. After the run ends, the verifier rebuilds the solver tree you leave in
# /app and judges it EXACTLY ONCE on the hidden instances; that single final
# judging is your score — self-tests never affect your score (no best-of).
#
# Usage:  submit.sh [solver_dir]     (default /app)
#
# The script creates a public judge session on first use, reuses it on later
# calls (the session id is kept in /app/.session_public_id), uploads a tar of
# the solver tree, then polls until judging finishes and prints the
# per-instance detail: instance name, your value A, and the validity status.
# Every judge session it creates is appended to the session chain
# /app/.judge_sessions — do not delete that file: the final scoring step
# scores only submissions in the declared chain.
set -euo pipefail

SERVICE_BASE="${TCSEXAM_BASE_URL:?Set TCSEXAM_BASE_URL to your TCSEXAM judge backend}"
JUDGE_IMAGE="${TCSEXAM_JUDGE_IMAGE:?Set TCSEXAM_JUDGE_IMAGE to the prepared backend image digest}"
N_SHARDS="${TCSEXAM_N_SHARDS:-10}"  # Prepared concurrency; pool tasks must remain one shard.
SESSION_FILE="${TCSEXAM_SESSION_FILE:-/app/.session_public_id}"
KEEPALIVE_PIDFILE="${TCSEXAM_KEEPALIVE_PIDFILE:-/app/.submit_keepalive.pid}"
CHAIN_FILE="${TCSEXAM_CHAIN_FILE:-/app/.judge_sessions}"
SRC_DIR="${1:-/app}"
SESSION_TTL="${TCSEXAM_SESSION_TTL:-46800}"  # seconds: 12-hour development budget plus 1-hour margin
POLL_INTERVAL="${TCSEXAM_POLL_INTERVAL:-60}"  # seconds between status requests
POLL_TIMEOUT="${TCSEXAM_POLL_TIMEOUT:-9000}"  # seconds to wait for one submission

STORAGE_RESOURCE=""
if [ -n "${TCSEXAM_WORKER_STORAGE_MB:-}" ]; then
  STORAGE_LIMIT="$TCSEXAM_WORKER_STORAGE_MB"
  case "$STORAGE_LIMIT" in
    none|null) STORAGE_LIMIT=null ;;
    *[!0-9]*|"") echo "TCSEXAM_WORKER_STORAGE_MB must be positive MiB or null" >&2; exit 2 ;;
    *) [ "$STORAGE_LIMIT" -gt 0 ] || exit 2 ;;
  esac
  STORAGE_RESOURCE=",\"storage_mb\":$STORAGE_LIMIT"
fi

: "${TCSEXAM_TOKEN_ID:?TCSEXAM_TOKEN_ID is not set in the environment}"
: "${TCSEXAM_TOKEN_SECRET:?TCSEXAM_TOKEN_SECRET is not set in the environment}"
AUTH=(-H "X-TCSEXAM-Token-Id: ${TCSEXAM_TOKEN_ID}" -H "X-TCSEXAM-Token-Secret: ${TCSEXAM_TOKEN_SECRET}")
# TCSEXAM identity headers use an explicit per-attempt identifier when supplied.
# A stable container hostname is the fallback. The backend must isolate clients
# by this identity, including clients sharing a network egress address.
ATTRIB_RUN_ID="${TCSEXAM_RUN_ID:-${HOSTNAME:-}}"
[ -n "$ATTRIB_RUN_ID" ] && AUTH+=(-H "X-TCSEXAM-Run-Id: $ATTRIB_RUN_ID")
[ -n "$ATTRIB_RUN_ID" ] && AUTH+=(-H "X-TCSEXAM-Client-Id: $ATTRIB_RUN_ID")
[ -n "${TCSEXAM_AGENT_NAME:-}" ] && \
  AUTH+=(-H "X-TCSEXAM-Agent-Name: ${TCSEXAM_AGENT_NAME}")

# v0.6.18: a session destroyed server-side answers HTTP 410 Gone with body
# {"error_class":"terminal"} — final, not transient. Stop at once instead of
# burning the retry/poll budget on a session that will never come back.
# (404 keeps the original retry handling below.)
stop_if_terminal() {  # $1 = http code, $2 = response body
  if [ "$1" = "410" ] || printf '%s' "$2" | grep -q '"error_class" *: *"terminal"'; then
    echo "[submit] the judging session was destroyed server-side (http $1):" >&2
    echo "[submit] The judging session was destroyed by the service; this submission is void — final, not transient; not retried." >&2
    exit 1
  fi
}

session_alive() {  # $1 = session id
  curl -sf --max-time 30 "${AUTH[@]}" "$SERVICE_BASE/v1/judge/sessions/$1" >/dev/null 2>&1
}

# Hibernate stopgap (260923, public self-test channel only): a HIBERNATED
# session (server-side idle sleep) is treated as gone — forget the local id
# and create a fresh session. Until a service update already in flight
# lands, reusing a hibernated session routes through a wake path that can
# misalign submission numbering and serve stale results; the fresh session
# re-judges from scratch (the accepted cost — the old session's results
# stay in the session chain). Hidden sessions are NEVER auto-recreated:
# the submission cap counts per session and the run-level 10-cap is
# reconciled over the declared chain, so recreating one breaks that
# accounting.
session_hibernated() {  # $1 = session id -> "yes" if hibernated ("no" on query failure)
  curl -s --max-time 30 "${AUTH[@]}" "$SERVICE_BASE/v1/judge/sessions/$1" 2>/dev/null \
    | python3 -c 'import json,sys; print("yes" if json.load(sys.stdin).get("status") == "hibernated" else "no")' 2>/dev/null \
    || echo no
}

# Degraded-session guard (260923): a shard can die after the ready flip
# (tunnel drop / sandbox crash); the service keeps the session alive with
# failed_shards>0 and every submission on it then silently misses the dead
# shard's instances (260923 full9: a celar public session lost the shard
# holding graph11.dzn — 12 of 13 instances for every solver on it; a maxcut
# public session lost shard 6 mid-judging — 95 of 105 records on two
# submissions, missing exactly that shard's modulo slice). The public
# self-test channel is uncapped, so a degraded session is destroyed and
# rebuilt, never reused. Hidden sessions are NEVER rebuilt here: the
# submission cap counts per session and the run-level 10-cap is reconciled
# over the declared chain, so rebuilding one breaks that accounting.
session_failed_shards() {  # $1 = session id -> failed-shard count ("0" on query failure)
  curl -s --max-time 30 "${AUTH[@]}" "$SERVICE_BASE/v1/judge/sessions/$1" 2>/dev/null \
    | python3 -c 'import json,sys; print(int(json.load(sys.stdin).get("failed_shards") or 0))' 2>/dev/null \
    || echo 0
}

destroy_session() {  # $1 = session id; best effort (submission history survives service-side)
  curl -s --max-time 30 -X DELETE "${AUTH[@]}" "$SERVICE_BASE/v1/judge/sessions/$1" >/dev/null 2>&1 || true
}

# ensure_session stays untouched; this wrapper checks the session it
# returns (reused or fresh) and replaces it when degraded. Final packages
# run the guard on their only (public) channel unconditionally; async
# packages only when PUBLIC=1 — the hidden channel skips it entirely.
ensure_session_with_guard() {
  ensure_session
  if [ "${PUBLIC:-1}" != "1" ]; then
    return
  fi
  local rebuild=0 fsh=0 sess_file="${PUBLIC_SESSION_FILE:-$SESSION_FILE}"
  while true; do
    fsh="$(session_failed_shards "$SID")"
    if [ "$fsh" = "0" ]; then
      return
    fi
    if [ $rebuild -ge 2 ]; then
      echo "[submit] WARNING: session $SID still has $fsh failed shard(s) after 2 rebuilds;" >&2
      echo "[submit] continuing anyway — results may be missing the dead shard's instances." >&2
      return
    fi
    rebuild=$((rebuild + 1))
    echo "[submit] WARNING: session $SID has $fsh failed shard(s); submissions on it miss" >&2
    echo "[submit] the dead shard's instances. Destroying it and creating a fresh session ($rebuild/2)..." >&2
    destroy_session "$SID"
    rm -f "$sess_file"
    ensure_session
  done
}


wait_ready() {  # $1 = session id; poll until the session is usable
  local sid="$1" tries=0 status="" detail=""
  while [ $tries -lt 120 ]; do
    local body code rfile
    rfile="$(mktemp /tmp/submit-sess-XXXXXX)"
    code="$(curl -s --max-time 30 -o "$rfile" -w "%{http_code}" "${AUTH[@]}" \
        "$SERVICE_BASE/v1/judge/sessions/$sid" 2>/dev/null)" || code="000"
    body="$(cat "$rfile")"; rm -f "$rfile"
    stop_if_terminal "$code" "$body"
    if [ "$code" = "200" ]; then
      # This service creates sessions synchronously: the session object has
      # NO status key, so GET 200 means ready. "status" only exists in the
      # core-package async-provisioning protocol (202); tolerate it if it
      # ever appears: ready/running pass, failed/dead/error fail, and a
      # missing status with tunnel_connected=false keeps waiting.
      status="$(printf '%s' "$body" | python3 -c \
        'import json,sys; d=json.load(sys.stdin); s=d.get("status"); print(("ready" if d.get("tunnel_connected", True) else "") if s is None else s)' 2>/dev/null || true)"
      case "$status" in
        ""|ready|running)
          return 0
          ;;
        failed|dead|error)
          detail="$(printf '%s' "$body" | python3 -c \
            'import json,sys; print(json.load(sys.stdin).get("detail",""))' 2>/dev/null || true)"
          echo "[submit] session $sid entered $status ($detail)" >&2
          return 1
          ;;
      esac
    fi
    sleep 15
    tries=$((tries + 1))
  done
  echo "[submit] session $sid still not ready after 30 min" >&2
  return 1
}

ensure_session() {
  if [ -f "$SESSION_FILE" ]; then
    SID="$(tail -n1 "$SESSION_FILE" | tr -d '[:space:]')"
    if [ -n "$SID" ] && session_alive "$SID"; then
      if [ "$(session_hibernated "$SID")" = "yes" ]; then
        echo "[submit] WARNING: previous session $SID is hibernated (server-side idle sleep)." >&2
        echo "[submit] Treating it as gone and creating a fresh session — the old session's" >&2
        echo "[submit] results stay in the session chain; re-judging happens on the fresh" >&2
        echo "[submit] session (an extra judging round, the accepted cost of the stopgap)." >&2
        rm -f "$SESSION_FILE"
      else
        return 0
      fi
    else
      echo "[submit] WARNING: previous session ${SID:-<none>} no longer exists;" >&2
      echo "[submit] its history is lost. Creating a fresh session." >&2
    fi
  fi
  echo "[submit] creating judge session (n_shards=$N_SHARDS)..." >&2
  local attempt=1 resp="" ok=0 code=""
  while [ $attempt -le 5 ]; do
    local rfile
    rfile="$(mktemp /tmp/submit-create-XXXXXX)"
    code="$(curl -s --max-time 2400 -o "$rfile" -w "%{http_code}" -X POST "${AUTH[@]}" \
        -H 'Content-Type: application/json' \
        -d "{\"judge_image\":\"$JUDGE_IMAGE\",\"ttl\":$SESSION_TTL,\"n_shards\":$N_SHARDS,\"instance_set\":\"public\",\"resources\":{\"cpu\":${TCSEXAM_WORKER_CPUS:-4},\"mem\":${TCSEXAM_WORKER_MEMORY_MB:-8192}${STORAGE_RESOURCE}}}" \
        "$SERVICE_BASE/v1/judge/sessions" 2>/dev/null)" || code="000"
    resp="$(cat "$rfile")"; rm -f "$rfile"
    stop_if_terminal "$code" "$resp"
    case "$code" in 2??) ok=1; break;; esac
    echo "[submit] session create attempt $attempt failed (http $code: $resp); retrying in 60s..." >&2
    sleep 60
    attempt=$((attempt + 1))
  done
  [ "$ok" = 1 ] || { echo "[submit] could not create a judge session after 5 attempts" >&2; exit 1; }
  SID="$(printf '%s' "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin)["session_id"])')"
  echo "$SID" >> "$SESSION_FILE"
  # Session chain (contract v1.2): every judge session this run
  # creates is appended here.
  echo "$SID" >> "$CHAIN_FILE"
  echo "[submit] session $SID created; waiting for it to become ready..." >&2
  wait_ready "$SID" || { echo "[submit] session failed to become ready" >&2; exit 1; }
  echo "[submit] session $SID ready" >&2
}

# The service reaps sessions idle for more than a few hours; a background
# refresher pings every session in the chain (plus the latest session of
# the legacy file) so a long stretch without self-tests does not lose
# the session history. Runs detached; harmless if it dies.
start_keepalive() {
  [ "${TCSEXAM_CLOSE_SESSION_AFTER_SUBMIT:-0}" = "1" ] && return 0
  if [ -f "$KEEPALIVE_PIDFILE" ] && kill -0 "$(cat "$KEEPALIVE_PIDFILE" 2>/dev/null)" 2>/dev/null; then
    return
  fi
  setsid bash -c '
    KAUTH=(-H "X-TCSEXAM-Token-Id: ${TCSEXAM_TOKEN_ID}"
           -H "X-TCSEXAM-Token-Secret: ${TCSEXAM_TOKEN_SECRET}")
    KRUN_ID="${TCSEXAM_RUN_ID:-${HOSTNAME:-}}"
    [ -n "$KRUN_ID" ] && KAUTH+=(-H "X-TCSEXAM-Run-Id: $KRUN_ID")
    [ -n "$KRUN_ID" ] && KAUTH+=(-H "X-TCSEXAM-Client-Id: $KRUN_ID")
    [ -n "${TCSEXAM_AGENT_NAME:-}" ] && \
      KAUTH+=(-H "X-TCSEXAM-Agent-Name: ${TCSEXAM_AGENT_NAME}")
    while sleep 600; do
      { [ -f "$0" ] && cat "$0"
        [ -f "$2" ] && tail -n1 "$2"
      } 2>/dev/null | tr -d " 	
" | sort -u | while read -r sid; do
        [ -n "$sid" ] || continue
        curl -sf --max-time 30 "${KAUTH[@]}" \
          "$1/v1/judge/sessions/$sid/submissions" >/dev/null 2>&1
      done
    done' "$CHAIN_FILE" "$SERVICE_BASE" "$SESSION_FILE" >/dev/null 2>&1 &
  echo $! > "$KEEPALIVE_PIDFILE"
}

# Pack the solver tree. The shipped public instances and reference colorings
# are static assets the judge does not need (it has its own hidden set), so
# they stay out of the upload; everything else in /app goes in. Keep any
# runtime assets YOUR solver needs outside ./instances and ./solutions.
# --- upload hygiene (2026-09-11) ---------------------------------------
# The judge re-runs `bash build.sh` and then runs your solver on ITS OWN
# instances — the upload only needs what those two steps use: source code,
# build inputs, and your solver's runtime assets. On top of the directory
# excludes above, the pack strips at any depth:
#   - VCS metadata and tool caches (.git, __pycache__, node_modules, .venv, ...)
#   - build byproducts and logs (*.o, *.pyc, *.log, ...)
# If this ever removes a file your solver genuinely needs at judging time,
# re-run with TCSEXAM_SUBMIT_PRUNE=0 to pack everything, and mention it in
# your notes so the filter can be fixed.
PRUNE_EXCLUDES=()
if [ "${TCSEXAM_SUBMIT_PRUNE:-1}" != "0" ]; then
  PRUNE_EXCLUDES=(
    --exclude='.git' --exclude='.svn' --exclude='.hg'
    --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.mypy_cache'
    --exclude='.ipynb_checkpoints' --exclude='node_modules'
    --exclude='.venv' --exclude='venv'
    --exclude='*.o' --exclude='*.obj' --exclude='*.pyc' --exclude='*.pyo'
    --exclude='*.log' --exclude='*.tmp'
    # this task's benchmark instance formats (local tuning data)
    --exclude='*.col'
  )
fi
# Packed submissions are capped at 200 MB: the service fans the upload out
# to every judging shard, so oversized packs are refused below before
# anything is sent. Override only for local dry-runs
# (TCSEXAM_SUBMIT_MAX_BYTES).
MAX_SUBMIT_BYTES="${TCSEXAM_SUBMIT_MAX_BYTES:-209715200}"
TARBALL="$(mktemp /tmp/submit-XXXXXX.tar.gz)"
cleanup_submission() {
  rm -f "$TARBALL"
  if [ "${TCSEXAM_CLOSE_SESSION_AFTER_SUBMIT:-0}" = "1" ] && [ -n "${SID:-}" ]; then
    destroy_session "$SID"
    rm -f "$SESSION_FILE"
  fi
}
trap cleanup_submission EXIT
tar -chzf "$TARBALL" -C "$SRC_DIR" \
  --exclude='./instances' --exclude='./solutions' \
  --exclude='./.session_public_id' --exclude='./.judge_sessions' --exclude='./.submit_keepalive.pid' \
  "${PRUNE_EXCLUDES[@]}" \
  .
SIZE="$(stat -c%s "$TARBALL")"
if [ "$SIZE" -gt "$MAX_SUBMIT_BYTES" ]; then
  SIZE_MB=$(( (SIZE + 1048575) / 1048576 ))
  cat <<EOF
[submit] SUBMISSION TOO LARGE: the packed solver tree is ${SIZE_MB} MB, over this task's 200 MB submission limit. This submission was NOT sent.

[submit] The judge only re-runs build.sh and your solver on its own instances, so the upload needs just what those two use: source code, build inputs, and runtime assets. Downloaded tuning instances, datasets, caches and build byproducts only inflate the upload — known junk and this task's instance formats are already stripped before packing (if that ever removes a file your solver needs, re-run with TCSEXAM_SUBMIT_PRUNE=0).

[submit] Largest entries under $SRC_DIR right now:
EOF
  ( cd "$SRC_DIR" 2>/dev/null && du -sm -- * .[!.]* 2>/dev/null | sort -rn | head -8 | sed 's/^/[submit]   /' ) || true
  cat <<EOF

[submit] Delete what the judge does not need (or move it out of $SRC_DIR), then submit again.
EOF
  exit 1
fi
echo "[submit] packed $SRC_DIR ($SIZE bytes)"

ensure_session_with_guard
start_keepalive
SESSION_URL="$SERVICE_BASE/v1/judge/sessions/$SID"
echo "[submit] submitting to session $SID..."

sattempt=1
while true; do
  SRESP_FILE="$(mktemp /tmp/submit-resp-XXXXXX)"
  SCODE="$(curl -s --max-time 600 -o "$SRESP_FILE" -w "%{http_code}" -X POST "${AUTH[@]}" \
    -H "Content-Type: application/gzip" --data-binary "@$TARBALL" \
    "$SESSION_URL/submit")" || SCODE="000"
  stop_if_terminal "$SCODE" "$(cat "$SRESP_FILE")"
  if [ "$SCODE" = "200" ] || [ "$SCODE" = "201" ] || [ "$SCODE" = "202" ]; then
    RESP="$(cat "$SRESP_FILE")"
    rm -f "$SRESP_FILE"
    break
  fi
  if [ "$SCODE" = "503" ] && [ $sattempt -le 5 ]; then
    echo "[submit] session still provisioning (503); retry $sattempt/5 in 60s..." >&2
    sleep 60
    sattempt=$((sattempt + 1))
    continue
  fi
  echo "[submit] submit failed (http $SCODE): $(cat "$SRESP_FILE")" >&2
  rm -f "$SRESP_FILE"
  exit 1
done
SUB_ID="$(printf '%s' "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["submission"])')"
echo "[submit] submission $SUB_ID accepted; judging runs on $N_SHARDS parallel shards over the public instances, polling..."

DEADLINE=$(( $(date +%s) + POLL_TIMEOUT ))
while true; do
  sleep "$POLL_INTERVAL"
  HRESP_FILE="$(mktemp /tmp/submit-hist-XXXXXX)"
  HCODE="$(curl -s --max-time 60 -o "$HRESP_FILE" -w "%{http_code}" "${AUTH[@]}" \
    "$SESSION_URL/submissions")" || HCODE="000"
  HIST="$(cat "$HRESP_FILE")"; rm -f "$HRESP_FILE"
  stop_if_terminal "$HCODE" "$HIST"
  [ "$HCODE" = "200" ] || continue
  LINE="$(printf '%s' "$HIST" | SUB_ID="$SUB_ID" python3 -c '
import json, os, sys
d = json.load(sys.stdin)
sid = int(os.environ["SUB_ID"])
subs = d["submissions"]
me = next((s for s in subs if s["submission"] == sid), None)
if me is None:
    print("missing")
elif me["status"] == "running":
    print("running ({} submission(s) so far)".format(len(subs)))
else:
    recs = me.get("records")
    if recs is None:
        print("done status={} detail={} (no per-instance records)".format(
            me["status"], me.get("detail", "")))
    else:
        by = {}
        for r in recs:
            by[r.get("status")] = by.get(r.get("status"), 0) + 1
        summ = " ".join("{}={}".format(k, by[k]) for k in sorted(by))
        lines = ["done status={} instances={} {}".format(me["status"], len(recs), summ)]
        for r in recs:
            det = (" — " + r["detail"]) if r.get("detail") else ""
            lines.append("  {} A={} {}{}".format(r.get("instance"), r.get("A"), r.get("status"), det))
        print("\n".join(lines))
    if me.get("pack_sha256"):
        print("pack sha256: " + str(me["pack_sha256"])[:12])
    print("fshards={}".format(int(me.get("failed_shards") or 0)))

')"
  case "$LINE" in
    done*)
      echo "[submit] $LINE"
      FSHARDS="$(printf '%s\n' "$LINE" | sed -n 's/^fshards=//p' | tail -1)"
      if [ -n "$FSHARDS" ] && [ "$FSHARDS" -gt 0 ]; then
        echo "[submit] WARNING: failed_shards=$FSHARDS — this session is degraded (partial judging); those instances scored 0 this round. Forcing a fresh session is recommended: delete /app/.session_id and /app/.session_public_id (keep .judge_sessions) and re-run submit.sh."
      fi
      exit 0
      ;;
    missing)
      echo "[submit] submission $SUB_ID vanished (session restarted?)" >&2
      exit 1
      ;;
    *)
      echo "[submit] $LINE"
      ;;
  esac
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    echo "[submit] poll timeout after ${POLL_TIMEOUT}s; the submission may still" >&2
    echo "[submit] finish — re-run submit.sh or ask the session for its history." >&2
    exit 1
  fi
done
