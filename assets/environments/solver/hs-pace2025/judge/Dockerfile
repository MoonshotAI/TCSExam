# SPDX-License-Identifier: Apache-2.0
# Context: repository root plus generated plaintext/, manifest.json and files.sha256.
ARG TCSEXAM_HS_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_HS_PUBLIC_DATA_IMAGE} AS hsdata
ARG TCSEXAM_TEMURIN_IMAGE=eclipse-temurin:21-jdk
FROM ${TCSEXAM_TEMURIN_IMAGE}

RUN apt-get update \
 || (sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' \
       /etc/apt/sources.list.d/ubuntu.sources && apt-get update) \
 && apt-get install -y --no-install-recommends g++ python3 xz-utils openssl p7zip-full curl \
 && rm -rf /var/lib/apt/lists/*

COPY tasks/solver/online/hs-pace2025/environment/verifier-src/ /opt/hs2025/verifier-src/
RUN cd /opt/hs2025/verifier-src \
 && mkdir -p /opt/hs2025/classes \
 && javac -d /opt/hs2025/classes $(find . -name '*.java') \
 && jar cfe /opt/hs2025/hs_verifier.jar de.uni.bremen.hs.Main -C /opt/hs2025/classes . \
 && rm -rf /opt/hs2025/classes

COPY tasks/solver/online/hs-pace2025/tests/scoring.py /opt/hs2025/scoring.py
COPY plain/ /opt/hs100-private/
COPY manifest.json files.sha256 /opt/hs2025/
COPY tasks/solver/online/hs-pace2025/tests/checker.py /tests/checker.py
COPY tasks/solver/online/hs-pace2025/tests/reference.json /tests/reference.json
COPY assets/environments/solver/hs-pace2025/judge/test.sh /tests/test.sh
COPY assets/environments/solver/hs-pace2025/judge/judge_worker.py /judge/judge_worker.py

RUN test "$(find /opt/hs100-private -maxdepth 1 -type f -name '*.hgr' | wc -l)" -eq 100 \
 && test -z "$(find /opt/hs100-private /tests -type f \( -name '*.key' -o -name '*.enc' \) -print)" \
 && chmod -R a+rX /tests /judge /opt/hs100-private \
 && find /tests -name "*.sh" -exec chmod 755 {} + \
 && chmod 755 /judge/judge_worker.py \
 && mkdir -p /work /logs/verifier

COPY --from=hsdata /opt/hs-data/public100/ /public-instances/
RUN xz -d /public-instances/*.xz
COPY tasks/solver/online/hs-pace2025/environment/app/public_reference.json /public_reference.json
RUN mkdir -p /tests-public \
 && cp /tests/checker.py /tests-public/checker.py \
 && cp /public_reference.json /tests-public/reference.json \
 && printf '%s\n' \
      '#!/bin/bash' \
      'if [ "${INSTANCE_SET:-hidden}" = "public" ]; then' \
      '  mkdir -p /logs/verifier' \
      '  exec python3 /tests-public/checker.py' \
      'fi' \
      'exec bash "${TESTS_DIR:-/tests}/test.sh"' \
      > /judge/entry.sh \
 && chmod 755 /judge/entry.sh

ENV PORT=8082 \
    TESTS_DIR=/tests \
    APP_DIR=/app \
    WORK_DIR=/work \
    JUDGE_TIMEOUT=8400 \
    INSTANCES_PUBLIC_DIR=/public-instances \
    JUDGE_CMD="bash /judge/entry.sh"

CMD ["python3", "/judge/judge_worker.py"]
