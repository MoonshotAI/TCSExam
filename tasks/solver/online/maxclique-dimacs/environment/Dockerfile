ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Build toolchain for the agent's C++ solver; taskset (util-linux) is used by
# the judge to pin parallel runs to cores.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ util-linux curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Local public-instance runner module (build + per-instance run + clique
# validity check), used by /app/run_public.py. The scoring module used by
# the judging chain lives judge-side only (tests/scoring.py) — no scoring
# code ships in this environment.
COPY app/public_runner.py /opt/maxclique/public_runner.py

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, the 56 public practice instances (the hidden judged
# set — 24 structure-preserving transforms of held-out benchmark instances
# — never enters this environment), the per-instance table, verified
# maximum cliques for the practice subset, the public B/K reference, and
# the local public-instances runner.
COPY app/solver.cpp /app/solver.cpp
COPY app/mcqd_anytime.h /app/mcqd_anytime.h
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/dimacs_table.md /app/dimacs_table.md
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
COPY app/solutions/ /app/solutions/

# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored source compiles with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

# Per-instance wall-clock contract of the judging chain (seconds): the same
# value the judge-side runner enforces; documented here so the local runner
# and solver self-limiting read the identical default.
ENV PER_INSTANCE_SECONDS=180

WORKDIR /app
