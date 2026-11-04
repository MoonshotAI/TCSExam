ARG TCSEXAM_PUBLIC_DATA_IMAGE
ARG TCSEXAM_TOOLS_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM ${TCSEXAM_TOOLS_IMAGE} AS tcsexam_tools
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

# Build toolchain for the agent's C++ solver.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Official PACE 2024 verifier (pip package pace2024-verifier 0.3.8, vendored
# wheel + the runtime deps its crossing counter actually needs: segment-tree
# [which itself needs numpy] and click for the CLI). Installed offline from
# /opt/ocm/pkg; source kept readable there. The CLI entry point lands on
# PATH as pace2024verifier; the local runner imports the same code.
COPY app/verifier /opt/ocm/pkg/
COPY --from=tcsexam_tools /payload/rootfs/opt/ocm/pkg/ /opt/ocm/pkg/
RUN pip install --no-index --find-links /opt/ocm/pkg --no-deps \
      pace2024-verifier segment-tree click numpy

# Local public-instance runner module (build + run + crossing-count logic),
# used by /app/run_public.py.
COPY app/public_runner.py /opt/ocm/public_runner.py

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, public instances, public B/K reference, and the local
# public-instances runner.
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/PROPERTIES.md /app/PROPERTIES.md
COPY app/testsets /app/testsets/
COPY --from=tcsexam_public_data /payload/rootfs/app/testsets/ /app/testsets/
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored source compiles with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
