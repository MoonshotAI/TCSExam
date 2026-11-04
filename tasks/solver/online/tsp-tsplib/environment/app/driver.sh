#!/bin/bash
# Baseline driver for the tsp-tsplib task (per-instance protocol).
#
# usage: solver INSTANCES_DIR OUTPUT_DIR LIMIT_SECONDS
#
# INSTANCES_DIR holds exactly one <name>.tsp; the tour is written to
# OUTPUT_DIR/<name>.tour. The compute budget is the limit minus a small
# flush margin; `timeout` backstops it and the solver's SIGTERM handler
# flushes its incumbent (tsp_bin also rewrites the tour file after every
# improvement, so the best-so-far tour is always on disk).
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
INST="$1"; OUT="$2"; LIMIT="$3"
mkdir -p "$OUT"
f=$(ls "$INST"/*.tsp | head -1)
[ -n "$f" ] || exit 0
name="$(basename "$f" .tsp)"
margin=10
budget=$(( LIMIT - margin ))
[ "$budget" -ge 1 ] || budget=1
timeout -s TERM -k 15 "$budget" "$DIR/tsp_bin" "$f" "$OUT/$name.tour" "$budget" 0
