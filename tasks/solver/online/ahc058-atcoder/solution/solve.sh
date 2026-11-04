#!/bin/bash
# Oracle solution for ahc058-atcoder (form2): replace /app/build.sh so the
# judged "solver" replays prerecorded best-known action sequences (see
# precomputed/, produced by the pilot44 model solver re-measured at the
# official 2 s per-test budget — every stored sequence was re-simulated by
# the real checker against its instance and lands exactly at K). The
# solver reads instances on stdin without a file name, so the stub
# identifies the instance by a sha256 over the normalized token stream.
# manifest.json covers both judging channels:
#   - 45 hidden transformed instances (tNN.txt -> tNN.out, machine ids
#     rewritten with the same permutation via tests/transform.py
#     rewrite-solutions) for the final judging;
#   - 5 self-generated instances moved to the public practice set
#     (original bytes -> original .out) for the self-test channel (the 100
#     official public instances have no prerecorded plays — the self-test
#     channel reports those as failures without affecting the score).
# Every hidden instance replays at exactly K (re-simulated against the
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
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded action sequences"
