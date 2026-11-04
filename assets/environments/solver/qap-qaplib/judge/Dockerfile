# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/qap-qaplib/tests/checker.py /tests/checker.py
COPY tasks/solver/online/qap-qaplib/tests/scoring.py /opt/qap/scoring.py
COPY tasks/solver/online/qap-qaplib/tests/reference.json /tests/reference.json
