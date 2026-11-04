ARG TCSEXAM_PYTHON_IMAGE
ARG QBF_PUBLIC_DATA_IMAGE
# Copy only the fixed certificate tools; no source-image layers enter the final image.
ARG QBF_TOOLS_IMAGE
FROM ${QBF_TOOLS_IMAGE} AS certificate_tools
FROM ${QBF_PUBLIC_DATA_IMAGE} AS qbf_public_data
FROM ${TCSEXAM_PYTHON_IMAGE}
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=60 -o Acquire::http::Timeout=60 update \
 && apt-get -o Acquire::Retries=2 -o Acquire::https::Timeout=60 -o Acquire::http::Timeout=60 install -y --no-install-recommends g++ cmake make curl xz-utils zlib1g-dev bc procps psmisc file xxd bsdextrautils \
 && rm -rf /var/lib/apt/lists/*
COPY --from=certificate_tools /opt/qbf/qrp2rup /opt/qbf/qrp2rup
COPY --from=certificate_tools /opt/qbf/drat-trim /opt/qbf/drat-trim
COPY app/public_runner.py app/verify_qbf.py /opt/qbf/
COPY app/ /app/
COPY --from=qbf_public_data /payload/rootfs/opt/qbf-public100/ /opt/qbf-public100/
COPY --from=qbf_public_data /payload/rootfs/opt/licenses/qbf/QBF-DATA-NOTICE.txt /payload/rootfs/opt/licenses/qbf/QBF-ParaProofa-CC-BY-4.0.txt /payload/rootfs/opt/licenses/qbf/ParaProofa-root-MIT.txt /payload/rootfs/opt/licenses/qbf/QBF-BMC-Toronto-research.txt /opt/licenses/qbf/
RUN chmod 755 /opt/qbf/verify_qbf.py \
 && ln -s /opt/qbf/verify_qbf.py /usr/local/bin/qbf_verify \
 && bash /app/build.sh
COPY submit.sh /usr/local/bin/submit.sh
RUN chmod 755 /usr/local/bin/submit.sh
WORKDIR /app
