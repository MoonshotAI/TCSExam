ARG TCSEXAM_PUBLIC_DATA_IMAGE
ARG TCSEXAM_TOOLS_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM ${TCSEXAM_TOOLS_IMAGE} AS tcsexam_tools
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Build toolchain for ABC (C/C++ + make) and xz to unpack the vendored source.
# apt sources point at the internal-reachable mirror (proxy 502s the default
# debian.org endpoints on the build service).
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && sed -i 's|deb.debian.org|deb.debian.org|g; s|security.debian.org|deb.debian.org|g' \
        /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends gcc g++ make xz-utils curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Local public-instance runner module + AIGER/truth-table library: pristine
# copies for /app/run_public.py. The judge side uses its own copies under
# /tests (never the agent-writable /app ones).
COPY app/public_runner.py /opt/ls/public_runner.py
COPY app/aiglib.py /opt/ls/aiglib.py

# Agent workspace: vendored ABC source (berkeley-abc, pinned commit, BSD
# style license), the build script the judge will run, the AIGER/truth-table
# library for the agent's own tooling, the public practice set (100 instances;
# the hidden judging instances are physically excluded), the public B/K
# reference, and the local public-instances runner.
COPY --from=tcsexam_tools /payload/rootfs/app/abc-src.tar.xz /app/abc-src.tar.xz
COPY app/build.sh /app/build.sh
COPY app/aiglib.py /app/aiglib.py
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
# Unpack + prebuild the baseline so /app/solver works out of the box (and to
# prove the vendored source compiles with this toolchain).
RUN bash /app/build.sh

# The judging container runs as a non-root user: the agent (and the judge's
# rebuild via /app/build.sh) must be able to write /app regardless of uid.
RUN chmod -R a+rwX /app

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

# Scoring-pool coefficient: 40 s per instance (matching the scoring image; run_public.py passes it through
# public_runner.py reads PER_INSTANCE_SECONDS; the full-set restoration batch changed 180s to 40s).
ENV PER_INSTANCE_SECONDS=40

WORKDIR /app
