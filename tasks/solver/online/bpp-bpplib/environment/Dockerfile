ARG TCSEXAM_PYTHON_IMAGE
ARG BPPLIB_DATA_IMAGE
FROM ${BPPLIB_DATA_IMAGE} AS bpplib_data
FROM ${TCSEXAM_PYTHON_IMAGE}

# Build toolchain for the agent's C++ solver.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=60 -o Acquire::http::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=60 -o Acquire::http::Timeout=60 install -y --no-install-recommends g++ curl \
 && apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=60 -o Acquire::http::Timeout=60 install -y --no-install-recommends bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*

# Agent workspace: baseline solver as the starting point, the build script
# the judge will run, the PUBLIC PRACTICE SET (90 instances at
# /app/instances/), the background library (6,216 additional instances at
# /app/library/, overlapping neither the practice set nor the hidden judged
# set — the hidden set is a separate 30% holdout of structure-preserving
# transformed copies, judge-side only), the per-instance table (registered
# bounds and baseline value), verified optimal packings for a few public
# practice instances, the public B/K reference, and a local convenience
# runner. NO scoring code ships here (form 2 cleanup, 2026-09-20: scoring
# moved judge-side, score_public.py replaced by the formula-free
# run_public.py).
COPY app/solver.cpp /app/solver.cpp
COPY app/build.sh /app/build.sh
COPY app/run_public.py /app/run_public.py
COPY app/public_reference.json /app/public_reference.json
COPY --from=bpplib_data /payload/rootfs/app/ /app/





# Prebuild the baseline so /app/solver works out of the box (and to prove the
# vendored source compiles with this toolchain).
RUN bash /app/build.sh

# The public self-test client: packs /app and posts it to the judging
# service's public channel, then prints per-instance detail (see
# instruction.md). On PATH.
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh

WORKDIR /app
