# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/jsplib-jssp/tests/checker.py /tests/checker.py
COPY tasks/solver/online/jsplib-jssp/tests/scoring.py /opt/jssp/scoring.py
COPY tasks/solver/online/jsplib-jssp/tests/reference.json /tests/reference.json
