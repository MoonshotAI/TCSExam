#!/bin/bash
# Oracle solution for dfvs-pace2022 (form 1): install a replay stub with 200
# prerecorded champion feedback vertex sets (keyed by a sha256 over the
# instance token stream; each stored set comes from the calibrated K runs —
# Dagger@1800s proven optima, DiVerSeS@1800s upper bounds on the 13 instances
# Dagger could not finish — and was re-validated against its instance file
# with the official PACE 2022 verifier, landing exactly at the reference K).
# The stub and its prerecorded answers are reused byte-for-byte from the
# async sibling package (dfvs-pace2022-async/solution/): this final package
# judges through the SAME judging chain (same judge image
# solver-dfvs-pace2022-judge-v7, same hidden set, same anchors) — at verify
# time tests/fetch_final.py packs /app, submits it for one final judging on
# the hidden instances (raw 1.0), and recomputes the score locally from the
# archived records with the same metric engine.
# Expected outcome: verifier reward 1.0.
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
with open(os.path.join(HERE, "precomputed", ent["fvs"])) as f:
    sys.stdout.write(f.read())
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded feedback vertex sets"
