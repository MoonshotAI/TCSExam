# Public practice set: 61 of the 87 official OR-Library SCP instances (the
# hidden judged set is a separate 30% holdout of structure-preserving
# transformed copies, judge-side only). Carried by a prebuilt data image —
# ~380 MB unfiltered including the four 40-80 MB railway instances, far too
# large for the git repo (sat-kissat data-image precedent) — filtered down
# to the public 61 by environment/public-instances.txt. SCP_DATA_IMAGE is an
# ARG so local self-checks can substitute a small fixture image.
ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS scp_source
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

# Build toolchain for the agent's C++ solver.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, the PUBLIC PRACTICE SET (48 official instances, filtered
# from the data image), verified covers for public practice instances, the
# public B/K reference, and a local convenience runner. NO scoring code ships
# here (form 2 cleanup, 2026-09-20: scoring moved judge-side, score_public.py
# replaced by the formula-free run_public.py), and NO library-wide table
# ships here either (2026-09-20 ruling: the environment only ever carries
# documents that match the shipped instance set exactly).
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY --from=scp_source /payload/rootfs/app/instances/ /app/instances/
COPY app/solutions/ /app/solutions/

# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored source compiles with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
