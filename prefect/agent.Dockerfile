# ----------------------------
# Stage 1: Builder
# ----------------------------
FROM bitnami/spark:3.5.5 AS builder

USER root

ARG dbt_version=1.9.0
ARG POSTGRES_JDBC_VERSION=42.7.2

WORKDIR /build

COPY ./prefect/requirements.txt ./requirements.txt

RUN apt-get update && \
    apt-get install -y git build-essential curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

RUN curl -L -o /tmp/postgresql.jar https://jdbc.postgresql.org/download/postgresql-${POSTGRES_JDBC_VERSION}.jar

COPY ./prefect ./prefect
COPY ./dbt /dbt
COPY ./spark/jobs /spark/jobs

# ----------------------------
# Stage 2: Runtime
# ----------------------------
FROM bitnami/spark:3.5.5

USER root

ARG GIT_COMMIT_SHA
ARG GIT_REPOSITORY_URL

ENV DD_GIT_COMMIT_SHA=$GIT_COMMIT_SHA
ENV DD_GIT_REPOSITORY_URL=$GIT_REPOSITORY_URL
ENV DBT_PROFILES_DIR=/opt/dbt

WORKDIR /app
RUN mkdir -p /opt/dbt /opt/spark/jobs /opt/spark/jars

COPY ./prefect/requirements.txt ./requirements.txt
RUN apt-get update && \
    apt-get install -y git build-essential curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

COPY --from=builder /tmp/postgresql.jar /opt/bitnami/spark/jars/postgresql.jar
COPY --from=builder /dbt /opt/dbt
COPY --from=builder /spark/jobs /opt/spark/jobs
COPY --from=builder /build/prefect /app/prefect

CMD ["ddtrace-run", "prefect", "worker", "start", "--pool", "default-agent-pool"]
