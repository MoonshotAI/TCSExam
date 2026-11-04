# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies the unchanged data, tools and worker.
ARG TCSEXAM_BACKEND_BASE
FROM ${TCSEXAM_BACKEND_BASE}
COPY tasks/solver/online/glasscut-roadef2018/tests/checker.py /tests/checker.py
COPY assets/environments/solver/glasscut-roadef2018/judge/scoring.py /opt/glasscut/scoring.py
COPY tasks/solver/online/glasscut-roadef2018/tests/reference.json /tests/reference.json
