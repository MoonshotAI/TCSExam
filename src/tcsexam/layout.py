"""Resolve task selection and Solver protocol independently."""
import json
import os
from pathlib import Path

PROTOCOLS = ("online", "offline")
TRACKS = ("theorem", "solver", "construction", "open")


def load(path):
    return json.loads(Path(path).read_text())


def repository(root=None):
    explicit = root or os.environ.get("TCSEXAM_ROOT")
    candidates = [Path(explicit)] if explicit else [*Path.cwd().parents, Path.cwd(),
                                                  Path(__file__).resolve().parents[2]]
    # Prefer the closest current checkout when called from a nested directory.
    if not explicit:
        candidates = [Path.cwd(), *Path.cwd().parents, candidates[-1]]
    for candidate in candidates:
        candidate = candidate.expanduser().resolve()
        if (candidate / "suites/tasks.json").is_file() and (candidate / "tasks").is_dir():
            return candidate
    raise ValueError("Use a TCSExam checkout, --root PATH, or TCSEXAM_ROOT")


def within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes the checkout: {relative}")
    return path


def selection(root, suite, track=None, task=None, solver_protocol=None):
    data = load(root / f"suites/{suite}.json")
    if solver_protocol is None:
        solver_protocol = data.get("default_solver_protocol", "offline")
    if solver_protocol not in PROTOCOLS:
        raise ValueError(f"Unknown Solver protocol: {solver_protocol}")
    values = [task] if isinstance(task, str) else list(task or [])
    requested = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError("Task IDs must be strings")
        parts = value.split(',')
        if any(not part.strip() for part in parts):
            raise ValueError("Task IDs must be nonempty")
        requested.update(part.strip() for part in parts)
    registry = {(r["track"], r["id"]): r for r in load(root / "suites/tasks.json")["tasks"]}
    rows = []
    for row in data["tasks"]:
        if (track and row["track"] != track) or (requested and row["id"] not in requested):
            continue
        variant = solver_protocol if row["track"] == "solver" else "default"
        entry = registry[(row["track"], row["id"])]["variants"].get(variant)
        rows.append({**row, "variant": variant, **(entry or {
            "path": None, "protocol": None, "readiness": "adapter_not_available"})})
    missing = requested - {row["id"] for row in rows}
    if missing:
        raise ValueError("Tasks not present in this suite/track selection: " + ", ".join(sorted(missing)))
    if not rows:
        raise ValueError("No tasks match this suite/track/task selection")
    return data, rows


def require_paths(rows):
    absent = [r["id"] for r in rows if r["path"] is None]
    if absent:
        raise ValueError("Selected Solver protocol has no adapter for: " + ", ".join(absent)
                         + ". No alternative protocol was selected.")
