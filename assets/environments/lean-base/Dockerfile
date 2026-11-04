# Build the shared Lean environment from pinned public upstream sources.
# Preserve component notices and corresponding-source materials in the image.
FROM ubuntu:noble-20260610@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl git build-essential python3 python3-pip ripgrep jq \
    && rm -rf /var/lib/apt/lists/*
ENV ELAN_HOME=/opt/elan
ENV PATH="/opt/elan/bin:${PATH}"
RUN curl -fsSL https://github.com/leanprover/elan/releases/download/v4.2.3/elan-x86_64-unknown-linux-gnu.tar.gz -o /tmp/elan.tar.gz \
    && echo 'df0b2b3a439961ffcbb3985214365ffe40f49bc871df04dff268c7d8e21ca8b2  /tmp/elan.tar.gz' | sha256sum -c - \
    && tar -xzf /tmp/elan.tar.gz -C /tmp \
    && /tmp/elan-init -y --default-toolchain none \
    && rm /tmp/elan.tar.gz /tmp/elan-init
WORKDIR /opt/lean-lib/mathlib4
RUN git init \
    && git remote add origin https://github.com/leanprover-community/mathlib4.git \
    && git fetch --depth 1 origin 5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3 \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = '5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3' \
    && test "$(cat lean-toolchain)" = 'leanprover/lean4:v4.33.0-rc1' \
    && elan toolchain install leanprover/lean4:v4.33.0-rc1 \
    && elan default leanprover/lean4:v4.33.0-rc1 \
    && lake exe cache get \
    && lake build Mathlib \
    && find /opt/lean-lib/mathlib4/.lake/build -type f ! -perm -004 -exec chmod a+r {} +
WORKDIR /app
COPY NOTICE.md /usr/share/doc/tcsexam/README.md
COPY graphviz-epl/ /usr/share/doc/tcsexam/graphviz-epl/
COPY lean-components/ /usr/share/doc/tcsexam/lean-components/
COPY browser-components/ /usr/share/doc/tcsexam/browser-components/
COPY proofwidgets-npm/ /usr/share/doc/tcsexam/proofwidgets-npm/
RUN echo '92a19150f341eae09d1deedb4efbf9f3d2ce6a65f3b932d6b9e9a70f084b1ed3  /usr/share/doc/tcsexam/README.md' | sha256sum -c - \
    && cd /usr/share/doc/tcsexam/graphviz-epl \
    && sha256sum -c SHA256SUMS \
    && cd /usr/share/doc/tcsexam/lean-components \
    && sha256sum -c SHA256SUMS \
    && cd /usr/share/doc/tcsexam/browser-components \
    && sha256sum -c SHA256SUMS \
    && cd /usr/share/doc/tcsexam/proofwidgets-npm \
    && sha256sum -c SHA256SUMS
