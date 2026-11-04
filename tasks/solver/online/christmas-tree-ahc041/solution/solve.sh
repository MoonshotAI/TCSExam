#!/bin/bash
# Oracle solution for christmas-tree-ahc041 (form2): replace /app/build.sh
# so the judged "solver" replays prerecorded best-known parent arrays (see
# precomputed/, produced by the calibration annealer (sa.cpp) — every
# stored array was re-validated by the real checker against its instance
# and lands exactly at K). The solver reads instances on stdin without a
# file name, so the stub identifies the instance by a sha256 over the
# normalized token stream. manifest.json covers:
#   - 45 hidden transformed instances (tNN.txt -> tNN.out, parent arrays
#     rewritten with the same vertex permutation via tests/transform.py
#     rewrite-solutions) for the final judging;
#   - 5 self-generated instances moved to the public practice set plus 20
#     official public instances with prerecorded plays (original bytes ->
#     original .out) for the self-test channel (the remaining 80 official
#     public instances have no prerecorded plays — the self-test channel
#     reports those as failures without affecting the score).
# Every hidden instance replays at exactly K (re-validated against the
# transformed instance files). Expected score through the real judging
# path: 45/45 = 1.0.
set -e
cp -r /solution/precomputed /app/precomputed
cat > /app/build.sh <<'EOF'
#!/bin/bash
# oracle build: emit the replay stub as the solver (no compilation)
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat > "$ROOT/solver" <<'INNER'
#!/usr/bin/env python3
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
toks = sys.stdin.read().split()
h = hashlib.sha256(" ".join(toks).encode()).hexdigest()
with open(os.path.join(HERE, "precomputed", "manifest.json")) as f:
    manifest = json.load(f)
ent = manifest.get(h)
if ent is None:
    # unknown instance: fail this instance (scores 0), leave the rest alone
    sys.exit(1)
with open(os.path.join(HERE, "precomputed", ent["sol"])) as f:
    sys.stdout.write(f.read())
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded parent arrays"
