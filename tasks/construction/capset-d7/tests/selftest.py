#!/usr/bin/env python3
"""Self-test for the capset-d7-lean judge.

Runs tests/score.py against fixture submissions and checks the verdicts:
  blank         (shipped file, no main theorem)  -> reward 0, not accepted
  bad_axiom     (private axiom cheat)            -> reward 0 (lexical gate)
  bad_tampered  (IsCap definition weakened)      -> reward 0 (fixed-layer gate)
  sanity_cube128 ({0,1}^7 cap, k = 128)          -> accepted, alpha = 0 (baseline)
  sanity_ub2188  (trivial upper bound, k = 2188) -> accepted, alpha = 0 (baseline)
plus pure-Python unit checks of the milestone table (including the
record_broken branches, for which no real certificate exists).

Local usage (host Lean env, no Docker):
  python3 tests/selftest.py --lake-cwd /path/to/lean-work
In the task image the default --lake-cwd is a plain directory containing the
submission under Task/Basic.lean; score.py runs `lake env lean` there.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

TESTS = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(TESTS)


def run_judge(app_dir: str, lake_cwd: str, reward: str):
    env = dict(os.environ)
    proc = subprocess.run(
        [sys.executable, os.path.join(TESTS, "score.py"),
         "--app", app_dir, "--tests", TESTS, "--reward", reward,
         "--lake-cwd", lake_cwd],
        capture_output=True, text=True, timeout=1500, env=env)
    out = proc.stdout + proc.stderr
    sidecar = os.path.join(os.path.dirname(reward), "judge_result.json")
    res = json.load(open(sidecar)) if os.path.exists(sidecar) else None
    val = float(open(reward).read()) if os.path.exists(reward) else None
    return val, res, out


def make_app(fixture: str) -> str:
    app = tempfile.mkdtemp(prefix="capset-selftest-app-")
    os.makedirs(os.path.join(app, "Task"))
    src = fixture if fixture else os.path.join(TESTS, "reference", "Basic.lean")
    shutil.copy(src, os.path.join(app, "Task", "Basic.lean"))
    return app


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lake-cwd", required=True,
                    help="directory with a working lake env (mathlib built)")
    args = ap.parse_args()
    failures = []

    def check(name, cond, detail=""):
        print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({detail})" if detail else ""))
        if not cond:
            failures.append(name)

    cases = [
        ("blank", None, {"accepted": False}, 0.0),
        ("bad_axiom", "bad_axiom.lean", {"accepted": False}, 0.0),
        ("bad_tampered", "bad_tampered.lean", {"accepted": False}, 0.0),
        ("sanity_cube128", "sanity_cube128.lean",
         {"accepted": True, "direction": "construction", "k": 128,
          "alpha": 0.0, "record_broken": False}, 0.0),
        ("sanity_ub2188", "sanity_ub2188.lean",
         {"accepted": True, "direction": "upper_bound", "k": 2188,
          "alpha": 0.0, "record_broken": False}, 0.0),
    ]
    tmp = tempfile.mkdtemp(prefix="capset-selftest-")
    for name, fixture, expect, expect_reward in cases:
        app = make_app(os.path.join(TESTS, "fixtures", fixture) if fixture else None)
        reward = os.path.join(tmp, name, "reward.txt")
        val, res, out = run_judge(app, args.lake_cwd, reward)
        ok = res is not None and val == expect_reward
        for key, v in expect.items():
            ok = ok and res.get(key) == v
        if name == "sanity_cube128":
            ok = ok and res.get("accepted") is True  # the judge must accept the cube
        check(name, ok, "" if ok else f"reward={val} res={res}\n{out[-2000:]}")

    # milestone unit checks (no certificates exist for these branches; the
    # scoring function itself is exercised)
    sys.path.insert(0, TESTS)
    import score as judge
    spec = json.load(open(os.path.join(TESTS, "judge.json")))
    unit = [
        ("lb 128 -> 0", judge.milestone("construction", 128, spec), (0.0, False)),
        ("lb 182 -> 0.5", judge.milestone("construction", 182, spec), (0.5, False)),
        ("lb 236 -> 1", judge.milestone("construction", 236, spec), (1.0, False)),
        ("lb 237 -> record", judge.milestone("construction", 237, spec), (1.0, True)),
        ("ub 2188 -> 0", judge.milestone("upper_bound", 2188, spec), (0.0, False)),
        ("ub 289 -> 1", judge.milestone("upper_bound", 289, spec), (1.0, False)),
        ("ub 288 -> record", judge.milestone("upper_bound", 288, spec), (1.0, True)),
    ]
    for name, got, want in unit:
        ga, gb = got
        wa, wb = want
        check(name, abs(ga - wa) < 1e-9 and gb == wb, f"got={got}")

    print("selftest:", "OK" if not failures else f"FAILED {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
