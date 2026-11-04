ARG TCSEXAM_PUBLIC_DATA_IMAGE
ARG TCSEXAM_TOOLS_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM ${TCSEXAM_TOOLS_IMAGE} AS tcsexam_tools
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

# Build toolchain for the agent's C++ solver + the official PACE 2022 verifier.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ xz-utils curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# The locally prepared official checker retains its source at
# /opt/dfvs/verifier/ and installs fvs_verify on PATH.
COPY --from=tcsexam_tools /payload/rootfs/ /

# Shared scoring module used by both the public self-scoring script and the
# hidden judge (same verifier, same formula).
COPY app/scoring.py /opt/dfvs/scoring.py

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, public instances, public B/K reference, and the local
# scoring script.
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/score_public.py /app/score_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/examples/ /app/examples/
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
RUN xz -d /app/instances/*.xz

# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored source compiles with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
