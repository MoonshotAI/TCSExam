# The 100 public instances (the odd-numbered half of the official PACE 2017
# heuristic set) ship in a prebuilt data image, kept out of the git repo by
# project rule; they are unpacked into /app/instances below.
ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS twpub
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

# Build toolchain for the agent's C++ solver + the official PACE td-validate
# (+ xz-utils to unpack the public instances).
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ make xz-utils curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Official validity checker (source kept readable at /opt/tw/td-validate.cpp,
# compiled binary on PATH as td-validate). Kept OUTSIDE /app so that the
# /app build never picks it up.
COPY app/td-validate.cpp /opt/tw/td-validate.cpp
COPY app/LICENSE-td-validate /opt/tw/LICENSE-td-validate
RUN g++ -O2 -std=c++14 -o /usr/local/bin/td-validate /opt/tw/td-validate.cpp

# Local public-instance runner module (make + per-instance run + td-validate
# call logic), used by /app/run_public.py.
COPY app/public_runner.py /opt/tw/public_runner.py

# Agent workspace: baseline solver (FlowCutter source + pool driver) +
# Makefile, public instances, public B/K reference, and the local
# public-instances runner.
COPY app/Makefile /app/Makefile
COPY app/driver.sh /app/driver.sh
COPY app/src/ /app/src/
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY --from=twpub /payload/rootfs/app/instances/ /app/instances/

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
