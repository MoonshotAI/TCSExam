# sorting-network-size-lean-open environment: lean base + task files (self-contained per Harbor convention)
ARG TCSEXAM_LEAN_BASE
FROM ${TCSEXAM_LEAN_BASE}

# task files (fixed definition layer + claim stub with sorry; agent edits these)
WORKDIR /app
COPY app/ /app/
RUN mkdir -p /logs/artifacts && chmod 777 /logs/artifacts
COPY examples/ /app/examples/
RUN (lake build Task || echo "WARN: prebuild failed")

WORKDIR /app
