# SPDX-License-Identifier: Apache-2.0
# Shared terminal functions rendered into every online fetch_final.py.

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
