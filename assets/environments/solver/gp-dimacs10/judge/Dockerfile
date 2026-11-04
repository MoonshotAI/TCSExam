# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/gp-dimacs10/tests/checker.py /tests/checker.py
COPY tasks/solver/online/gp-dimacs10/tests/scoring.py /opt/gp/scoring.py
COPY tasks/solver/online/gp-dimacs10/tests/reference.json /tests/reference.json
