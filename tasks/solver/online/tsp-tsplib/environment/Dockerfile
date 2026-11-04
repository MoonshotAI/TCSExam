ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

# Build toolchain for the agent's C++ solver + the tsp_check tour validator.
# Package downloads use the upstream Debian mirrors over HTTPS.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 || (sed -i 's|deb.debian.org|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
     && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update) \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ make curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Tour validator (source kept readable at /opt/tsp/src, compiled binary on
# PATH as tsp_check). Kept OUTSIDE /app so that the /app build never picks
# it up; the judge-side validator is always the pristine build.
COPY app/src/ /opt/tsp/src/
RUN g++ -O2 -std=c++14 -o /usr/local/bin/tsp_check /opt/tsp/src/tsp_check.cpp

# Local public-instance runner module (build + per-instance run + tour
# validation), used by /app/run_public.py. The scoring module used by the
# judging chain lives judge-side only (tests/scoring.py) — no scoring code
# ships in this environment.
COPY app/public_runner.py /opt/tsp/public_runner.py

# Agent workspace: baseline solver (C++ source + driver) + Makefile, the 78
# public practice instances (the hidden judged set — 33 structure-preserving
# transforms of held-out library instances — never enters this environment),
# the official documentation (tsp95.pdf), the verified optimal-values table,
# the public B/K reference, and the local public-instances runner.
COPY app/Makefile /app/Makefile
COPY app/driver.sh /app/driver.sh
COPY app/src/ /app/src/
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/tsplib_known_optima.txt /app/tsplib_known_optima.txt
COPY --from=tcsexam_public_data /payload/rootfs/app/tsp95.pdf /app/tsp95.pdf
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

# Per-instance wall-clock contract of the judging chain (seconds): the same
# value the judge-side runner hands to the solver as LIMIT_SECONDS;
# documented here so the local runner and solver self-limiting read the
# identical default.
ENV PER_INSTANCE_BUDGET=600

WORKDIR /app
