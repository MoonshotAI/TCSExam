ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Build toolchain for the agent's C++ solver and for the official checker.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Local public-instance runner module (per-instance run logic), used by
# /app/run_public.py. Kept OUTSIDE /app.
COPY app/public_runner.py /opt/mr/public_runner.py

# Official ROADEF/EURO 2012 solution checker: source for the agent to
# inspect, plus a prebuilt binary for local validation. The judge compiles
# its own copy from /tests/checker-src at verify time.
COPY app/checker-src/ /app/checker-src/
RUN g++ -O2 -std=c++11 -o /opt/mr/checker \
        /app/checker-src/solution_checker.cc \
        /app/checker-src/solution_checker_run.cc

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, the public instance set (10 small + 10 large; the
# hidden judging instances are physically excluded), the official problem
# specification, the 2012 final standings table, the public B/K reference,
# and the local public-instances runner.
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY --from=tcsexam_public_data /payload/rootfs/app/problem_definition_v1_1.pdf /app/problem_definition_v1_1.pdf
COPY app/roadef2012_final_results.md /app/roadef2012_final_results.md
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
