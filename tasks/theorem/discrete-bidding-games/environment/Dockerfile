# lean-discrete-bidding-games task environment: lean-base + task files (self-contained per Harbor convention)
ARG TCSEXAM_LEAN_BASE
FROM ${TCSEXAM_LEAN_BASE}

# Cached compiler artifacts must be readable by a non-root verifier.
RUN find /opt/lean-lib/mathlib4/.lake/build -type f ! -perm -004 -exec chmod a+r {} +

# task files (statements with sorry; agent edits these)
WORKDIR /app
COPY app/ /app/
RUN lake build Task \
    && find /opt/lean-lib/mathlib4/.lake/build -type f ! -perm -004 -exec chmod a+r {} +

WORKDIR /app
