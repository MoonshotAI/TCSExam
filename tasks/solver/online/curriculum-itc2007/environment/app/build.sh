#!/bin/bash
# Build script run by the judge (and by score_public.py). The only contract:
# after `bash /app/build.sh` there is an executable /app/solver that reads a
# .ctt instance on stdin and writes a timetable on stdout. The shipped
# version compiles the vendored CPSolver ITC 2007 wrapper sources against
# the bundled jars and emits /app/solver as a small launcher script.
# Replace anything you like — add sources under /app (keep them inside
# cpsolver-src/ or adapt this script), tune ctt.properties, or rewrite the
# solver from scratch in any language.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$ROOT/classes"
find "$ROOT/cpsolver-src" -name '*.java' | sort > "$ROOT/.sources"
javac -nowarn -encoding UTF-8 -cp "$ROOT/lib/*" -d "$ROOT/classes" @"$ROOT/.sources"
rm -f "$ROOT/.sources"
cp "$ROOT/ctt.properties" "$ROOT/classes/ctt.properties"
cat > "$ROOT/solver" <<'EOF'
#!/bin/bash
# Shipped baseline solver: CPSolver (the ITC 2007 Track 3 winner) with a
# fixed iteration budget and a fixed seed (see ctt.properties), so its
# results are reproducible on any machine. Reads a .ctt instance on stdin,
# writes the timetable (<CourseID> <RoomID> <Day> <Day_Period> lines, one
# per lecture) on stdout.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/instance.ctt"
java -Xmx2g -cp "$ROOT/classes:$ROOT/lib/*" \
  net.sf.cpsolver.itc.ItcTest ctt "$TMP/instance.ctt" "$TMP/solution.out" -1 12345 1>&2
cat "$TMP/solution.out"
EOF
chmod +x "$ROOT/solver"
echo "built: $ROOT/solver"
