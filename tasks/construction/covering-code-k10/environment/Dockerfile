# covering-code-k10-lean-open environment: lean-base + task files (self-contained per Harbor convention)
ARG TCSEXAM_LEAN_BASE
FROM ${TCSEXAM_LEAN_BASE}

# task files (fixed definition layer only; agent adds the theorem)
WORKDIR /app
COPY app/ /app/
RUN mkdir -p /logs/artifacts && chmod 777 /logs/artifacts
RUN (lake build Task || echo "WARN: prebuild failed")

WORKDIR /app
