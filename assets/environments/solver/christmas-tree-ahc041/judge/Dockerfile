# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/christmas-tree-ahc041/tests/checker.py /tests/checker.py
COPY tasks/solver/online/christmas-tree-ahc041/tests/scoring.py /opt/ahc041/scoring.py
COPY tasks/solver/online/christmas-tree-ahc041/tests/reference-hidden.json /tests/reference.json
