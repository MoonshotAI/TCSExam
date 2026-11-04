#!/usr/bin/env python3
"""make_fixtures.py — build the six validation-gate candidate apps for
d-vs-r-total-functions.  Run inside the sandbox at /work/dvr:

    python3 tests/reference/make_fixtures.py

Reads environment/app (the blank submission) and tests/reference/Basic.lean
(the positive control), and writes candidate apps to /tmp/dvr-<label>-app:
  axiom       blank + `axiom` in the helper layer          -> lexical ban, 0
  tamper      reference with a weakened (provable) `conj` header -> stmt check, 0
  exfalso     reference + helper `theorem boom : False` referenced by all
              three checkpoint slots                          -> SUSPECT, 0
  cross       both main slots "proved" via each other (conj cites refuted,
              refuted cites conj) through sorry-carrying helpers; the
              grader deletes the twin main slot from each variant, so both
              fail to compile                               -> 0
  positive    the reference itself                          -> 1.0 (3/3 partial)
(blank needs no fixture: environment/app itself is the all-sorry candidate.)
Every candidate app gets the .lake/packages symlink so `lake env lean` works.
"""
import os
import re
import shutil
import subprocess

ROOT = os.getcwd()
APP = os.path.join(ROOT, "environment", "app")
REF = open(os.path.join(ROOT, "tests", "reference", "Basic.lean"), encoding="utf-8").read()
BLANK = open(os.path.join(APP, "Task", "Basic.lean"), encoding="utf-8").read()

MARK = "-- outside the CHECKPOINT slots.\n"
CONJ_HEADER = (
    "theorem conj : ∃ C : ℝ, ∀ (n : ℕ) (f : (Fin n → Bool) → Bool),\n"
    "    (D f : ℝ) ≤ C * (Rc f) ^ 2 := by"
)


def make(label: str, text: str) -> None:
    dest = f"/tmp/dvr-{label}-app"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(APP, dest, ignore=shutil.ignore_patterns(".lake"))
    os.makedirs(os.path.join(dest, ".lake"), exist_ok=True)
    subprocess.run(["ln", "-sfn", "/app/.lake/packages",
                    os.path.join(dest, ".lake", "packages")], check=True)
    with open(os.path.join(dest, "Task", "Basic.lean"), "w", encoding="utf-8") as f:
        f.write(text)
    print(f"fixture {label}: {dest}")


def slot_body(text: str, name: str, new_body: str) -> str:
    """Replace the body between `-- CHECKPOINT <name> BEGIN` and END."""
    pat = re.compile(
        r"(-- CHECKPOINT " + re.escape(name) + r" BEGIN\n).*?(  -- CHECKPOINT " + re.escape(name) + r" END)",
        re.S,
    )
    out, n = pat.subn(lambda m: m.group(1) + new_body + "\n" + m.group(2), text, count=1)
    assert n == 1, f"slot {name} not found"
    return out


# ---- axiom: forbidden token in the helper layer ------------------------------
make("axiom", BLANK.replace(MARK, MARK + "\naxiom dvrCheat : False\n", 1))

# ---- tamper: weakened (and provable) conj header, genuine proof body ---------
tampered = REF.replace(
    CONJ_HEADER,
    "theorem conj : ∃ C : ℝ, ∀ (n : ℕ) (f : (Fin n → Bool) → Bool),\n"
    "    (Rc f : ℝ) ≤ C * (D f : ℝ) := by",
    1,
)
assert tampered != REF
tampered = slot_body(
    tampered,
    "conj",
    "  refine ⟨1, fun n f => ?_⟩\n"
    "  rw [one_mul]\n"
    "  obtain ⟨T, hT, hc⟩ := dvrDSpec f\n"
    "  refine csInf_le (dvrRcSet_bddBelow f) ?_\n"
    "  exact ⟨dvrSingle T, fun x => (dvrSingle_err T f hT x).trans_le (by norm_num),\n"
    "         fun x => (dvrSingle_cost T x).trans_le (by exact_mod_cast hc x)⟩",
)
make("tamper", tampered)

# ---- exfalso: packaged False harvested by every checkpoint slot --------------
exfalso = REF.replace(
    MARK, MARK + "\ntheorem boom : False := by\n  sorry\n", 1
)
for name in ("symmetric_evasive", "maj3_gap", "compose_D_le"):
    exfalso = slot_body(exfalso, name, "  exact False.elim boom")
make("exfalso", exfalso)

# ---- cross: each main slot proved through the contradictory twin -------------
cross = BLANK.replace(
    MARK,
    MARK
    + "\ntheorem dvrP : ∃ C : ℝ, ∀ (n : ℕ) (f : (Fin n → Bool) → Bool),\n"
    + "    (D f : ℝ) ≤ C * (Rc f) ^ 2 := by\n  sorry\n"
    + "theorem dvrNotP : ¬ ∃ C : ℝ, ∀ (n : ℕ) (f : (Fin n → Bool) → Bool),\n"
    + "    (D f : ℝ) ≤ C * (Rc f) ^ 2 := by\n  sorry\n",
    1,
)
cross = slot_body(cross, "conj", "  exact absurd dvrP DVR.refuted")
cross = slot_body(cross, "refuted", "  exact fun _ => absurd DVR.conj dvrNotP")
make("cross", cross)

# ---- positive: the reference itself ------------------------------------------
make("positive", REF)
