#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) that reads a QDIMACS formula on stdin and prints the answer on
# stdout as `s TRUE` or `s FALSE`. Whichever verdict it prints, the solver
# must also write a certificate to the file path given in the environment
# variable QBF_PROOF_PATH: a (long-distance) Q-resolution proof in Qute's
# compact QRP-style format (what `qute --trace` emits on stdout) or in
# classic ASCII QRP format with an `r SAT` / `r UNSAT` trailer line. The
# judge checks the certificate with qrp2rup + drat-trim — an unverifiable
# certificate counts as no answer. When QBF_PROOF_PATH is unset (e.g. your
# own quick tests) proof production may be skipped.
#
# You may edit this script (or the solver source in ./qute) as you like —
# e.g. add more source files, change flags, or produce a different wrapper —
# as long as the solver ends up as an executable honoring the I/O contract.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/qute"
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
cp qute "$ROOT/qute-bin"

# Baseline configuration. Qute's own README warns that dependency learning
# (its default) "in certain cases ... can be detrimental to performance" —
# on the query-style families of this benchmark the stock default stalls
# for minutes on instances the competition edition solved in under a
# second, so the baseline ships with dependency learning switched off.
# (Making smarter use of it is exactly the kind of improvement you can
# explore.)
QUTE_FLAGS="--dependency-learning off"

# /app/solver is a thin wrapper: qute wants a file path, the contract is
# stdin/stdout, so the formula is spooled to a temp file. With --trace,
# this qute edition prints the QRP proof (and nothing else) on stdout and
# signals the verdict via its exit code (10 = true, 20 = false), so the
# proof goes to QBF_PROOF_PATH and the status line is printed by us.
cat > "$ROOT/solver" <<EOF
#!/bin/bash
ROOT="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="\$ROOT/qute/build/docopt.cpp:\${LD_LIBRARY_PATH}"
tmp="\$(mktemp /tmp/qbf-input-XXXXXX.qdimacs)"
cat > "\$tmp"
if [ -n "\$QBF_PROOF_PATH" ]; then
  "\$ROOT/qute-bin" $QUTE_FLAGS --trace "\$tmp" > "\$QBF_PROOF_PATH" 2>/dev/null
else
  "\$ROOT/qute-bin" $QUTE_FLAGS "\$tmp" >/dev/null 2>&1
fi
rc=\$?
rm -f "\$tmp"
if [ "\$rc" -eq 10 ]; then
  echo "s TRUE"
  exit 10
fi
if [ "\$rc" -eq 20 ]; then
  echo "s FALSE"
  exit 20
fi
echo "s UNKNOWN"
exit 0
EOF
chmod +x "$ROOT/solver"
