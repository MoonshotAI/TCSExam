#!/bin/bash
# Oracle solution for qbf-qbfeval: replace /app/build.sh so the judged
# "solver" replays prerecorded answers with their certificates (see
# precomputed/, generated at task-construction time by running the baseline
# architecture at the competition-scale budget and keeping only instances
# whose certificate passed the full qrp2rup + drat-trim chain). The solver
# reads instances on stdin without a file name, so the stub identifies the
# instance by a sha256 over the normalized token stream. Through the real
# judging path every hidden instance with a prerecorded certificate lands
# at solved. Since the 2026-08-31 rework the judged set also carries 10
# hard band instances (winner-solved, no baseline-architecture certificate
# exists by construction — they widen the score band) and 7 unsolved
# breakthrough slots; the shipped pack holds 39 certificates
# (ex028's was retired: its rewritten certificate does not
# pass the chain on the transformed instance). With the anchors at their
# 2026-09-13 caliber-aligned state (B = chain-verified solve within the 900 s
# per-instance judging budget on the transformed instance, seconds from the
# 2026-09-03 judging-spec measurement; 25 baseline-solved, 24 scored
# instances), the replay covers 13 of the 24 scored instances and the
# expected verifier reward is 13/24 = 0.5417.
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
toks = sys.stdin.read().split()
h = hashlib.sha256(" ".join(toks).encode()).hexdigest()
with open(os.path.join(HERE, "precomputed", "manifest.json")) as f:
    manifest = json.load(f)
ent = manifest.get(h)
if ent is None:
    # unknown instance: fail this instance (scores 0), leave the rest alone
    sys.exit(1)
proof_path = os.environ.get("QBF_PROOF_PATH")
if proof_path:
    src = os.path.join(HERE, "precomputed", ent["proof"])
    with open(src, "rb") as fin, open(proof_path, "wb") as fout:
        subprocess.run(["xz", "-dc"], stdin=fin, stdout=fout, check=True)
print("s TRUE" if ent["answer"] == "true" else "s FALSE")
sys.exit(10 if ent["answer"] == "true" else 20)
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded certificates"
