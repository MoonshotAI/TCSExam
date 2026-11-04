ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Build toolchain for the agent's C++ solver.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && sed -i 's|deb.debian.org|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Public-instance runner used by the agent-side convenience script (run /
# validate / re-simulate only — no reference values, no aggregation, no
# scoring formula). Kept OUTSIDE /app. The judging-side scoring module is
# NOT in this image.
COPY public_runner.py /opt/ahc058/public_runner.py

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, the 105 public practice instances (100 official test
# cases plus 5 freshly generated ones), the official tester package source
# (generator + scorer documentation), the public B/K reference, and the
# local runner script.
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
COPY app/tools/ /app/tools/

# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored source compiles with this toolchain). /app stays agent-writable.
RUN bash /app/build.sh && chmod -R a+w /app

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
