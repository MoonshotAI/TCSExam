ARG TCSEXAM_PUBLIC_DATA_IMAGE
ARG TCSEXAM_TOOLS_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM ${TCSEXAM_TOOLS_IMAGE} AS tcsexam_tools
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Toolchain: JDK 21 (the shipped baseline solver is Java), g++ (the official
# validator is C++; agents may also write C/C++ solvers).
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && sed -i 's|deb.debian.org|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends openjdk-21-jdk-headless g++ curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Public-instance runner used by the agent-side convenience script (run /
# validate / recompute cost only — no reference values, no aggregation, no
# scoring formula). Kept OUTSIDE /app. The judging-side scoring module is
# NOT in this image.
COPY public_runner.py /opt/ctt/public_runner.py

# Official ITC 2007 Track 3 validator (validator.cc by the track organizers
# Schaerf & Di Gaspero, downloadable from the competition site). The SAME
# binary validates on the agent side and on the judge side. Agents are
# expected to use it to check their own timetables.
COPY app/validator.cc /opt/ctt/validator.cc
RUN g++ -O2 -o /opt/ctt/validator /opt/ctt/validator.cc

# Agent workspace: the vendored CPSolver ITC 2007 wrapper sources (LGPL-3,
# lgpl.txt included) + the bundled jars (cpsolver core 1.2, dom4j, log4j),
# the baseline configuration, the build script the judge will run, the 15
# public practice instances, verified best-known timetables for four of
# them, the public B/K reference, and the local runner script.
COPY app/cpsolver-src /app/cpsolver-src
COPY --from=tcsexam_tools /payload/rootfs/app/lib/ /app/lib/
COPY app/ctt.properties /app/ctt.properties
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/itc2007_table.md /app/itc2007_table.md
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
COPY app/solutions /app/solutions
COPY app/lgpl.txt /app/lgpl.txt

# Prebuild the baseline so /app/solver works out of the box (and to prove
# the vendored source compiles with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
