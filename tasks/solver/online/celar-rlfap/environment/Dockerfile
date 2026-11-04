ARG TCSEXAM_PUBLIC_DATA_IMAGE
FROM ${TCSEXAM_PUBLIC_DATA_IMAGE} AS tcsexam_public_data
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464

# Build toolchain for any native code the agent may write (apt via the
# aliyun mirror — deb.debian.org is unreachable from the build network).
RUN for tcsexam_apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do if [ -f "$tcsexam_apt_source" ]; then sed -i 's|http://|https://|g' "$tcsexam_apt_source"; fi; done \
 && sed -i 's|deb.debian.org|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends g++ curl ca-certificates \
 && apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# MiniZinc 2.10.0 bundle (includes minizinc CLI, OR-Tools CP-SAT
# (fzn-cp-sat), Chuffed, Gecode, CBC, HiGHS). Downloaded from the official
# GitHub release and pinned by sha256.
RUN curl -fsSL -o /tmp/minizinc-bundle.tgz \
      https://github.com/MiniZinc/MiniZincIDE/releases/download/2.10.0/MiniZincIDE-2.10.0-bundle-linux-x86_64.tgz \
 && echo "1781daef871a52bebc992b21049ed514cfcdf7cc652ce26df8c9fa82aca1a852  /tmp/minizinc-bundle.tgz" | sha256sum -c - \
 && tar xzf /tmp/minizinc-bundle.tgz -C /opt --no-same-owner \
 && mv /opt/MiniZincIDE-2.10.0-bundle-linux-x86_64 /opt/minizinc \
 && rm /tmp/minizinc-bundle.tgz
ENV PATH="/opt/minizinc/bin:$PATH"
# Per-instance wall-clock budget handed to local runs (the judging sandbox
# enforces the same 1200 s; run_public.py reads this variable).
ENV PER_INSTANCE_SECONDS=1200

# Public-instance runner used by the agent-side convenience script and by
# the shipped baseline (load_instance / check_solution only — no reference
# values, no aggregation, no scoring formula). Kept OUTSIDE /app. The
# judging-side scoring module is NOT in this image.
COPY public_runner.py /opt/celar/public_runner.py

# Agent workspace: the reference model, the baseline pipeline (solve.sh) and
# the build script the judge will run, the public practice instances, the
# per-instance table, the public B/K reference, and the local runner script.
COPY app/celar.mzn /app/celar.mzn
COPY app/solve.sh /app/solve.sh
COPY app/solve.py /app/solve.py
COPY app/construct.py /app/construct.py
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY app/instances_table.md /app/instances_table.md
COPY --from=tcsexam_public_data /payload/rootfs/app/instances/ /app/instances/
COPY app/solutions/ /app/solutions/

# Prebuild the baseline so /app/solver works out of the box (and to prove
# the shipped pipeline runs with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
