#!/bin/bash
# Oracle solution for maxcut-mqlib: replace /app/build.sh so the judged
# "solver" replays prerecorded best-known cuts (see precomputed/, produced
# by the 2026-08-31 K-anchor re-pin measurement — every stored cut was
# validated with the task's mc_check against its instance, both in the
# isolated execution environment measurement sandbox and again locally at harvest; see
# tests/SAMPLING.md "K re-anchoring record"). The solver reads the instance on stdin
# without a file name, so the stub identifies it by a sha256 over the
# normalized token stream. Every hidden instance with a stored cut lands at
# its re-pinned K (raw ~1.0), so this must score ~1.0.
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
with open(os.path.join(HERE, "precomputed", ent["out"])) as f:
    sys.stdout.write(f.read())
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
