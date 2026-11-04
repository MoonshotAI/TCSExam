#!/bin/bash
# Baseline driver for the tw-heuristic task (per-instance protocol).
#
# usage: solver INSTANCES_DIR OUTPUT_DIR POOL_SECONDS
#
# Strategy: split the pool into equal slices, one per instance, and run
# FlowCutter (seed 0) on each instance for its slice. `timeout` sends SIGTERM
# at the slice boundary; FlowCutter answers SIGTERM by printing the best
# decomposition found so far — see src/pace.cpp.
#
# This equal-split policy is deliberately naive: big instances are exactly
# where 60 s runs out first. Allocating the pool smarter (and restarting with
# more seeds) is the first thing to improve.
# FlowCutter can take a long time to honor SIGTERM on huge instances (it
# finishes the current round first — measured: minutes on a 26k-vertex
# graph). `timeout -k` hard-caps the flush phase, and each instance's compute
# budget is trimmed by a flush margin so a slow death never eats the next
# instance's slice.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
INST="$1"; OUT="$2"; POOL="$3"
mkdir -p "$OUT"
mapfile -t gs < <(ls "$INST"/*.gr | sort)
N=${#gs[@]}
[ "$N" -gt 0 ] || exit 0
slice=$(( POOL / N ))
[ "$slice" -ge 1 ] || slice=1
margin=15
[ "$slice" -le $(( margin + 5 )) ] && margin=0
deadline=$(( $(date +%s) + POOL ))
for g in "${gs[@]}"; do
  name="$(basename "$g" .gr)"
  left=$(( deadline - $(date +%s) ))
  [ "$left" -ge 1 ] || break
  s=$slice
  [ "$s" -gt "$left" ] && s=$left
  budget=$(( s - margin ))
  [ "$budget" -ge 1 ] || budget=1
  timeout -s TERM -k 10 "$budget" "$DIR/fc_bin" -s 0 < "$g" > "$OUT/$name.td" 2>/dev/null
done
