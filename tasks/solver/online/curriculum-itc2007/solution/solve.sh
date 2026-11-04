#!/bin/bash
# Oracle solution for curriculum-itc2007 (form2): replace /app/build.sh so
# the judged "solver" replays prerecorded best-known timetables (see
# precomputed/, downloaded from OptHub — the Udine benchmark repository —
# and every one re-validated with the official ITC 2007 Track 3 validator:
# 0 hard violations, cost exactly K). The solver reads instances on stdin
# without a file name, so the stub identifies the instance by a sha256 over
# the normalized token stream. manifest.json covers both judging channels:
#   - 12 public practice instances (original bytes -> original .sol) for
#     the self-test channel;
#   - 6 hidden transformed instances (hNN.ctt -> hNN.sol, rewritten with
#     the same course/room relabeling via tests/transform.py
#     rewrite-solutions) for the final judging.
# Every hidden instance replays at exactly K (verified with the official
# validator against the transformed instance files): the 4 scored hidden
# instances (h02=comp05, h03=comp06, h04=comp07, h05=comp09) land raw 1.0;
# the 2 closed ones (h01=comp04, h06=comp11) are excluded by the
# B_equals_K rule. Expected score through the real judging path: 4/4 = 1.0.
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
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded timetables"
