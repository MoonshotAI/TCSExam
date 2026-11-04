"""Submission-cap wiring smoke tests (no service, no workers).

Covers the three seams the cap depends on:
- config: the judge_sessions.submission_cap YAML section is really parsed
  (per-field loaders have silently dropped keys before)
- store: JudgeSessionStore's constructor wires up the SessionJournal
- counting semantics: record_submission_accept / submission_used / cap_for /
  cap_exempt work per the contract (relay-level counting unit, exemptions
  journaled but not counted, family override first)
"""
from __future__ import annotations

import json
from pathlib import Path

from tcsexam.backend.config import load_config
from tcsexam.backend.journal import SessionJournal
from tcsexam.backend.sessions import JudgeSessionStore


def test_cap_wiring_end_to_end(tmp_path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        f"""
host: 127.0.0.1
port: 0
public_base_url: http://test
auth: {{token_id: t, token_secret: s}}
adapter: local-test
state_dir: {tmp_path}/state
backend:
  judge_sessions:
    max_sessions: 4
    submission_cap:
      enabled: true
      default: 10
      overrides: {{sat: 4}}
      exempt_identities: ["192.0.2.2"]
"""
    )
    config = load_config(cfg_path)

    cap = config.backend.judge_sessions.submission_cap
    assert cap.enabled is True
    assert cap.default == 10
    assert cap.overrides == {"sat": 4}
    assert cap.exempt_identities == ["192.0.2.2"]

    store = JudgeSessionStore(executor=None, config=config)
    assert store._journal is not None, "the journal must be wired at construction"
    assert store.cap_for("other") == 10
    assert store.cap_for("sat") == 4
    assert store.cap_exempt("192.0.2.2") and not store.cap_exempt("192.0.2.1")

    # Production order: register the session first, then journal accepted
    # submissions (submission events for unknown sids are dropped by design —
    # in production a submit always happens after the register).
    store._journal.record_register("jsess-a", "reg/sat-judge:v1", "sat", "192.0.2.1")
    store._journal.record_register("jsess-b", "reg/other-judge:v1", "other", "192.0.2.2")
    store.record_submission_accept("jsess-a", "192.0.2.1")
    store.record_submission_accept("jsess-a", "192.0.2.1")
    store.record_submission_accept("jsess-b", "192.0.2.2")  # exempt identity: journaled, not counted
    assert store.submission_used("192.0.2.1") == 2
    assert store.submission_used("192.0.2.2") == 0

    # Public channel: submit_accept_public is journaled but never enters the
    # cap counter (hidden-only), replay-stable.
    store._journal.record_register("jsess-p", "reg/sat-judge:v1", "sat", "192.0.2.1")
    store.record_submission_accept_public("jsess-p", "192.0.2.1")
    store.record_submission_accept_public("jsess-p", "192.0.2.1")
    assert store.submission_used("192.0.2.1") == 2
    types = [
        json.loads(line)["type"]
        for line in open(Path(config.state_dir) / "judge_session_journal.jsonl")
    ]
    assert types.count("submit_accept_public") == 2

    # Restart replay: a fresh journal over the same file keeps the counts.
    replay = SessionJournal(str(Path(config.state_dir) / "judge_session_journal.jsonl"))
    assert replay.submission_count("192.0.2.1") == 2
    assert replay.submission_count("192.0.2.1") == 2
