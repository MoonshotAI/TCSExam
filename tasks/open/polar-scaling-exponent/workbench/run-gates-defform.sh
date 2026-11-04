#!/bin/bash
# Scoring-gate checks after the polar-scaling-exponent definition-shape fix (2026-09-06, rate form)
# Run in the sandbox; the task package is synced to /work/polarfix. First export PATH to point to the Lean toolchain.
# Usage: bash workbench/run-gates-defform.sh
set -u
BASE=/work/polarfix
G=/tmp/polarfix-gates
ST=/tmp/polarfix-scratch
rm -rf $G $ST
mkdir -p $G $ST

PKGDIR=/opt/lean-lib/mathlib4/.lake/packages
[ -d "$PKGDIR" ] || PKGDIR=/app/.lake/packages
echo "packages: $PKGDIR"

python3 - << 'PYEOF'
import pathlib
BASE = pathlib.Path("/work/polarfix")
G = pathlib.Path("/tmp/polarfix-gates")
ST = pathlib.Path("/tmp/polarfix-scratch")
src = (BASE / "environment/app/Task/Basic.lean").read_text()
CONJ_HDR = "theorem conj :\n    ∀ {Y : Type*} [Fintype Y] (W : Channel Y), IsBMS W → ScalingExponentLe W 4 := by"
REF_HDR  = "theorem refuted :\n    ¬∀ {Y : Type*} [Fintype Y] (W : Channel Y), IsBMS W → ScalingExponentLe W 4 := by"
FIXED_MARK = "-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,\n-- outside the CHECKPOINT slots."

def variant(name, text):
    d = G / name
    (d / "Task").mkdir(parents=True, exist_ok=True)
    (d / ".lake").mkdir(exist_ok=True)
    for f in ("lakefile.toml", "lake-manifest.json", "lean-toolchain", "Task.lean"):
        (d / f).write_text((BASE / "environment/app" / f).read_text())
    (d / "Task/Basic.lean").write_text(text)

assert CONJ_HDR in src and REF_HDR in src and FIXED_MARK in src

# g1-nop: unchanged (sorry in both main slots)
variant("g1-nop", src)

# g2-cheat-axiom: add an axiom after the fixed section and use it in place of conj
t = src.replace(FIXED_MARK, FIXED_MARK + "\n\naxiom cheatAx : ∀ {Y : Type*} [Fintype Y] (W : Channel Y), IsBMS W → ScalingExponentLe W 4")
t = t.replace(CONJ_HDR + "\n  -- CHECKPOINT conj BEGIN\n  sorry",
              CONJ_HDR + "\n  -- CHECKPOINT conj BEGIN\n  exact cheatAx")
assert "cheatAx" in t and "exact cheatAx" in t
variant("g2-cheat-axiom", t)

# g3-tamper-stmt: change 4 to 5 in the conj statement (one numeral)
t = src.replace(CONJ_HDR, CONJ_HDR.replace("W 4", "W 5"))
assert t != src
variant("g3-tamper-stmt", t)

# g4-exfalso: add helper theorem boom : False and use exact boom.elim in the conj slot
t = src.replace(FIXED_MARK, FIXED_MARK + "\n\ntheorem boom : False := by\n  sorry")
t = t.replace(CONJ_HDR + "\n  -- CHECKPOINT conj BEGIN\n  sorry",
              CONJ_HDR + "\n  -- CHECKPOINT conj BEGIN\n  exact boom.elim")
assert "theorem boom : False" in t and "exact boom.elim" in t
variant("g4-exfalso", t)

# g5-crossref: make the refuted proof refer to conj (cross-reference)
t = src.replace(REF_HDR + "\n  -- CHECKPOINT refuted BEGIN\n  sorry",
                REF_HDR + "\n  -- CHECKPOINT refuted BEGIN\n  exact fun h => absurd PolarScaling.conj h")
assert "absurd PolarScaling.conj h" in t
variant("g5-crossref", t)

# g6-conj-true / g7-refuted-true: scratch tests (update the statement in reference as well) plus candidate
for label, hdr, name in (("g6-conj-true", CONJ_HDR, "conj"), ("g7-refuted-true", REF_HDR, "refuted")):
    t = src.replace(hdr, hdr.split(" :")[0] + " : True := by")
    t = t.replace("-- CHECKPOINT " + name + " BEGIN\n  sorry",
                  "-- CHECKPOINT " + name + " BEGIN\n  trivial")
    assert " : True := by" in t and "trivial" in t
    variant(label, t)
    td = ST / label / "tests"
    td.mkdir(parents=True, exist_ok=True)
    (td / "score.py").write_text((BASE / "tests/score.py").read_text())
    (td / "checkpoints.json").write_text((BASE / "tests/checkpoints.json").read_text())
    (td / "reference").mkdir(exist_ok=True)
    (td / "reference/Basic.lean").write_text(t)
print("variants written")
PYEOF
[ $? -eq 0 ] || { echo "VARIANT GENERATION FAILED"; exit 1; }

for L in g1-nop g2-cheat-axiom g3-tamper-stmt g4-exfalso g5-crossref g6-conj-true g7-refuted-true; do
  ln -sfn $PKGDIR $G/$L/.lake/packages
done

run () {  # $1 = label, $2 = tests dir
  local L=$1 T=$2
  echo "===== GATE $L ====="
  flock /tmp/lean.lock -c "python3 $BASE/tests/score.py --app $G/$L --tests $T --reward /tmp/polarfix-$L.reward" \
    > /tmp/polarfix-$L.log 2>&1
  echo "exit=$? reward=$(cat /tmp/polarfix-$L.reward 2>/dev/null)"
  tail -6 /tmp/polarfix-$L.log
  echo
}

run g1-nop          $BASE/tests
run g2-cheat-axiom  $BASE/tests
run g3-tamper-stmt  $BASE/tests
run g4-exfalso      $BASE/tests
run g5-crossref     $BASE/tests
run g6-conj-true    $ST/g6-conj-true/tests
run g7-refuted-true $ST/g7-refuted-true/tests
echo "ALL GATES DONE"
