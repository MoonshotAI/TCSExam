ARG TCSEXAM_LEAN_BASE
FROM ${TCSEXAM_LEAN_BASE}
RUN rm -rf /app && mkdir -p /app
WORKDIR /app
COPY app/ /app/
RUN mkdir -p /logs/artifacts && chmod 777 /logs/artifacts \
    && lake build Task
WORKDIR /app
