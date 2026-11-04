#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) that reads an ITC2021 instance (RobinX XML <Instance>) on stdin
# and prints a schedule (RobinX XML <Solution>) on stdout.
#
# You may edit this script (or the solver source) as you like — e.g. add
# more source files, change flags, or produce a wrapper — as long as the
# solver ends up as an executable honoring the I/O contract. Note: all
# top-level /app/*.cpp files are compiled together; keep helper sources in
# subdirs.
#
# The shipped baseline is deterministic (2026-08-31 rework, itc2019
# precedent): fixed seed + a pinned per-instance iteration budget
# (budgets.tsv, looked up by instance sha256) instead of the old
# micro-benchmark wall-clock sizing. All transcendental math in the search
# goes through fixed-path polynomial approximations (det_exp/det_log in
# solver.cpp) and -ffp-contract=off keeps FMA fusion out, so the output is
# bit-identical on any machine. Wall clock remains only as a safety
# backstop (the judge's shared time pool): if it ever fires, the run ends
# at a prefix of the one deterministic trajectory. Instances without a
# pinned budget fall back to a fixed default iteration count.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
g++ -O2 -std=c++17 -ffp-contract=off -o "$ROOT/solver-bin" "$ROOT"/*.cpp
cat > "$ROOT/solver" <<'EOF'
#!/bin/bash
# Baseline wrapper: pin the iteration budget per instance (sha256 lookup in
# budgets.tsv) so the shipped configuration is machine-independent. The
# remaining shared time pool is still honoured by the binary itself
# (ITC2021_TIME_POOL backstop) as a safety net.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"
HASH=$(sha256sum "$TMP" | cut -d' ' -f1)
BUDGET=$(grep -m1 "^$HASH " "$ROOT/budgets.tsv" 2>/dev/null | cut -d' ' -f2 || true)
if [ -z "${ITC_ITERS:-}" ]; then
  ITC_ITERS="${BUDGET:-4000000}"
fi
exec env ITC_ITERS="$ITC_ITERS" "$ROOT/solver-bin" < "$TMP"
EOF
chmod +x "$ROOT/solver"
