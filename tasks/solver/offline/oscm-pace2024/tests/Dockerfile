# SPDX-License-Identifier: Apache-2.0
ARG TCSEXAM_OFFLINE_BACKEND_IMAGE
FROM ${TCSEXAM_OFFLINE_BACKEND_IMAGE}
RUN mkdir -p /opt/public_judge && cp -p /tests/test.sh /opt/public_judge/frozen-test.sh
COPY assets/environments/solver/offline-runtime/*.py assets/environments/solver/offline-runtime/LICENSE assets/environments/solver/offline-runtime/python-shim.sh /opt/public_judge/
COPY tasks/solver/offline/oscm-pace2024/tests/ /tests/
COPY tasks/solver/offline/oscm-pace2024/tests/runtime/task.json /opt/public_judge/task.json
RUN mkdir -p /opt/public_judge/bin /work /submission /logs/verifier \
 && cp /opt/public_judge/python-shim.sh /opt/public_judge/bin/python3 \
 && cp /opt/public_judge/python-shim.sh /opt/public_judge/bin/python \
 && chmod 755 /opt/public_judge/bin/python* /tests/test.sh
WORKDIR /work
ENTRYPOINT []
CMD ["sleep", "infinity"]
