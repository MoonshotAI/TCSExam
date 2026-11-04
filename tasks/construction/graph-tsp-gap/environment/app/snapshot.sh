#!/bin/sh
# Snapshot the /app/Task workspace into /logs/artifacts every 5 minutes.
# The proof in Task/Basic.lean is the valuable output of this task; this
# keeps it recoverable even if anything later in the pipeline breaks.
while true; do
  mkdir -p /logs/artifacts/snapshot 2>/dev/null
  rm -rf /logs/artifacts/snapshot/Task 2>/dev/null
  cp -a /app/Task /logs/artifacts/snapshot/Task 2>/dev/null
  sleep 300
done
