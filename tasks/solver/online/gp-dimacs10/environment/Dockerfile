ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464 AS kahip-build

ARG http_proxy
ARG https_proxy

# Build toolchain for KaHIP (debian bookworm; aliyun mirror through proxy).
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && sed -i 's|deb.debian.org|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ cmake make git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# KaHIP v3.25, MIT license (https://github.com/KaHIP/KaHIP), pinned commit.
RUN git clone --depth 1 --branch v3.25 https://github.com/KaHIP/KaHIP /opt/kahip-src \
 && test "$(git -C /opt/kahip-src rev-parse HEAD)" = "2e86d3da2065bcf6ddbf6fb84d2b52f33db1061f"
# No MPI in the agent image (kaffpaE/ParHIP disabled); -march=native OFF so
# the binaries run on any judge host.
RUN cmake -S /opt/kahip-src -B /opt/kahip-build \
      -DCMAKE_BUILD_TYPE=Release -DNONATIVEOPTIMIZATIONS=ON -DNOMPI=ON \
 && cmake --build /opt/kahip-build -j4 \
      --target kahip_static kaffpa evaluator graphchecker

FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

ARG http_proxy
ARG https_proxy

# g++ for the agent's solver, bzip2 for the packaged instances.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && sed -i 's|deb.debian.org|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ bzip2 curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Local public-instance runner module (build + per-instance pool run +
# partition validity check), used by /app/run_public.py. The scoring module
# used by the judging chain lives judge-side only (tests/scoring.py) — no
# scoring code ships in this environment.
COPY app/public_runner.py /opt/gp/public_runner.py

# Vendored KaHIP library (static) + C interface header for the agent's
# solver, and the KaHIP command-line tools for local experiments.
COPY --from=kahip-build /opt/kahip-build/libkahip_static.a /app/kahip/lib/libkahip_static.a
COPY --from=kahip-build /opt/kahip-src/interface/kaHIP_interface.h /app/kahip/include/kaHIP_interface.h
COPY --from=kahip-build /opt/kahip-build/kaffpa /opt/gp/bin/kaffpa
COPY --from=kahip-build /opt/kahip-build/evaluator /opt/gp/bin/evaluator
COPY --from=kahip-build /opt/kahip-build/graphchecker /opt/gp/bin/graphchecker
ENV PATH="/opt/gp/bin:${PATH}"

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, the 30 public practice instances plus 3 practice-only
# sample graphs (the hidden judged set — 13 structure-preserving transforms
# of held-out benchmark/generated instances — never enters this
# environment), the public B/K reference, and the local public-instances
# runner.
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY --from=tcsexam_public_data /payload/rootfs/app/instances-packed/ /app/instances-packed/
RUN mkdir -p /app/instances \
 && cd /app/instances-packed \
 && for f in *.graph.bz2; do bunzip2 -kc "$f" > "/app/instances/$(basename "$f" .bz2)"; done \
 && cd / && rm -rf /app/instances-packed

# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored toolchain links with this compiler).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

# Per-instance reference seconds of the judging chain's shared time pool
# (total pool = this value x instance count): the same value the judge-side
# runner uses; documented here so the local runner reads the identical
# default.
ENV PER_INSTANCE_SECONDS=60

WORKDIR /app
