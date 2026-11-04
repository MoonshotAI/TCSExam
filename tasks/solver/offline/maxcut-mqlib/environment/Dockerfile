# SPDX-License-Identifier: Apache-2.0
ARG TCSEXAM_OFFLINE_DEVELOPMENT_IMAGE
FROM ${TCSEXAM_OFFLINE_DEVELOPMENT_IMAGE}
COPY app/ /app/
COPY app/public_runner.py /opt/maxcut/public_runner.py
RUN rm -f /usr/local/bin/submit.sh \
 && apt-get update && apt-get install -y --no-install-recommends nodejs npm procps \
 && npm install -g --registry=https://registry.npmmirror.com @anthropic-ai/claude-code@2.1.257 \
 && claude --version && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENTRYPOINT []
CMD ["sleep", "infinity"]
