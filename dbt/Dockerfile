FROM python:3.13-slim

# System packages
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
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Environment
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8

# Python tools
RUN python -m pip install --upgrade pip setuptools wheel --no-cache-dir

# Install dbt
ARG dbt_version=1.9.0
RUN pip install --no-cache-dir \
    dbt-core==${dbt_version} \
    dbt-postgres==${dbt_version}

# Healthcheck
HEALTHCHECK CMD dbt --version || exit 1

WORKDIR /usr/app

# only for running dbt inside the container
ENTRYPOINT ["dbt"]

# Optional: default command if none is passed
# CMD ["dbt", "--help"]