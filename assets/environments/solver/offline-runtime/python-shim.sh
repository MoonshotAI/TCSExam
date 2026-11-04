#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
set -eu
for argument in "$@"; do
    if [ "$argument" = /tests/checker.py ]; then
        exec "$TCSEXAM_PYTHON_EXECUTABLE" /opt/public_judge/judge_entry.py
    fi
done
exec "$TCSEXAM_PYTHON_EXECUTABLE" "$@"
