"""The adopted index and fixed-reference Solver metric. No task score is rewritten."""
from collections import defaultdict
import math
from statistics import mean, stdev, NormalDist

WEIGHTS = {"theorem": 30, "solver": 30, "construction": 30, "open": 10}
METRIC_ID = "tcsexam-index-original-30303010-v0.1"


def number(value):
    if isinstance(value, bool):
        raise ValueError("A score must be a finite number, not a boolean")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("A score must be finite")
    return result


def aggregate(rows, suite, cohort):
    """Equal attempts within tasks, then equal tasks within each track.

    Incomplete planned cells produce a null index; they are never filled with zero.
    The cohort names every evaluated model and the planned repetitions per task.
    """
    if cohort["suite"] != suite["suite"]:
        raise ValueError("Cohort and task suite differ")
    if not cohort.get("solver_reference_id"):
        raise ValueError("Declare the fixed Solver reference")
    declared_protocol = cohort.get("solver_protocol")
    if declared_protocol is not None and declared_protocol not in {"online", "offline"}:
        raise ValueError("Unknown Solver protocol in cohort")
    observed_protocols = {r.get("solver_protocol") for r in rows
                          if r["track"] == "solver" and r["adoption_status"] != "excluded"
                          and r.get("solver_protocol")}
    if observed_protocols - {"online", "offline"}:
        raise ValueError("Unknown Solver protocol in attempts")
    if len(observed_protocols) > 1:
        raise ValueError("Cannot mix online and offline Solver attempts")
    if declared_protocol and any(r.get("solver_protocol") != declared_protocol for r in rows
                                if r["track"] == "solver" and r["adoption_status"] != "excluded"):
        raise ValueError("Attempt Solver protocol differs from the cohort")
    expected = {(t["track"], t["id"]) for t in suite["tasks"]}
    groups = defaultdict(list)
    seen = set()
    counts = defaultdict(int)
    problems = defaultdict(list)
    for row in rows:
        model, track, item = row["model"], row["track"], row["item"]
        if model not in cohort["models"]:
            raise ValueError(f"Undeclared model: {model}")
        if (track, item) not in expected:
            raise ValueError(f"Task does not belong to suite: {track}/{item}")
        key = (model, track, item, str(row["attempt"]))
        if key in seen:
            raise ValueError(f"Duplicate attempt: {key}")
        seen.add(key)
        adoption = row["adoption_status"]
        if adoption == "excluded":
            continue
        if adoption not in {"selected", "selected_provisional"}:
            raise ValueError(f"Unknown adoption status: {adoption}")
        counts[(model, track, item)] += 1
        if adoption == "selected_provisional":
            problems[model].append(f"{track}/{item}: provisional attempt")
        if row["score_status"] != "valid":
            problems[model].append(f"{track}/{item}: {row['score_status']}")
            continue
        score = number(row["score"])
        if track in {"theorem", "open"} and score not in {0., 1.}:
            raise ValueError("Proof tracks require complete-proof outcomes, not partial credit")
        if track == "solver":
            if row["score_type"] != "fixed_reference_relative":
                raise ValueError("Solver needs the fixed-reference score, not raw checker reward")
            if not 0 <= score <= 1:
                raise ValueError("Relative Solver score must be in [0, 1]")
        if track == "construction" and score < 0:
            raise ValueError("Construction score must be nonnegative")
        groups[(model, track, item)].append(score)
    result = []
    for model, settings in cohort["models"].items():
        repeats = settings["attempts_per_task"]
        if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
            raise ValueError("attempts_per_task must be a positive integer")
        tracks = {}
        coverage = {}
        for track in WEIGHTS:
            items = sorted(item for t, item in expected if t == track)
            values = []
            for item in items:
                key = (model, track, item)
                if counts[key] > repeats:
                    raise ValueError(f"Too many adopted attempts: {key}")
                if len(groups[key]) != repeats:
                    problems[model].append(f"{track}/{item}: {len(groups[key])}/{repeats} valid attempts")
                else:
                    values.append(mean(groups[key]))
            coverage[track] = {"valid_tasks": len(values), "expected_tasks": len(items)}
            tracks[track] = mean(values) if items and len(values) == len(items) else None
        complete = all(v is not None for v in tracks.values())
        total = sum(WEIGHTS[t] * v for t, v in tracks.items()) if complete else None
        result.append({"model": model, **tracks, "index": total,
                       "status": "complete" if complete and not problems[model] else
                                 "provisional" if complete else "incomplete",
                       "coverage": coverage, "issues": sorted(set(problems[model]))})
    return {"metric_id": METRIC_ID, "suite": suite["suite"], "weights": WEIGHTS,
            "solver_reference_id": cohort["solver_reference_id"],
            "solver_protocol": declared_protocol or next(iter(observed_protocols), None),
            "unit": "index_points_not_percentage", "models": result}


def relative_score(task_id, records, reference):
    """Score a complete final-judge instance table against a frozen reference.

    Missing final outcomes fail loudly. Solver-level invalidity receives zero.
    Extra unscored instances are retained separately, never silently used as zero.
    """
    task = reference["tasks"][task_id]
    kind = task.get("kind")
    if kind not in ("objective", "solve"):
        raise ValueError(f"Reference task {task_id} must declare kind as objective or solve")
    refs = task["reference_values"]
    by_name = {}
    for record in records:
        name = record["instance"]
        if name in by_name:
            raise ValueError(f"Duplicate instance {name}")
        by_name[name] = record
    missing = set(refs) - set(by_name)
    if missing:
        raise ValueError(f"Missing final outcomes: {sorted(missing)}")
    sign = {"min": -1, "max": 1}[task["direction"]]
    solved_metric = kind == "solve"
    values = []
    detail = []
    invalid_statuses = {"invalid", "timeout", "crash", "error", "failed",
                        "unsolved", "build_failed", "wrong_answer", "certificate_failed"}
    for name, raw_refs in refs.items():
        ref = [number(x) for x in raw_refs]
        if len(ref) < 2:
            raise ValueError(f"Reference has fewer than two valid outcomes: {name}")
        rec = by_name[name]
        status = rec["status"]
        if status != "ok":
            if status not in invalid_statuses:
                raise ValueError(f"Unknown or infrastructure status: {name}: {status}")
            score = 0.
        else:
            if solved_metric:
                if "solved" in rec:
                    if not isinstance(rec["solved"], bool):
                        raise ValueError("solved must be an explicit Boolean")
                    value = float(rec["solved"])
                else:
                    value = number(rec["A"])
                    if value not in {0., 1.}:
                        raise ValueError("Solve-rate outcome must be 0 or 1")
            else:
                value = number(rec["A"])
            mu = mean(ref)
            scale = max(stdev(ref), abs(mu) * reference["sigma_floor_relative"],
                        reference["sigma_floor_absolute"])
            score = NormalDist().cdf(sign * (value - mu) / scale)
        values.append(score)
        detail.append({"instance": name, "score": score, "status": status})
    if not values:
        raise ValueError("No scoreable reference instances")
    return {"task": task_id, "relative_score": mean(values), "instances": detail,
            "unscored_instances": sorted(set(by_name) - set(refs)),
            "reference_id": reference["reference_id"]}
