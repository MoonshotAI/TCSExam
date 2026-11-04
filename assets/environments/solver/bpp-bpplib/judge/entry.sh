#!/bin/bash
if [ "${INSTANCE_SET:-hidden}" = "public" ]; then
  mkdir -p /logs/verifier
  exec python3 /tests-public/checker.py
fi
exec bash "${TESTS_DIR:-/tests}/test.sh"
