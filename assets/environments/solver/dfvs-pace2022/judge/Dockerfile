# SPDX-License-Identifier: Apache-2.0
# Context: repository root. Frozen base supplies data and the worker; the
# separately prepared official resource supplies the checker source and binary.
ARG TCSEXAM_BACKEND_BASE
ARG TCSEXAM_TOOLS_IMAGE
FROM ${TCSEXAM_TOOLS_IMAGE} AS tcsexam_tools
FROM ${TCSEXAM_BACKEND_BASE}
COPY --from=tcsexam_tools /payload/rootfs/ /
COPY tasks/solver/online/dfvs-pace2022/tests/checker.py /tests/checker.py
COPY tasks/solver/online/dfvs-pace2022/environment/app/scoring.py /opt/dfvs/scoring.py
COPY tasks/solver/online/dfvs-pace2022/tests/reference.json /tests/reference.json
