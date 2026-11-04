ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Build-time network goes through the local proxy (the build network cannot
# reach github.com directly); --build-arg http_proxy=... is expected.
ARG http_proxy
ARG https_proxy
ARG CVC5_URL=https://github.com/cvc5/cvc5/releases/download/cvc5-1.3.4/cvc5-Linux-x86_64-static.zip
ARG CVC5_ZIP_SHA256=dcdbfada0ce493ee98259c0816e0daafc561c223aadb3af298c2968e73ea39c6
ARG CVC5_BIN_SHA256=7562a8b0b835e3eaad5f1a7b4616cd762350cf567b6be03d7e8ee24fa5ced5ee

# Toolchain: g++ for agents who want to compile their own synthesizer,
# curl/unzip for the cvc5 download. apt via the aliyun mirror
# (deb.debian.org is unreachable from the build network).
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && sed -i 's|deb.debian.org|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ curl unzip ca-certificates \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# cvc5 1.3.4 official static binary (modified BSD license; the non-GPL
# static build), sha256-pinned at both zip and binary level. One copy lives
# in /app for the agent's solver to drive; a pristine copy lives in
# /opt/sygus for the judge-side machine check (the judge never trusts the
# agent's build or a tampered engine — tests/checker.py verifies hashes).
RUN curl -fsSL -o /tmp/cvc5.zip "$CVC5_URL" \
 && echo "$CVC5_ZIP_SHA256  /tmp/cvc5.zip" | sha256sum -c - \
 && unzip -q /tmp/cvc5.zip -d /tmp \
 && install -m 0755 /tmp/cvc5-Linux-x86_64-static/bin/cvc5 /usr/local/lib/cvc5 \
 && echo "$CVC5_BIN_SHA256  /usr/local/lib/cvc5" | sha256sum -c - \
 && mkdir -p /opt/sygus \
 && cp /usr/local/lib/cvc5 /opt/sygus/cvc5 \
 && cp /tmp/cvc5-Linux-x86_64-static/COPYING /opt/sygus/cvc5-COPYING \
 && rm -rf /tmp/cvc5.zip /tmp/cvc5-Linux-x86_64-static

# Machine checker + local public-instance runner module. Kept OUTSIDE /app.
COPY app/sygus_check.py /opt/sygus/sygus_check.py
COPY app/public_runner.py /opt/sygus/public_runner.py

# Agent-facing single-solution check tool on PATH (uses the pristine
# engine read-only): `sygus_check BENCHMARK.sl SOLUTION_FILE`.
RUN printf '#!/bin/bash\nexec python3 /opt/sygus/sygus_check.py "$@"\n' \
      > /usr/local/bin/sygus_check \
 && chmod +x /usr/local/bin/sygus_check

# Agent workspace: the cvc5 binary the baseline drives, the baseline
# wrapper + build script (the judge runs exactly /app/build.sh), the
# public practice instances (the hidden judging instances are physically
# excluded), the per-instance table, the public S_B/S_K reference, and the
# local public-instances runner.
RUN install -D -m 0755 /usr/local/lib/cvc5 /app/cvc5
COPY app/build.sh /app/build.sh
COPY app/naive_sygus.py /app/naive_sygus.py
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/instances_table.md /app/instances_table.md
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
# "Build" the baseline so /app/solver works out of the box.
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
