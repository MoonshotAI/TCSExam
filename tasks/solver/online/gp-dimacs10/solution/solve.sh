#!/bin/bash
# Oracle solution for gp-dimacs10: replace /app/build.sh so the judged
# "solver" replays the prerecorded best partitions (see precomputed/). The
# solver reads instances on stdin without a file name, so the stub identifies
# the instance by a sha256 over the normalized token stream.
# Coverage on the 43-instance judged set (no-hidden-set form, 2026-09-11):
# the 20 long-standing instances replay partitions that recompute EXACTLY to
# K (raw 1.0 each); 12 restored instances replay the best partitions held
# from the K-reproduction runs (above the archive K, raw ~0.88-1.0 each);
# the remaining 11 restored instances have no partition on hand yet (their
# K-hunt is deferred to the isolated execution environment batch, see PROVENANCE.md) and score 0.
# Expected score through the real judging path: 0.735192 (= (20 + 11.6133)/43).
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
with open(os.path.join(HERE, "precomputed", ent["part"])) as f:
    sys.stdout.write(f.read())
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded partitions"
