FROM apache/spark:3.5.5-scala2.12-java17-ubuntu

# Switch to root to install system + Python tools
USER root

# Install Python 3, pip, and other tools
RUN apt-get update && \
    apt-get install -y python3 python3-pip git build-essential && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
ARG dbt_version=1.9.0
RUN pip install --no-cache-dir \
    prefect \
    ddtrace \
    pandas \
    pyspark \
    dbt-core==${dbt_version} \
    dbt-postgres==${dbt_version}

# Set working directory
WORKDIR /app

# Add PostgreSQL JDBC driver
ARG POSTGRES_JDBC_VERSION=42.7.2
# Set it as a runtime environment variable (optional but helps with debugging)
ENV POSTGRES_JDBC_VERSION=${POSTGRES_JDBC_VERSION}
ADD https://jdbc.postgresql.org/download/postgresql-${POSTGRES_JDBC_VERSION}.jar /opt/spark/jars/

# Copy your flow code and jobs
COPY ./prefect /app/prefect
COPY ./dbt /opt/dbt
COPY ./spark/jobs /opt/spark/jobs


# dbt needs this to locate your profile
ENV DBT_PROFILES_DIR=/opt/dbt

# Start the process agent
CMD ["prefect", "worker", "start", "--pool", "default-agent-pool"]
