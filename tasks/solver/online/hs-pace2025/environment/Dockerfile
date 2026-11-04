# The fixed input image supplies the official public and small test sets.
# Only those selected files are copied into the clean development stage.
ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS hsdata
FROM eclipse-temurin:21-jdk@sha256:23cc5734ff46e776f51ce66eb9ee08444fd47caabec0a95b7eb6e94be2d3696d

# Build toolchain for the agent's C++ solver + python3 for the runner code;
# xz-utils for the public-instance archives;
# p7zip for the test set's large/*.7z.
# Package downloads use HTTPS with bounded retries and timeouts.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 || (sed -i 's|http://archive.ubuntu.com/ubuntu|http://archive.ubuntu.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|http://archive.ubuntu.com/ubuntu|g' \
       /etc/apt/sources.list.d/ubuntu.sources && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update) \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ python3 xz-utils openssl p7zip-full curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Official PACE 2025 hitting-set verifier (Java, no runtime deps).
# Source kept readable at /opt/hs2025/verifier-src, compiled jar at
# /opt/hs2025/hs_verifier.jar. Upstream: github.com/MarioGrobler/hs_verifier.
COPY verifier-src/ /opt/hs2025/verifier-src/
RUN cd /opt/hs2025/verifier-src \
 && mkdir -p /opt/hs2025/classes \
 && javac -d /opt/hs2025/classes $(find . -name '*.java') \
 && jar cfe /opt/hs2025/hs_verifier.jar de.uni.bremen.hs.Main -C /opt/hs2025/classes . \
 && rm -rf /opt/hs2025/classes

# Local public-instance runner module (compile + run + verify logic), used
# by /app/run_public.py.
COPY app/public_runner.py /opt/hs2025/public_runner.py

# Only the official public and small test sets enter the development image.
COPY --from=hsdata /payload/rootfs/app/instances/ /app/instances/
COPY --from=hsdata /payload/rootfs/app/test-instances/ /app/test-instances/

# Agent workspace: baseline solver as the starting point, public instances,
# public B/K reference, and the local public-instances runner.
COPY app/solver.cpp /app/solver.cpp
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
