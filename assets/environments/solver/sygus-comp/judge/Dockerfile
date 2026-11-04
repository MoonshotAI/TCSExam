# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/sygus-comp/tests/checker.py /tests/checker.py
COPY tasks/solver/online/sygus-comp/tests/scoring.py /opt/sygus/scoring.py
COPY tasks/solver/online/sygus-comp/tests/reference.json /tests/reference.json
