# ----------------------------
# Stage 1: Builder
# ----------------------------
FROM apache/spark:3.5.5-java17-python3 AS builder

USER root

# Set arguments
ARG dbt_version=1.9.0
ARG POSTGRES_JDBC_VERSION=42.7.2

# Create build directory
WORKDIR /build

# Copy requirements first for layer caching
COPY ./prefect/requirements.txt ./requirements.txt

# Install required packages
RUN apt-get update && \
    apt-get install -y git build-essential curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# Download JDBC driver
RUN curl -L -o /tmp/postgres.jar https://jdbc.postgresql.org/download/postgresql-${POSTGRES_JDBC_VERSION}.jar

# Copy application code
COPY ./prefect ./prefect
COPY ./dbt /dbt
COPY ./spark/jobs /spark/jobs

# ----------------------------
# Stage 2: Runtime
# ----------------------------
FROM apache/spark:3.5.5-java17-python3

USER root

# Set arguments again
ARG dbt_version=1.9.0
ARG POSTGRES_JDBC_VERSION=42.7.2
ARG GIT_COMMIT_SHA
ARG GIT_REPOSITORY_URL

# Set environment variables
ENV DD_GIT_COMMIT_SHA=$GIT_COMMIT_SHA
ENV DD_GIT_REPOSITORY_URL=$GIT_REPOSITORY_URL
ENV DBT_PROFILES_DIR=/opt/dbt
ENV POSTGRES_JDBC_VERSION=${POSTGRES_JDBC_VERSION}

# Create working directories
WORKDIR /app
RUN mkdir -p /opt/dbt /opt/spark/jobs /opt/spark/jars

# Copy installed packages and dependencies
COPY ./prefect/requirements.txt ./requirements.txt
RUN apt-get update && \
    apt-get install -y git build-essential curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code and JDBC driver
COPY --from=builder /tmp/postgres.jar /opt/spark/jars/postgresql.jar
COPY --from=builder /dbt /opt/dbt
COPY --from=builder /spark/jobs /opt/spark/jobs
COPY --from=builder /prefect /app/prefect

# Default command
CMD ["prefect", "worker", "start", "--pool", "default-agent-pool"]
