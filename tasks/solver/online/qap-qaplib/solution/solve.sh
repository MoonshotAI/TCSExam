#!/bin/bash
# Oracle solution for qap-qaplib: replace /app/build.sh so the judged
# "solver" replays the prerecorded best-known permutations (see
# precomputed/: the 134 QAPLIB-registered permutations plus the two
# tai10a/tai10b optima from exact enumeration, rewritten onto the judged
# transformed instances per p'(pi(i)) = sigma(p(i)) by
# tests/transform.py bake-oracle — every stored permutation recomputes
# exactly to K on its transformed instance). The solver reads instances on
# stdin without a file name, so the stub identifies the instance by a
# sha256 over the normalized token stream. Through the real judging path
# every judged instance lands exactly at K (raw 1.0 on every participating
# instance), so this must score 1.0.
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
with open(os.path.join(HERE, "precomputed", ent["perm"])) as f:
    sys.stdout.write(f.read())
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded permutations"
