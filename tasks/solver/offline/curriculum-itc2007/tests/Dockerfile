# SPDX-License-Identifier: Apache-2.0
ARG TCSEXAM_OFFLINE_BACKEND_IMAGE
FROM ${TCSEXAM_OFFLINE_BACKEND_IMAGE}
COPY tasks/solver/offline/curriculum-itc2007/tests/runtime/ /opt/public_judge/
COPY tasks/solver/offline/curriculum-itc2007/tests/anchors.json tasks/solver/offline/curriculum-itc2007/tests/metric_config.json tasks/solver/offline/curriculum-itc2007/tests/reference.json /tests/
COPY tasks/solver/offline/curriculum-itc2007/tests/metric/ /tests/metric/
COPY tasks/solver/offline/curriculum-itc2007/tests/test.sh /tests/test.sh
RUN chmod 755 /tests/test.sh && mkdir -p /work /submission /logs/verifier
WORKDIR /work
ENTRYPOINT []
CMD ["sleep", "infinity"]
