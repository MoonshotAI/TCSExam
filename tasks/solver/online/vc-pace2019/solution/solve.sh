#!/bin/bash
# Oracle (sanity validation only — this channel is never shown to agents):
# install a solver that answers every hidden instance with the precomputed
# proven-optimal cover harvested by measure/vc-kb (WeGotYouCovered / peaty
# under the official 1800 s budget, validated with the official checker,
# size == proven K).
#
# The judging protocol is stdin/stdout and the solver never learns the
# instance name, so the installed solver hashes the instance it receives
# on stdin and answers with the cover filed under that hash. The judge
# then rebuilds /app via build.sh (a no-op here) and runs the per-instance
# protocol; every judged instance comes out solved, so the expected
# reward is 1.0.
set -e
mkdir -p /app/precomputed
cp /solution/precomputed/*.vc /app/precomputed/

cat > /app/solver <<'EOF'
#!/bin/bash
# Precomputed-answer solver: hash the instance on stdin, print the cover
# harvested for exactly that instance content.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp)"
cat > "$tmp"
h="$(sha1sum "$tmp" | cut -d' ' -f1)"
rm -f "$tmp"
cat "$DIR/precomputed/$h.vc"
EOF
chmod +x /app/solver

# build.sh must succeed but must NOT rebuild/overwrite the precomputed solver.
cat > /app/build.sh <<'EOF'
#!/bin/bash
exit 0
EOF
echo "oracle solver installed ($(ls /app/precomputed/*.vc | wc -l) precomputed covers)"
