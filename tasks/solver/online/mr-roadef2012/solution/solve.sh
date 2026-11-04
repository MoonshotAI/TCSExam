#!/bin/bash
# Oracle solution for mr-roadef2012: replace /app/build.sh so the judged
# "solver" replays the prerecorded best verified assignments (see
# precomputed/, produced by the K-production runs recorded in
# tests/calibration/make_reference.py — every stored assignment was checked
# by the official ROADEF checker and recomputes exactly to K). The stub
# identifies the instance by a sha256 over the model file. Through the real
# judging path every hidden instance lands exactly at K (raw 1.0), so this
# must score 1.0.
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
model_path, initial_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
h = hashlib.sha256()
with open(model_path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
with open(os.path.join(HERE, "precomputed", "manifest.json")) as f:
    manifest = json.load(f)
ent = manifest.get(h.hexdigest())
if ent is None:
    # unknown instance: fail this instance (scores 0), leave the rest alone
    sys.exit(1)
with open(os.path.join(HERE, "precomputed", ent["solution"])) as f:
    data = f.read()
with open(out_path, "w") as f:
    f.write(data)
INNER
chmod +x "$ROOT/solver"
EOF
chmod +x /app/build.sh
bash /app/build.sh
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded assignments"
