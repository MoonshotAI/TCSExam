#!/usr/bin/env python3
"""TCSExam shared metric engine (single source used across the full benchmark).

Verifier-side metric engine for raw per-instance feedback.
The scoring service stores only raw per-instance data (instance, A value, valid/failed status); the final metric
is computed on the verifier side by this engine using anchor data (K = best known score, B = shipped baseline score).

Input: a list of per-instance records [{"instance": str, "A": number, "status": "ok"|"invalid"|"error"}]
          + anchor data {"K": {instance: number}, "B": {instance: number}}
          + configuration {"shape": str, "direction": "max"|"min", "params": {...}}
Output: {"score": number, "detail": {...}}The detail includes per-instance contributions and exclusions,
     with invalid/error instances listed separately.

Scoring formula: the raw gap ratio r, with no clipping or other transformation:
for max problems, r=(A−B)/(K−B); for min problems, r=(B−A)/(B−K). A=B gives 0, A=K gives 1, exceeding K gives >1,
and doing worse than B gives <0. Instances with B==K are excluded automatically.
"""
import json

# Raw gap ratio with no clipping or transformation.
METRIC_VERSION = "gap-ratio-260920"
PROVISIONAL = False


class MetricConfigError(ValueError):
    """Invalid configuration or anchor data."""


def load_anchors(path):
    """Read anchor data from a JSON file {"K": {inst: v}, "B": {inst: v}}。"""
    with open(path) as f:
        data = json.load(f)
    return validate_anchors(data)


def validate_anchors(data):
    if not isinstance(data, dict) or "K" not in data or "B" not in data:
        raise MetricConfigError('anchors must be a dict with "K" and "B" keys')
    k, b = data["K"], data["B"]
    if not isinstance(k, dict) or not isinstance(b, dict):
        raise MetricConfigError('anchors "K" and "B" must be {instance: value} dicts')
    return {"K": {str(i): v for i, v in k.items()},
            "B": {str(i): v for i, v in b.items()}}


# ---------------------------------------------------------------------------
# Shape: gap ratio (A−B)/(K−B), with no clipping.
# For max problems, use (A−B)/(K−B); for min problems, (B−A)/(B−K), then take the mean without clipping.
# Instances with B==K are excluded and recorded automatically; invalid/error instances score 0 and are listed separately.
# ---------------------------------------------------------------------------
def shape_gap_ratio(records, anchors, config):
    direction = config["direction"]
    per_instance = []
    excluded = []
    zeroed = []
    contributions = []

    for rec in records:
        inst = str(rec["instance"])
        status = rec.get("status", "ok")
        b = anchors["B"][inst]
        k = anchors["K"][inst]

        if b == k:
            excluded.append({"instance": inst, "reason": "B_equals_K"})
            continue
        if direction == "max" and not k > b:
            raise MetricConfigError(f"{inst}: max problem requires K > B, got K={k} B={b}")
        if direction == "min" and not k < b:
            raise MetricConfigError(f"{inst}: min problem requires K < B, got K={k} B={b}")

        if status != "ok":
            contribution = 0.0
            zeroed.append({"instance": inst, "status": status})
        else:
            a = rec.get("A")
            if direction == "max":
                contribution = (a - b) / (k - b)
            else:
                contribution = (b - a) / (b - k)
            # Raw gap ratio: no clipping; exceeding K naturally gives >1, and doing worse than B naturally gives <0.

        per_instance.append({"instance": inst, "status": status, "A": rec.get("A"),
                             "B": b, "K": k, "contribution": contribution})
        contributions.append(contribution)

    return _assemble(per_instance, excluded, zeroed, contributions)


# ---------------------------------------------------------------------------
# Shape: solve rate (S_A−S_B)/(S_K−S_B) for decision problems, with solved/unsolved represented as Boolean values.
# For each instance S ∈ {0,1}. Instances with S_B==S_K do not contribute to the denominator and are excluded and recorded automatically.
# Invalid/error instances are treated as unsolved (score 0) and listed separately.
# ---------------------------------------------------------------------------
def shape_solve_rate(records, anchors, config):
    per_instance = []
    excluded = []
    zeroed = []
    contributions = []

    for rec in records:
        inst = str(rec["instance"])
        status = rec.get("status", "ok")
        s_b = int(bool(anchors["B"][inst]))
        s_k = int(bool(anchors["K"][inst]))

        if s_k < s_b:
            raise MetricConfigError(f"{inst}: solve-rate anchors require K to be solved whenever the baseline is solved; got K={s_k} B={s_b}")
        if s_b == s_k:
            excluded.append({"instance": inst, "reason": "B_equals_K"})
            continue

        if status != "ok":
            contribution = 0.0
            zeroed.append({"instance": inst, "status": status})
        else:
            solved = int(bool(rec.get("A")))
            contribution = float((solved - s_b) / (s_k - s_b))
            contribution = min(1.0, max(0.0, contribution))

        per_instance.append({"instance": inst, "status": status,
                             "solved": bool(rec.get("A")) if status == "ok" else False,
                             "S_B": s_b, "S_K": s_k, "contribution": contribution})
        contributions.append(contribution)

    return _assemble(per_instance, excluded, zeroed, contributions)


# ---------------------------------------------------------------------------
# Shape: All-key solve rate: every scored item participates.
# B==K items are included. Each solved item scores 1 and each unsolved item scores 0 (invalid, timed-out, and crashed items also score 0 and are listed separately).
# The total score is the mean over all items. For items with K>B, this matches solve_rate item by item ((A−B)/(K−B)=A for binary values),
# so the overall metric is the all-item solve rate, matching ICCMA official rankings by number solved. Anchors are not part of the formula;
# S_B/S_K are kept in the details for reference only. Inverted items where s_k < s_b are still scored (solved = 1).
# ---------------------------------------------------------------------------
def shape_solve_rate_all_keys(records, anchors, config):
    per_instance = []
    excluded = []
    zeroed = []
    contributions = []

    for rec in records:
        inst = str(rec["instance"])
        status = rec.get("status", "ok")
        s_b = int(bool(anchors["B"][inst]))
        s_k = int(bool(anchors["K"][inst]))

        if status != "ok":
            contribution = 0.0
            zeroed.append({"instance": inst, "status": status})
        else:
            contribution = float(int(bool(rec.get("A"))))

        per_instance.append({"instance": inst, "status": status,
                             "solved": bool(rec.get("A")) if status == "ok" else False,
                             "S_B": s_b, "S_K": s_k, "contribution": contribution})
        contributions.append(contribution)

    return _assemble(per_instance, excluded, zeroed, contributions)


# ---------------------------------------------------------------------------
# Scaffolds: a two-component shape (radiation-style) and a certificate adjustment (SAT-style false-claim penalty).
# These interfaces are reserved and raise NotImplementedError.
# ---------------------------------------------------------------------------
def shape_two_component(records, anchors, config):
    # Reserved parameter: params["tolerance"] is the threshold tolerance for the primary term to be close to the lower bound,
    #              params["secondary_weight"] is the weight of the secondary term.
    raise NotImplementedError(
        "The two_component shape is a parameterized scaffold: the primary-term threshold tolerance and secondary-term weight are reserved,"
        "and this shape is not implemented."
    )


def shape_certificate_adjust(records, anchors, config):
    # Reserved parameter: params["penalty_per_false_unsat"] is the penalty for a false UNSAT claim (default 8,
    # matching SMT-COMP: a false UNSAT claim incurs −8 solved); the rule requiring a certificate for UNSAT is not implemented.
    raise NotImplementedError(
        "The certificate_adjust shape is a parameterized scaffold: solved count is primary and the false UNSAT penalty is reserved,"
        "and this shape is not implemented."
    )


# Shape library: shape name → function. Shapes with implemented=False are scaffolds; calling them raises NotImplementedError.
SHAPES = {
    "gap_ratio": {
        "fn": shape_gap_ratio,
        "implemented": True,
        "provisional": False,
        "description": "Raw gap ratio (A−B)/(K−B), averaged over instances without clipping",
    },
    "solve_rate": {
        "fn": shape_solve_rate,
        "implemented": True,
        "provisional": False,
        "description": "Solve rate (S_A−S_B)/(S_K−S_B), Boolean decision problem",
    },
    "solve_rate_all_keys": {
        "fn": shape_solve_rate_all_keys,
        "implemented": True,
        "provisional": False,
        "description": "All-key solve rate: all items participate, B==K items are included, and the score is the mean of 1 for solved and 0 for unsolved",
    },
    "two_component": {
        "fn": shape_two_component,
        "implemented": False,
        "provisional": False,
        "description": "Two-component (radiation-style): primary-term threshold + secondary-term primary score (scaffold)",
    },
    "certificate_adjust": {
        "fn": shape_certificate_adjust,
        "implemented": False,
        "provisional": False,
        "description": "Certificate adjustment (SAT-style): solved count is primary; false UNSAT claims incur −8 solved (scaffold)",
    },
}


def _assemble(per_instance, excluded, zeroed, contributions):
    score = sum(contributions) / len(contributions) if contributions else 0.0
    return {
        "score": score,
        "instances": per_instance,
        "excluded": excluded,
        "zeroed": zeroed,
        "counts": {
            "scored": len(per_instance),
            "excluded": len(excluded),
            "zeroed": len(zeroed),
        },
    }


def compute_metric(records, anchors, config):
    """Engine entry point: records (raw per-instance data) + anchors (K/B) + config → metric score and details."""
    anchors = validate_anchors(anchors)
    shape_name = config["shape"]
    shape = SHAPES[shape_name]  # Configuration validation has already ensured that the shape name is valid

    missing = [str(r["instance"]) for r in records
               if str(r["instance"]) not in anchors["B"] or str(r["instance"]) not in anchors["K"]]
    if missing:
        raise MetricConfigError(f"Anchor data is missing for these instances: {missing}")

    detail = shape["fn"](records, anchors, config)
    return {
        "score": detail.pop("score"),
        "detail": detail,
        "shape": shape_name,
        "direction": config["direction"],
        "metric_version": METRIC_VERSION,
        "provisional": PROVISIONAL,
        "metric_note": "Raw gap ratio r: A=B→0, A=K→1, no clipping",
    }
