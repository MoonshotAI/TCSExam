# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/maxclique-dimacs/tests/checker.py /tests/checker.py
COPY tasks/solver/online/maxclique-dimacs/tests/scoring.py /opt/maxclique/scoring.py
COPY tasks/solver/online/maxclique-dimacs/tests/reference.json /tests/reference.json
