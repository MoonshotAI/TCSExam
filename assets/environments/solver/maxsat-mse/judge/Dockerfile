# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/maxsat-mse/tests/checker.py /tests/checker.py
COPY assets/environments/solver/maxsat-mse/judge/scoring.py /opt/maxsat/scoring.py
COPY tasks/solver/online/maxsat-mse/tests/reference.json /tests/reference.json
