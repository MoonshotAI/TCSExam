# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/maxcut-mqlib/tests/checker.py /tests/checker.py
COPY tasks/solver/online/maxcut-mqlib/tests/scoring.py /opt/maxcut/scoring.py
COPY tasks/solver/online/maxcut-mqlib/tests/reference.json /tests/reference.json
