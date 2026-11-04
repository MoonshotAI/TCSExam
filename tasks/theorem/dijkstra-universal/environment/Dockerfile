# lean-odd-query-ldc-lb task environment: lean-base + task files (self-contained per Harbor convention)
ARG TCSEXAM_LEAN_BASE
FROM ${TCSEXAM_LEAN_BASE}

# task files (statements with sorry; agent edits these)
WORKDIR /app
COPY app/ /app/
RUN (lake build Task || echo "WARN: prebuild failed")

WORKDIR /app
