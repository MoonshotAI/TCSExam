ARG TCSEXAM_DEVELOPMENT_IMAGE
FROM ${TCSEXAM_DEVELOPMENT_IMAGE}
COPY --chown=0:0 . /tests/
RUN test -x /tests/test.sh \
    && cp -a /app /opt/tcsexam-trusted-app \
    && rm -rf /opt/tcsexam-trusted-app/.lake/build \
    && for repo in /app/.lake/packages/*; do \
       if [ -d "$repo/.git" ]; then git config --system --add safe.directory "$repo"; fi; done
