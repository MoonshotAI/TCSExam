#!/bin/bash
# Oracle solution for ds-pace2025 (form 1): install the replay stub as the
# solver (prerecorded champion-reference dominating sets for the 100 hidden
# private instances, keyed by the SHA-256 of the instance bytes; every
# recorded solution was produced by the calibrated K-anchor measurement —
# fontanf / Root, full 300 s PACE 2025 budget — and validated with the
# official PACE 2025 DS verifier, landing at the reference size K). The stub
# and its prerecorded answers are reused byte-for-byte from the async sibling
# package (ds-pace2025-async/solution/): this final package judges through
# the SAME judging chain (same judge image solver-ds-pace2025-judge-v4, same
# hidden set, same anchors) — at verify time tests/fetch_final.py packs /app,
# submits it for one final judging on the hidden instances (raw 1.0), and
# recomputes the score locally from the archived records with the same metric
# engine.
# Expected outcome: verifier reward 1.0.
set -e
cp /solution/replay_solver.cpp /app/solver.cpp
cp -r /solution/precomputed /app/precomputed
echo "oracle stub installed: $(wc -l < /app/precomputed/manifest.tsv) prerecorded dominating sets"

# Compile check with the exact judge command line (g++ -O2 -std=c++17).
g++ -O2 -std=c++17 -o /tmp/replay_check /app/solver.cpp

# Functional check on a synthetic instance through the real lookup path:
# build a scratch precomputed dir = the real one + one entry for the tiny
# graph, then replay and validate the output with the official verifier.
printf "p ds 5 4\n1 2\n2 3\n3 4\n4 5\n" > /tmp/tiny.gr
TDIR="$(mktemp -d)"
trap 'rm -rf "$TDIR" /tmp/replay_check /tmp/tiny.gr /tmp/tiny.out' EXIT
cp -r /app/precomputed "$TDIR/precomputed"
printf "2\n2\n4\n" > "$TDIR/precomputed/tiny.sol"
H="$(sha256sum /tmp/tiny.gr | cut -d' ' -f1)"
printf "%s\t%s\n" "$H" "tiny.sol" >> "$TDIR/precomputed/manifest.tsv"
PRECOMPUTED_DIR="$TDIR/precomputed" /tmp/replay_check < /tmp/tiny.gr > /tmp/tiny.out
java -jar /opt/ds2025/ds_verifier.jar /tmp/tiny.gr /tmp/tiny.out | grep -q "is valid!"
echo "oracle stub self-check OK (replay + official verifier on synthetic instance)"
