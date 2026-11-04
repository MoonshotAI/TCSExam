# circles-in-square-n100-lean-open environment: lean base + task files (self-contained per Harbor convention)
ARG TCSEXAM_LEAN_BASE
FROM ${TCSEXAM_LEAN_BASE}

# task files (fixed definition layer + claim stub with sorry; agent edits these)
WORKDIR /app
COPY app/ /app/
RUN mkdir -p /logs/artifacts && chmod 777 /logs/artifacts
RUN (lake build Task || echo "WARN: prebuild failed")

# worked-example point sets shared with the solver sibling task circles-in-square-n100
COPY examples/ /app/examples/

WORKDIR /app
