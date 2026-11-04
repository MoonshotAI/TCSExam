ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

# Build toolchain for the agent's C++ solver + the official PACE 2019
# vertex-cover checker. apt prefers the aliyun mirror (direct
# deb.debian.org egress is 502 through the local proxy) and falls back to
# the stock sources where the mirror is unreachable (evaluation runner builders).
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && cp /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list.d/debian.sources.bak \
 && sed -i 's|http://deb.debian.org|http://deb.debian.org|g' \
      /etc/apt/sources.list.d/debian.sources \
 && { apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
      || { cp /etc/apt/sources.list.d/debian.sources.bak /etc/apt/sources.list.d/debian.sources && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update; }; } \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ xz-utils curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Official validity checker (source kept readable at /opt/vc/, compiled
# binary on PATH as vc_validate). Kept OUTSIDE /app so that the
# "compile /app/*.cpp" build step never picks it up.
COPY app/vc_validate.cpp /opt/vc/vc_validate.cpp
COPY app/LICENSE-vc_validate /opt/vc/LICENSE-vc_validate
RUN g++ -std=c++11 -O3 -o /usr/local/bin/vc_validate \
      /opt/vc/vc_validate.cpp

# Local public-instance runner module (build + per-instance run + vc_validate
# call logic), used by /app/run_public.py.
COPY app/public_runner.py /opt/vc/public_runner.py

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, public instances, public K reference, and the local
# public-instances runner.
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
RUN for f in /app/instances/*.xz; do \
      xz -dc "$f" > "${f%.xz}.gr" && rm "$f"; \
    done

# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored source compiles with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
