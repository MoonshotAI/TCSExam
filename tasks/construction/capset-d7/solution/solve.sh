#!/bin/bash
# Reference sanity submission: the {0,1}^7 cube cap (128 points, the trivial
# baseline -> alpha = 0 by design). Copies the reference proof into /app.
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
