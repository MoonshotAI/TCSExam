# SPDX-License-Identifier: Apache-2.0
ARG TCSEXAM_OFFLINE_BACKEND_IMAGE
FROM ${TCSEXAM_OFFLINE_BACKEND_IMAGE}
COPY tasks/solver/offline/maxcut-mqlib/tests/runtime/ /opt/public_judge/
COPY tasks/solver/offline/maxcut-mqlib/tests/anchors.json tasks/solver/offline/maxcut-mqlib/tests/metric_config.json tasks/solver/offline/maxcut-mqlib/tests/reference.json /tests/
COPY tasks/solver/offline/maxcut-mqlib/tests/metric/ /tests/metric/
COPY tasks/solver/offline/maxcut-mqlib/tests/test.sh /tests/test.sh
RUN chmod 755 /tests/test.sh && mkdir -p /work /submission /logs/verifier
RUN mkdir -p /opt/public-instances-judge && python3 /judge/prepare.py /tests/instances && cp -a /tests/instances/. /opt/public-instances-judge/
WORKDIR /work
ENTRYPOINT []
CMD ["sleep", "infinity"]
