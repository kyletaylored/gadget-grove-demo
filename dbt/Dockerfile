# Use Docker's built-in platform arguments
# TARGETPLATFORM is automatically set by Docker buildx
FROM python:3.13-slim

RUN apt-get update \
    && apt-get dist-upgrade -y \
    && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    libpq-dev \
    make \
    openssh-client \
    software-properties-common \
    && apt-get clean \
    && rm -rf \
    /var/lib/apt/lists/* \
    /tmp/* \
    /var/tmp/*

ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8

RUN python -m pip install --upgrade pip setuptools wheel --no-cache-dir

HEALTHCHECK CMD dbt --version || exit 1

WORKDIR /usr/app/dbt/
ENTRYPOINT ["dbt"]

# You can specify a specific version if needed
ARG dbt_version=1.9.0
RUN python -m pip install --no-cache-dir dbt-core==${dbt_version} dbt-postgres==${dbt_version}