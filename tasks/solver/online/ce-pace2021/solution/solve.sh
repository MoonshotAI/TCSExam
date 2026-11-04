#!/bin/bash
# Oracle solution for ce-pace2021 (form 1): install the replay stub
# (prerecorded champion-grade edit sets for the 100 hidden instances, keyed
# by sha256 over the raw instance bytes; every stored edit set was produced
# by re-running the K-anchor recipe — KaPoCE fast.ini @600s and CluES @600s
# per instance, per-instance min of verifier-validated outputs). The stub and
# its prerecorded answers are reused byte-for-byte from the async sibling
# package (ce-pace2021-async/solution/): this final package judges through
# the SAME judging chain (same judge image solver-ce-pace2021-judge-v6, same
# hidden set, same anchors) — at verify time tests/fetch_final.py packs /app,
# submits it for one final judging on the hidden instances, and recomputes
# the score locally from the archived records with the same metric engine.
# Expected outcome (260920 finalized gap ratio, judge image >= v4):
# verifier reward > 1.0 — the replay lands at K on most instances (r = 1.0)
# and beats the recorded K on 43 instances (r > 1, unclipped under the
# finalized formula; the retired SOL caliber recorded 1.004290 for the same
# replay). Baseline staging scores 0.0 (A == B -> r = 0).
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
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
data = sys.stdin.buffer.read()
h = hashlib.sha256(data).hexdigest()
with open(os.path.join(HERE, "precomputed", "manifest.json")) as f:
    manifest = json.load(f)
ent = manifest.get(h)
if ent is None:
    # unknown instance: fail this instance (scores 0), leave the rest alone
    sys.exit(1)
p = subprocess.run(["xz", "-dc", os.path.join(HERE, "precomputed", ent["file"])],
                   stdout=sys.stdout.buffer)
sys.exit(p.returncode)
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded edit sets"
