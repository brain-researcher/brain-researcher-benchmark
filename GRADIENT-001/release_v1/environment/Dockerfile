ARG SOURCE_IMAGE
FROM ${SOURCE_IMAGE} AS qualified_runtime
FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
COPY --from=qualified_runtime /usr /usr
COPY --from=qualified_runtime /etc/alternatives /etc/alternatives
COPY --from=qualified_runtime /etc/ssl/certs /etc/ssl/certs
COPY capsule /data
COPY public /public
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
RUN mkdir -p /submission /app && chmod 755 /submission /app
WORKDIR /app
