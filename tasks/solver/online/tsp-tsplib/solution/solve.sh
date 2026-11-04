#!/bin/bash
# Oracle solution for tsp-tsplib (form 1): install the replay stub
# (prerecorded best tours for all 111 judged instances — since 260911 the
# judged set is the full official TSPLIB set under official names, no
# transform, no codenames — keyed by a sha256 over the official instance file
# bytes; 109 of them land exactly at the proven optimum K under the
# judge-side tsp_check verifier, the remaining two — d657, linhp318 — land at
# the best tour we could establish for the judged instance files, which sit
# above the literature K because the published K for those instances
# corresponds to revised instance files; pla33810's official .opt.tour
# re-validated exactly at K under the pristine tsp_check in the 260911
# re-bake, retiring the third former gap). The stub and its prerecorded tours
# are reused byte-for-byte from the async sibling package
# (tsp-tsplib-async/solution/): this final package has NO hidden set — the
# judged set is the same full public TSPLIB collection shipped in the agent's
# environment — and at verify time tests/fetch_final.py packs /app, submits
# it for one final judging through the same judging service and judge image
# (solver-tsp-tsplib-judge-v10), then recomputes the score locally from the
# archived records with the same metric engine and anchors, taking
# best(public self-test history, the final judging).
# Expected outcome: verifier reward ~0.9814.
set -e
cp -r /solution/precomputed /app/precomputed
cat > /app/driver.sh <<'EOF'
#!/usr/bin/env python3
# oracle replay driver: identify the instance by the sha256 of its file
# bytes and replay the prerecorded tour; unknown instances fail (score 0
# for that instance only).
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
inst_dir, out_dir = sys.argv[1], sys.argv[2]
files = [f for f in os.listdir(inst_dir) if f.endswith(".tsp")]
if not files:
    sys.exit(1)
name = files[0][:-4]
with open(os.path.join(inst_dir, files[0]), "rb") as f:
    h = hashlib.sha256(f.read()).hexdigest()
with open(os.path.join(HERE, "precomputed", "manifest.json")) as f:
    manifest = json.load(f)
ent = manifest.get(h)
if ent is None:
    sys.exit(1)
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(HERE, "precomputed", ent["tour"])) as src, \
     open(os.path.join(out_dir, name + ".tour"), "w") as dst:
    dst.write(src.read())
EOF
chmod +x /app/driver.sh
make -C /app
echo "oracle stub installed: $(python3 -c 'import json; print(len(json.load(open("/app/precomputed/manifest.json"))))') prerecorded tours"
