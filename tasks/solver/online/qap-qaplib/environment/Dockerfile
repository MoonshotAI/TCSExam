ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Build toolchain for the agent's C++ solver.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, the PUBLIC PRACTICE SET (95 official instances from the
# library's public collection — the hidden judged set is a separate 30%
# holdout of structure-preserving transformed copies, judge-side only), the
# per-instance table (registered values / optimality status / lower bounds),
# the public B/K reference for those 95 instances, and a local convenience
# runner. NO registered solution permutations ship here (they are public on
# the library's site, and the hidden transformed copies make them useless
# anyway), and NO scoring code ships here either (form 2 cleanup, 2026-09-20:
# scoring moved judge-side, score_public.py replaced by the formula-free
# run_public.py).
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
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
