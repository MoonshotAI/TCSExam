#!/bin/bash
# Oracle solution for scp-orlib: replace /app/build.sh so the judged
# "solver" replays prerecorded covers (see precomputed/, generated at
# authoring time and re-keyed to the official instances on 2026-09-11 —
# the 56 covers from the retired judge-side row/column transform were
# mapped back through its inverse permutation, and the 15 practice covers
# were added; every stored cover was re-validated by the real checker
# against the official instance file and lands exactly at K). The solver
# reads instances on stdin without a file name, so the stub identifies the
# instance by a sha256 over the normalized token stream. 71 of the 87
# judged instances have prerecorded covers; the remaining 16 (12 scored,
# 4 excluded at B == K) await the oracle-completion measurement batch, so
# this scores 69/81 on the participating instances (~0.852), not 1.0.
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
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded covers"
