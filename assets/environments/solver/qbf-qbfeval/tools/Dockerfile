# SPDX-License-Identifier: Apache-2.0
FROM python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get update && apt-get install -y --no-install-recommends gcc g++ make cmake zlib1g-dev curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY apply_qrp2rup_fix.py /tmp/apply_qrp2rup_fix.py
ARG QRP2RUP_COMMIT=0b7b9569bd19fdb946e0eb48ef13431635baeced
ARG QRP2RUP_SHA256=9679238a4fac783141b4a791f6dc39cd265d5fad94661268972b717199c8cbac
RUN mkdir -p /opt/qbf \
 && curl -fsSL "https://codeload.github.com/peitl/qrp2rup/tar.gz/$QRP2RUP_COMMIT" \
      -o /tmp/qrp2rup.tar.gz \
 && echo "$QRP2RUP_SHA256  /tmp/qrp2rup.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/qrp2rup.tar.gz -C /tmp \
 && cd "/tmp/qrp2rup-$QRP2RUP_COMMIT" \
 && python3 /tmp/apply_qrp2rup_fix.py src/proof_translator.cc \
 && cmake -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build -j4 \
 && cp qrp2rup /opt/qbf/qrp2rup \
 && rm -rf /tmp/qrp2rup.tar.gz "/tmp/qrp2rup-$QRP2RUP_COMMIT"

# drat-trim (Marijn Heule, SAT competition proof checker), pinned commit,
# checksum-verified. Stage 2 of the certificate check: verifies the DRUP
# proof that the extracted strategy wins on the instance's matrix.
ARG DRAT_TRIM_COMMIT=2e3b2dc0ecf938addbd779d42877b6ed69d9a985
ARG DRAT_TRIM_SHA256=a75e5a2072fa5a5493ee8504067661c6b452d45a32f889ac5b2c9470c227b58c
RUN curl -fsSL "https://codeload.github.com/marijnheule/drat-trim/tar.gz/$DRAT_TRIM_COMMIT" \
      -o /tmp/drat-trim.tar.gz \
 && echo "$DRAT_TRIM_SHA256  /tmp/drat-trim.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/drat-trim.tar.gz -C /tmp \
 && gcc "/tmp/drat-trim-$DRAT_TRIM_COMMIT/drat-trim.c" -std=gnu99 -O2 \
      -o /opt/qbf/drat-trim \
 && rm -rf /tmp/drat-trim.tar.gz "/tmp/drat-trim-$DRAT_TRIM_COMMIT"

