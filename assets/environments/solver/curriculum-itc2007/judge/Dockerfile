# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/curriculum-itc2007/tests/checker.py /tests/checker.py
COPY tasks/solver/online/curriculum-itc2007/tests/scoring.py /opt/ctt/scoring.py
COPY tasks/solver/online/curriculum-itc2007/tests/reference.json /tests/reference.json
