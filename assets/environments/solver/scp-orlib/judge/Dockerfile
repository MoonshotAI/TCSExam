# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/scp-orlib/tests/checker.py /tests/checker.py
COPY tasks/solver/online/scp-orlib/tests/scoring.py /opt/scp/scoring.py
COPY tasks/solver/online/scp-orlib/tests/reference.json /tests/reference.json
