# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/itc2021-sports-timetabling/tests/checker.py /tests/checker.py
COPY tasks/solver/online/itc2021-sports-timetabling/tests/scoring.py /tests/scoring.py
COPY tasks/solver/online/itc2021-sports-timetabling/tests/reference.json /tests/reference.json
