# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/celar-rlfap/tests/checker.py /tests/checker.py
COPY tasks/solver/online/celar-rlfap/tests/scoring.py /opt/celar/scoring.py
COPY tasks/solver/online/celar-rlfap/tests/reference.json /tests/reference.json
