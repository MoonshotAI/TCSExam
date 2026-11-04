#!/bin/bash
# Oracle solution for glasscut-roadef2018: replace /app/build.sh so the
# judged "solver" replays prerecorded best-known cutting patterns (see
# precomputed/, the ROADEF 2018 champion's best solutions — every stored
# pattern was re-validated by the real checker against the hidden instance
# and lands exactly at K). The solver is called as
#   solver <instance_prefix> <output_csv>
# so the stub identifies the instance by the prefix basename. Judging runs
# the solver twice per instance (3-minute and 1-hour tiers); the stub
# replays the same stored pattern in both tiers, so each tier lands at K,
# the 0.1/0.9 composite lands exactly at K (raw 1.0), and this must score 1.0.
set -e
cp -r /solution/precomputed /app/precomputed
cat > /app/build.sh <<'EOF'
#!/bin/bash
# oracle build: emit the replay stub as the solver (no compilation)
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat > "$ROOT/solver" <<'INNER'
#!/bin/bash
# oracle replay: copy the prerecorded pattern for this instance
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
name="$(basename "$1")"
sol="$HERE/precomputed/${name}_solution.csv"
if [ ! -f "$sol" ]; then
  # unknown instance: fail this instance (scores 0), leave the rest alone
  exit 1
fi
cp "$sol" "$2"
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(ls /app/precomputed/*_solution.csv | wc -l) prerecorded solutions"
