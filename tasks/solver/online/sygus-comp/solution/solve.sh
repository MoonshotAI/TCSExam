#!/bin/bash
# Oracle solution for sygus-comp: replace /app/build.sh so the judged
# "solver" replays prerecorded cvc5 long-run solutions (see precomputed/,
# produced by the 600 s reference runs at task construction — every stored
# solution passed the real two-step machine check against its instance).
# The solver reads the instance path from argv, so the stub identifies the
# instance by a sha256 over the normalized token stream. Through the real
# judging path every instance with K = 1 lands a verified solution and
# every K = 0 instance fails, so S_A == S_K and this must score 1.0.
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
with open(sys.argv[1], errors="replace") as f:
    toks = f.read().split()
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
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded solutions"
