"""Append-only session journal with replay.

Every session lifecycle event and every accepted submission is appended as a
JSONL line to ``<state_dir>/judge_session_journal.jsonl`` and replayed at
startup. This is what makes the submission cap restart-proof and the
reconciliation query able to include destroyed sessions. Live judging does
NOT depend on the journal: it is an observability/accounting ledger, written
after the fact, never in the request path's failure domain (append errors
are logged and swallowed).
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("tcsexam.backend.journal")


@dataclass
class JournalSession:
    """One journaled session as the query API presents it."""

    session_id: str
    image: str
    family: str
    creator_identity: str  # identity of the session-creating request
    created: float
    # Owning run-id (the caller-declared X-TCSEXAM-Run-Id at create time;
    # "" when the creator sent none). Journaled at register so the
    # ownership check survives restarts. Ledger lines written before this
    # field existed replay to "" (unowned: readable by any caller).
    run_id: str = ""
    destroyed: bool = False
    status: str = "provisioning"  # provisioning | ready | failed
    error: str = ""
    # Relay-level accepted submissions: (timestamp, identity). Shards never
    # appear here — a POST /submit is one entry regardless of fan-out.
    submissions: list[tuple[float, str]] = field(default_factory=list)
    # Accepted PUBLIC-channel submissions: recorded for run-level history
    # attribution but NEVER counted toward the submission cap.
    public_submissions: list[tuple[float, str]] = field(default_factory=list)
    best_score: float | None = None
    best_submission_id: str = ""


class SessionJournal:
    """The append-only JSONL ledger plus its in-memory replay index."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self.sessions: dict[str, JournalSession] = {}
        self.replay()

    # ------------------------------------------------------------------ #
    # Replay
    # ------------------------------------------------------------------ #
    def replay(self) -> None:
        if not self._path.exists():
            return
        with self._path.open(errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    self._apply(event)
                except Exception:  # noqa: BLE001 - skip a torn tail line
                    continue

    def _apply(self, event: dict[str, Any]) -> None:
        kind = event.get("type")
        sid = event.get("sid")
        if kind == "register":
            self.sessions[sid] = JournalSession(
                session_id=sid,
                image=str(event.get("image") or ""),
                family=str(event.get("family") or ""),
                creator_identity=str(event.get("identity") or ""),
                created=float(event.get("t") or 0.0),
                # Old-format lines carry no run_id: read as "" (unowned).
                run_id=str(event.get("run_id") or ""),
            )
            return
        session = self.sessions.get(sid)
        if session is None:
            return
        if kind == "ready":
            session.status = "ready"
        elif kind == "failed":
            session.status = "failed"
            session.error = str(event.get("error") or "")
        elif kind == "destroyed":
            session.destroyed = True
        elif kind == "submit_accept":
            session.submissions.append(
                (float(event.get("t") or 0.0), str(event.get("identity") or ""))
            )
            if session.status == "provisioning":
                session.status = "ready"
        elif kind == "submit_accept_public":
            # Public channel: journaled for run-level history attribution;
            # never enters submissions (the cap counter).
            session.public_submissions.append(
                (float(event.get("t") or 0.0), str(event.get("identity") or ""))
            )
        elif kind == "score":
            score = event.get("score")
            if isinstance(score, (int, float)):
                if session.best_score is None or score > session.best_score:
                    session.best_score = float(score)
                    session.best_submission_id = str(event.get("submission_id") or "")

    # ------------------------------------------------------------------ #
    # Append
    # ------------------------------------------------------------------ #
    def _append(self, event: dict[str, Any]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a") as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001 - the ledger must never break requests
            LOGGER.warning("journal append failed", exc_info=True)
        self._apply(event)

    def record_register(
        self,
        sid: str,
        image: str,
        family: str,
        identity: str,
        created: float | None = None,
        *,
        run_id: str = "",
    ) -> None:
        self._append(
            {
                "t": created if created is not None else time.time(),
                "type": "register",
                "sid": sid,
                "image": image,
                "family": family,
                "identity": identity,
                "run_id": run_id,
            }
        )

    def record_status(self, sid: str, status: str, error: str = "") -> None:
        event: dict[str, Any] = {"t": time.time(), "type": status, "sid": sid}
        if error:
            event["error"] = error
        self._append(event)

    def record_destroyed(self, sid: str) -> None:
        self._append({"t": time.time(), "type": "destroyed", "sid": sid})

    def record_submit_accept(self, sid: str, identity: str) -> None:
        self._append(
            {"t": time.time(), "type": "submit_accept", "sid": sid, "identity": identity}
        )

    def record_score(self, sid: str, score: Any, submission_id: str = "") -> None:
        self._append(
            {
                "t": time.time(),
                "type": "score",
                "sid": sid,
                "score": score,
                "submission_id": submission_id,
            }
        )

    # ------------------------------------------------------------------ #
    # Queries (submission cap + reconciliation API)
    # ------------------------------------------------------------------ #
    def submission_count(
        self, identity: str, *, since: float = 0.0, exclude: set[str] | None = None
    ) -> int:
        """Accepted submissions by one identity since ``since`` (cap counter).

        ``exclude`` lists exempt identities (journaled but never counted).
        """
        if exclude and identity in exclude:
            return 0
        total = 0
        for session in self.sessions.values():
            total += sum(
                1 for ts, ident in session.submissions if ident == identity and ts >= since
            )
        return total

    def sessions_by_identity(self, identity: str) -> list[JournalSession]:
        """Sessions with at least one accepted submission from this identity
        (the reconciliation query's session set, destroyed included)."""
        return sorted(
            (s for s in self.sessions.values() if any(ident == identity for _, ident in s.submissions)),
            key=lambda s: s.created,
            reverse=True,
        )

    def session_submission_count(self, sid: str, *, since: float = 0.0) -> int:
        """Accepted hidden submissions in ONE session: the per-session cap
        counter and the ``?session_ids=`` query's per-row value.
        Public-channel accepts never count here. ``since`` bounds the count
        to submissions accepted at/after that time (the cap uses it so
        sessions from the unlimited era start fresh at the flip)."""
        s = self.sessions.get(sid)
        if s is None:
            return 0
        return sum(1 for ts, _ident in s.submissions if ts >= since)

    def first_seen(self, identity: str) -> float | None:
        """The identity's earliest journal footprint, or None if it has none.

        "Footprint" = a session REGISTER event carrying this creator identity
        or an accepted submission, whichever is earlier. Drives the cap's
        grandfather clause: register alone is enough — a run that created
        its session before the cap went live but had not submitted yet still
        started under the old unlimited rules.
        """
        best: float | None = None
        for s in self.sessions.values():
            if s.creator_identity == identity:
                best = s.created if best is None else min(best, s.created)
            for ts, ident in s.submissions:
                if ident == identity:
                    best = ts if best is None else min(best, ts)
        return best
