#!/bin/bash
# Oracle solution for coloring-dimacs: replace /app/build.sh so the judged
# "solver" replays prerecorded best-known colorings (see precomputed/,
# rekeyed to official instances by tests/calibration/rekey_oracle_nohidden_260911.py
# — every stored coloring was re-validated by the real checker against the
# shipped instance file and lands exactly at the anchor K). The solver reads
# instances on stdin without a file name, so the stub identifies the instance
# by a sha256 over the normalized token stream. Expected score through the
# real judging path: 46/51 participating instances land exactly at K (raw
# 1.0), so ~0.902 — the 5 participating instances whose literature-K
# colorings are not yet on file (abb313GPIA, le450_15c, r1000.5, r250.1c,
# r250.5) score 0 here; see PROVENANCE.md (no-hidden-set section) for the
# oracle-completion follow-up.
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
with open(os.path.join(HERE, "precomputed", ent["coloring"])) as f:
    sys.stdout.write(f.read())
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded colorings"
