#!/bin/bash
# Six scoring-gate checks for polar-scaling-exponent (run in the sandbox; task package is synced to /work/polar)
# Usage: bash workbench/run-gates.sh (first export PATH to point to the Lean toolchain)
set -u
BASE=/work/polar
G=/tmp/gates
mkdir -p $G

mkcand () {  # $1 = label, $2 = variant file (relative to $BASE)
  local L=$1 V=$2
  rm -rf $G/$L && mkdir -p $G/$L/Task $G/$L/.lake
  cp $BASE/environment/app/lakefile.toml $BASE/environment/app/lake-manifest.json \
     $BASE/environment/app/lean-toolchain $BASE/environment/app/Task.lean $G/$L/
  cp $V $G/$L/Task/Basic.lean
  ln -sfn /app/.lake/packages $G/$L/.lake/packages
}

run () {   # $1 = label
  local L=$1
  echo "===== GATE $L ====="
  flock /tmp/lean.lock -c "python3 $BASE/tests/score.py --app $G/$L --tests $BASE/tests --reward $G/$L.reward" \
    > $G/$L.log 2>&1
  echo "exit=$? reward=$(cat $G/$L.reward 2>/dev/null)"
  tail -12 $G/$L.log
  echo
}

mkcand g1-nop          $BASE/workbench/gates/g1-nop.lean
mkcand g2-cheat-axiom  $BASE/workbench/gates/g2-cheat-axiom.lean
mkcand g3-tamper-stmt  $BASE/workbench/gates/g3-tamper-stmt.lean
mkcand g4-positive     $BASE/workbench/gates/g4-positive.lean
mkcand g5-exfalso      $BASE/workbench/gates/g5-exfalso.lean
mkcand g6-both-mains   $BASE/workbench/gates/g6-both-mains.lean

for L in g1-nop g2-cheat-axiom g3-tamper-stmt g4-positive g5-exfalso g6-both-mains; do
  run $L
done
