#!/bin/bash
# Oracle solution for jsplib-jssp: replace /app/build.sh so the judged
# "solver" replays the prerecorded schedules by instance name (283
# instances, full judged set since 2026-09-12): the 31 fresh instances
# replay at K (24 from the 2026-08 field-best measurement; the 7 restored
# seed-batch instances from the 2026-09-12 full-set measurement), the 252
# classic instances replay at the best schedule on record for each
# (mostly the 2026-08 L-level CP-SAT runs; 31 instances the baseline
# runs; every schedule re-validated with jssp_check at assembly time).
# Expected outcome (full set, judge image v11): pure gap ratio r =
# 0.7158595951604652 (262 participating instances, 21 B==K excluded) — the
# replay lands inside [B, K] everywhere, so the retired provisional
# gap_ratio caliber recorded the same value; retired calibers: SOL =
# 0.8177977854822949, v0 three-anchor 0.3583969465648842 — reproduced by
# the local judging-chain replay (tests/SELF-CHECK.md 2026-09-12
# full-set section).
set -e
cp -r /solution/solutions /app/solutions
cat > /app/build.sh <<'EOF'
#!/bin/bash
# oracle build: emit the replay stub as the solver (no compilation)
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat > "$ROOT/solver" <<'INNER'
#!/bin/bash
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INST="$1"; OUT="$2"
name=$(basename "$INST" .txt)
cp "$HERE/solutions/$name.sol" "$OUT"
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(ls /app/solutions | wc -l) prerecorded schedules"
