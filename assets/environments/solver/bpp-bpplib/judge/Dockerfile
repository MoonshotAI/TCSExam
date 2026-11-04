# SPDX-License-Identifier: Apache-2.0
ARG TCSEXAM_BACKEND_BASE
ARG JUDGING_DATA_IMAGE
FROM ${JUDGING_DATA_IMAGE} AS judging_data
FROM ${TCSEXAM_BACKEND_BASE}

ENV TESTS_DIR=/tests \
    APP_DIR=/app \
    WORK_DIR=/work \
    JUDGE_CMD="bash /judge/entry.sh" \
    JUDGE_TIMEOUT=3300 \
    INSTANCES_PUBLIC_DIR=/tests-public/instances \
    PORT=8082

COPY assets/environments/solver/bpp-bpplib/judge/test.sh /tests/test.sh
COPY assets/environments/solver/bpp-bpplib/judge/entry.sh /judge/entry.sh
COPY assets/environments/solver/bpp-bpplib/judge/judge_worker.py /judge/judge_worker.py
COPY tasks/solver/online/bpp-bpplib/tests/checker.py /tests/checker.py
COPY tasks/solver/online/bpp-bpplib/tests/checker.py /tests-public/checker.py
COPY tasks/solver/online/bpp-bpplib/tests/reference.json /tests/reference.json
COPY tasks/solver/online/bpp-bpplib/tests/scoring.py /opt/bpp/scoring.py
COPY tasks/solver/online/bpp-bpplib/environment/app/public_reference.json /tests-public/reference.json
COPY --from=judging_data /payload/rootfs/ /

RUN cp -a /app/instances /tests-public/instances \
 && rm -rf /app \
 && mkdir -p /app /work \
 && chmod 755 /judge/entry.sh /judge/judge_worker.py /tests/test.sh

CMD ["python3", "/judge/judge_worker.py"]
