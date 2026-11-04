#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) that is invoked as
#
#   solver TRUTH_FILE OUTPUT_AIGER
#
# with the remaining time pool (seconds) in the environment variable
# LS_TIME_POOL. TRUTH_FILE is an ASCII truth table (one line per output,
# 2^n characters over {0,1}); OUTPUT_AIGER must be a binary AIGER file for a
# combinational circuit (no latches) that computes exactly the reference
# function. Exit code 0.
#
# You may edit this script (or the ABC source in ./abc) as you like — change
# the synthesis flow, loop over several scripts and keep the smallest
# circuit, hack ABC passes — as long as the solver ends up as an executable
# honoring the I/O contract.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Unpack the vendored ABC source on first run (the image build already did
# this; kept idempotent so a wiped /app/abc can be restored from the archive).
if [ ! -d "$ROOT/abc" ]; then
  mkdir -p "$ROOT/abc"
  tar -xJf "$ROOT/abc-src.tar.xz" -C "$ROOT/abc" --strip-components=1 --no-same-owner
fi

# Build ABC incrementally (a full build only happens when objects are
# missing). ABC_USE_NO_READLINE=1 drops the readline dependency.
make -C "$ROOT/abc" -j"$(nproc)" ABC_USE_NO_READLINE=1 abc

# The judged solver: a thin wrapper calling ABC with one fixed, deterministic
# script — the flow documented in the IWLS 2022 contest PDF (BDD collapse,
# then the dc2 compress script on the AIG). It works, but it is deliberately
# plain: contest-grade flows do much better. Improve it.
# (Remove before rewriting: the prebuilt solver is owned by the image-build
# user; recreating the file makes the caller its owner so chmod works under
# any uid.)
rm -f "$ROOT/solver"
cat > "$ROOT/solver" <<'EOF'
#!/bin/bash
# solver TRUTH_FILE OUTPUT_AIGER — remaining pool (seconds) in LS_TIME_POOL.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/abc/abc" -c "read_truth -xf \"$1\"; collapse; sop; strash; dc2; write_aiger \"$2\""
EOF
chmod +x "$ROOT/solver"
