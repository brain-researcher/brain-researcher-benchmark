ARG SOURCE_IMAGE
FROM ${SOURCE_IMAGE} AS qualified_runtime
FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
COPY --from=qualified_runtime /usr /usr
COPY --from=qualified_runtime /etc/alternatives /etc/alternatives
COPY --from=qualified_runtime /usr /sandbox/usr
COPY capsule /sandbox/data
COPY public /public
COPY public /sandbox/public
COPY private /private
COPY grading.py sandbox.py verify.py test.sh /tests/
RUN mkdir -p /submission /sandbox/input /sandbox/tmp /sandbox/out /logs/verifier && \
    ln -s usr/lib /sandbox/lib && ln -s usr/lib64 /sandbox/lib64 && ln -s usr/bin /sandbox/bin && \
    chown 61616:61616 /sandbox/tmp /sandbox/out && chmod 700 /sandbox/tmp /sandbox/out && \
    chmod 700 /private /tests && chmod -R a-w /sandbox/usr /sandbox/data /sandbox/public && \
    chmod 755 /sandbox /sandbox/input && chmod +x /tests/test.sh
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /tests
