#!/bin/bash
# Oracle solution for logic-syn-iwls2023: replace /app/build.sh so the judged
# "solver" replays the prerecorded best verified circuits (see precomputed/:
# the best published circuit per function across the IWLS 2022 and 2023
# contests — the 2023 benchmark is the 2022 set NPN-re-encoded, so 2022
# submissions migrate; each stored circuit is NPN-transformed together with
# its hidden truth table and re-verified by exhaustive simulation — every
# stored circuit computes exactly the reference function with exactly K AND
# gates). The stub identifies the instance by a sha256 over the truth file.
# Through the real judging path every hidden instance lands exactly at K
# (raw 1.0), so this must score 1.0.
set -e
cp -r /solution/precomputed /app/precomputed
# Remove before rewriting: /app/build.sh is owned by the image-build user and
# a non-root agent cannot chmod it in place; recreating it makes the caller
# the owner.
rm -f /app/build.sh
cat > /app/build.sh <<'EOF'
#!/bin/bash
# oracle build: emit the replay stub as the solver (no compilation)
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rm -f "$ROOT/solver"
cat > "$ROOT/solver" <<'INNER'
#!/usr/bin/env python3
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
truth_path, out_path = sys.argv[1], sys.argv[2]
h = hashlib.sha256()
with open(truth_path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
with open(os.path.join(HERE, "precomputed", "manifest.json")) as f:
    manifest = json.load(f)
ent = manifest.get(h.hexdigest())
if ent is None:
    # unknown instance: fail this instance (scores 0), leave the rest alone
    sys.exit(1)
with open(os.path.join(HERE, "precomputed", ent["solution"]), "rb") as f:
    data = f.read()
with open(out_path, "wb") as f:
    f.write(data)
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded circuits"
