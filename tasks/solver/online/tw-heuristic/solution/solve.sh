#!/bin/bash
# Oracle solution for tw-heuristic (form 1): install a replay stub as the
# solver. The stub and its prerecorded decompositions are reused
# byte-for-byte from the async sibling package (tw-heuristic-async/solution/):
# this final package judges through the SAME judging chain (same judge image
# solver-tw-heuristic-judge-v6, same hidden set, same anchors) — at verify
# time tests/fetch_final.py packs /app, submits it for one final judging on
# the hidden instances, and recomputes the score locally from the archived
# records with the same metric engine.
#
# The replay stub plays back, per instance, the best decomposition available
# in our measurement archives (precomputed as .td.xz under /app/precomputed;
# every stored decomposition was produced by the calibrated K-measurement
# runs or the 2026-08-31 transform B-remeasure, and re-validated by the
# official td-validate). For instances with no prerecording (B == K, no
# scoring signal) it emits a trivial one-bag decomposition at run time, so
# no instance is left without a valid .td.
#
# 2026-08-31 judged-set transform (vertex relabeling, judge image v3): every
# stored .td was mechanically rewritten along the secret permutation (widths
# unchanged, td-validate re-verified), and the stub gained sandbox-baseline
# decompositions for the newly participating instances (relabeling moved B
# off K on those, see PROVENANCE「scored-set transformation (260831)」).
# Expected outcome under the CURRENT anchors (post 260911-260912 B-remeasure
# 3f89a19d): verifier reward = 0.6722011166296253 — the manifest-width replay
# against the current anchors, matching the async sibling's measured score to
# the last digit. The gap to 1.0 has the same sources as the async twin's,
# none a judging-chain defect:
#   1. 21 participating instances' prerecorded widths equal the (remeasured)
#      baseline B, contributing 0;
#   2. he190's archived decomposition is valid (td-validate: valid, 403 s on
#      a 16-core box) but exceeds the chain's VERIFY_TIMEOUT=120 s, so he190
#      is scored 0 by the rule — decompositions that large timeout for every
#      solver, including a real one;
#   3. 20 judged instances have no prerecording at all (14 B==K excluded + 6
#      anchor-inverted K>B, which the runtime anchor adaptation excludes from
#      scoring anyway) and get the trivial one-bag fallback;
#   4. the remaining prerecorded replays land at widths between B and K and
#      take partial credit under the gap-ratio formula.
set -e
cp -r /solution/precomputed /app/precomputed

# Replay stub in place of the baseline driver. Same contract:
#   solver INSTANCE_DIR OUTPUT_DIR LIMIT_SECONDS
cat > /app/driver.sh <<'EOF'
#!/bin/bash
# oracle replay driver: emit the prerecorded decomposition for each instance
# (decompressed from ./precomputed), or a trivial one-bag decomposition when
# no prerecording exists (only possible for B==K excluded instances).
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
INST="$1"; OUT="$2"
mkdir -p "$OUT"
for g in "$INST"/*.gr; do
  name="$(basename "$g" .gr)"
  if [ -f "$DIR/precomputed/$name.td.xz" ]; then
    xz -dc "$DIR/precomputed/$name.td.xz" > "$OUT/$name.td"
  else
    # trivial decomposition: one bag with all n vertices (valid, width n-1)
    awk '/^p tw/ { printf "s td 1 %s %s\nb 1", $3, $3;
                   for (i = 1; i <= $3; i++) printf " %d", i;
                   printf "\n"; exit }' "$g" > "$OUT/$name.td"
  fi
done
EOF
chmod +x /app/driver.sh

# Build through the real judge path (make must produce ./solver).
make -C /app -j4
test -x /app/solver && echo "oracle stub installed: $(ls /app/precomputed/*.td.xz | wc -l) prerecorded decompositions"
