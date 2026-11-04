# The instance data ships in a prebuilt data image — the 100 public .gr
# (xz-compressed, ~1.4 GB) plus the official test set are far too large for
# the git repo. The public layer is stored as plaintext xz inside the image
# (the hidden layer stays on the judge side, not in this image).
ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS dsdata
FROM eclipse-temurin:21-jdk@sha256:23cc5734ff46e776f51ce66eb9ee08444fd47caabec0a95b7eb6e94be2d3696d

# Build toolchain for the agent's C++ solver + python3 for the runner code;
# xz-utils to unpack the instances, p7zip for the test set's large/*.7z.
# The sed fallback keeps the build working on networks where
# archive.ubuntu.com is unreachable but mirrors.aliyun.com is.
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 || (sed -i 's|http://archive.ubuntu.com/ubuntu|http://archive.ubuntu.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|http://archive.ubuntu.com/ubuntu|g' \
       /etc/apt/sources.list.d/ubuntu.sources && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update) \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ python3 xz-utils p7zip-full curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Official PACE 2025 dominating-set verifier (Java, no runtime deps).
# Source kept readable at /opt/ds2025/verifier-src, compiled jar at
# /opt/ds2025/ds_verifier.jar. Upstream: github.com/MarioGrobler/ds_verifier.
COPY verifier-src/ /opt/ds2025/verifier-src/
RUN cd /opt/ds2025/verifier-src \
 && mkdir -p /opt/ds2025/classes \
 && javac -d /opt/ds2025/classes $(find . -name '*.java') \
 && jar cfe /opt/ds2025/ds_verifier.jar de.uni.bremen.ds.Main -C /opt/ds2025/classes . \
 && rm -rf /opt/ds2025/classes

# Local public-instance runner module (compile + run + verify logic), used
# by /app/run_public.py.
COPY app/public_runner.py /opt/ds2025/public_runner.py

# The 100 public instances (complete official public set) and the official
# small test set, both from the data image.
COPY --from=dsdata /payload/rootfs/app/instances/ /app/instances/
COPY --from=dsdata /payload/rootfs/app/test-instances/ /app/test-instances/

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
