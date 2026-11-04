# The instance library ships in a prebuilt data image (the 283-instance
# library is kept out of the git repo by project rule). Form 2 (2026-09-20):
# the environment carries the PUBLIC PRACTICE SET — 198 of the 283 instances
# (filtered from the data image by environment/public-instances.txt); the
# hidden judged set is a separate 30% holdout of structure-preserving
# transformed copies, judge-side only. The data image itself is unchanged.
ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS jssp_source
FROM python:3.11-slim@sha256:b7a9e5f6a93d6d4a31f129bbd4bdee69efccb6ded0fb230d78aafaf37af98377 AS tcsexam_certificates
FROM ubuntu:22.04@sha256:0a9887931b0e38af2e3487ed39e29436b0535c4f3f52e57745baaf79d1898956
COPY --from=tcsexam_certificates /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Preserve the original toolchain packages; bootstrap HTTPS trust from a clean base.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends \
      g++ make python3 python3-pip xz-utils openssl util-linux curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# OR-Tools CP-SAT, pinned to the exact JSPLib reference-engine version.
RUN pip3 install --no-cache-dir -i https://pypi.org/simple \
      ortools==9.15.6755

# jssp_check: the clean-room validity checker + makespan evaluator (source
# kept readable at /opt/jssp/, binary on PATH). Prints "OK <makespan>" iff
# the schedule is feasible; the same binary validates on both sides.
COPY app/jssp_check.cpp /opt/jssp/jssp_check.cpp
RUN g++ -O2 -std=c++17 -o /usr/local/bin/jssp_check /opt/jssp/jssp_check.cpp

# The PUBLIC PRACTICE SET (198 instances) for the agent, filtered from the
# 283-instance library in the data image down to the public hold-in list.
COPY --from=jssp_source /payload/rootfs/app/instances/ /app/instances/

# Agent workspace: baseline solver + a tabu-search reference implementation,
# the build script the judge will run, the stock CP-SAT model (a reference
# solver level documented in the public reference), public B/L/K reference,
# and a local convenience runner. NO scoring code ships here (form 2 cleanup,
# 2026-09-20: scoring moved judge-side, score_public.py replaced by the
# formula-free run_public.py). The tabu search ships in a subdirectory (so
# the "compile /app/*.cpp" build never picks up its main) and is also
# prebuilt on PATH.
COPY app/solver.cpp /app/solver.cpp
COPY app/tabu/ /app/tabu/
RUN g++ -O2 -std=c++17 -o /usr/local/bin/tabu /app/tabu/tabu.cpp
COPY app/build.sh /app/build.sh
COPY app/cpsat_example.py /app/cpsat_example.py
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/jsplib/ /app/jsplib/

# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored sources compile with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
