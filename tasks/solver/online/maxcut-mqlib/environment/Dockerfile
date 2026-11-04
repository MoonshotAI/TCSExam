ARG TCSEXAM_PUBLIC_DATA_IMAGE
# The 105 public practice instances ship decompressed in /app/instances,
# with their 105 official zip files in the public data image. The full
# MQLib instance library and official-name files for the 45 hidden
# transformed judging instances are excluded from this environment.
# The verifier judges the hidden set once after the run ends.
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Build toolchain for the agent's C++ solver (g++/make/binutils for the
# vendored MQLib) plus xz-utils for the bundled instances and unzip for the
# library zips under /opt/mqlib-instances.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ make binutils xz-utils unzip curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Cut validator/evaluator (source kept readable at /opt/maxcut/, compiled
# binary on PATH as mc_check). Kept OUTSIDE /app so the "compile /app/*.cpp"
# build step never picks up its main(). Prints "OK <cut weight>" on stdout
# and exits 0 iff the solution is a well-formed 0/1 assignment; the weight
# is recomputed by summing crossing edges.
COPY mc_check.cpp /opt/maxcut/mc_check.cpp
RUN g++ -O3 -std=c++17 -o /usr/local/bin/mc_check /opt/maxcut/mc_check.cpp

# Local public-instance runner module (build + per-instance run + mc_check
# validation), used by /app/run_public.py. The scoring module used by the
# judging chain lives judge-side only (tests/scoring.py) — no scoring code
# ships in this environment.
COPY app/public_runner.py /opt/maxcut/public_runner.py

# Agent workspace: the vendored MQLib library (MIT, 37 literature
# heuristics, its data/ tables trimmed to the 105-instance caliber, and the
# paper), the baseline solver main as the starting point, the build script
# the judge will run, the 105 public practice instances, their B/K
# reference, and the local public-instances runner.
COPY app/mqlib /app/mqlib/
COPY --from=tcsexam_public_data /payload/rootfs/app/mqlib/ /app/mqlib/
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
RUN xz -d /app/instances/*.xz

# The 105 public practice instances' official zip files (byte-identical to
# the corresponding entries of the official public S3 bucket) under
# /opt/mqlib-instances — unpack on demand, e.g.
# `unzip -p /opt/mqlib-instances/G55.zip > /tmp/G55.txt` (or python zipfile).
COPY --from=tcsexam_public_data /payload/rootfs/opt/mqlib-instances/ /opt/mqlib-instances/

# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored library compiles with this toolchain; also warms the incremental
# make cache so the agent's rebuilds are fast).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

# Per-instance wall-clock contract of the judging chain (seconds): the same
# value the judge-side runner enforces; documented here so the local runner
# and solver self-limiting read the identical default.
ENV PER_INSTANCE_SECONDS=600

WORKDIR /app
