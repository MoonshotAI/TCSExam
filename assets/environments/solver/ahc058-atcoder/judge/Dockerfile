# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/ahc058-atcoder/tests/checker.py /tests/checker.py
COPY tasks/solver/online/ahc058-atcoder/tests/scoring.py /opt/ahc058/scoring.py
COPY tasks/solver/online/ahc058-atcoder/tests/reference-hidden.json /tests/reference.json
