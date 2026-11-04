ARG TCSEXAM_PUBLIC_DATA_IMAGE
ARG TCSEXAM_TOOLS_IMAGE
ARG BASE=python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM ${TCSEXAM_TOOLS_IMAGE} AS tcsexam_tools
FROM $BASE

# Build toolchain for the agent's C++ solver.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ curl ca-certificates \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Public-instance runner used by the agent-side convenience script (run /
# validate / recompute penalty only — no reference values, no aggregation,
# no scoring formula), plus the official RobinX Validator 2.0 binary
# (static build) that run_public.py calls for local practice validation.
# Both kept OUTSIDE /app. The judging-side scoring module is NOT in this
# image; the judge side imports its own pristine copies from /tests, so the
# agent cannot influence judging by editing these.
COPY public_runner.py /opt/itc2021/public_runner.py
COPY --from=tcsexam_tools /payload/rootfs/opt/itc2021/RobinX /opt/itc2021/RobinX
# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, the 29 public practice instances, the per-instance
# known-results table, and the local runner script.
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/budgets.tsv /app/budgets.tsv
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/itc2021_table.md /app/itc2021_table.md
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
COPY app/instances.md5 /app/instances.md5

# Prebuild the baseline so /app/solver works out of the box (and to prove
# the vendored source compiles with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
