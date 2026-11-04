ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Build toolchain for the agent's own C++ solver (apt via the aliyun mirror —
# deb.debian.org is unreachable from the build network). boost is available
# for agent-written solvers.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && sed -i 's|deb.debian.org|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ libboost-program-options-dev curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Local public-instance runner module (validity check + dual-tier run
# logic), used by /app/run_public.py. Kept OUTSIDE /app.
COPY app/public_runner.py /opt/glasscut/public_runner.py

# Agent workspace: the naive baseline solver (a simple constructive
# shelf-packing heuristic), the build script the judge will run, the public
# practice instances (sets A and B; the hidden judging instances are
# physically excluded), the per-instance table, verified best-known
# solutions for the practice subset, the public B/K reference, and the
# local public-instances runner.
COPY app/naive_shelf.py /app/naive_shelf.py
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/instances_table.md /app/instances_table.md
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
COPY app/solutions/ /app/solutions/

# Prebuild the baseline so /app/solver works out of the box (and to prove the
# build script works with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
