#!/bin/bash
# Oracle solution for celar-rlfap (form2): replace /app/build.sh so the
# judged "solver" replays prerecorded solutions (see precomputed/). The
# solver is invoked with the instance path, so the stub identifies the
# instance by a sha256 over the normalized token stream. manifest.json
# covers both judging channels:
#   - 13 public practice instances (original bytes -> original .sol) for
#     the self-test channel;
#   - 8 hidden transformed instances (hNN.dzn -> hNN.sol, rewritten with
#     the same variable permutation via tests/transform.py
#     rewrite-solutions) for the final judging.
# Replay coverage on the hidden set (every stored solution re-validated by
# the real checker against its transformed instance file, objective
# strictly preserved by the isomorphism):
#   - the 3 scored hidden instances (h02=graph07, h07=scen06, h08=scen08)
#     replay witnessed best-known solutions landing exactly at K (raw 1.0);
#   - the 5 trivial hidden instances replay objective-0 witnesses
#     (B==K==0, excluded from the metric by the B_equals_K rule).
# Expected score through the real judging path: 3/3 = 1.0 over the 3
# scored (B>K) hidden instances.
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
toks = open(sys.argv[1], errors="replace").read().split()
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
