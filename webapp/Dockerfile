FROM python:3.11-slim

# Define a non-root user and group
ARG NB_USER=celeryuser
ARG NB_UID=1000

# Create the user and group
RUN adduser --disabled-password \
    --gecos "" \
    --uid ${NB_UID} \
    ${NB_USER}

WORKDIR /app

# Install PostgreSQL client + curl + jq
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Add pip cache here for faster rebuilds
RUN --mount=type=cache,target=/root/.cache \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Change ownership of the application directory to the non-root user
RUN chown -R ${NB_USER}:${NB_USER} /app

# Switch to the non-root user
USER ${NB_USER}

# The default CMD is for the web application.
# This will be overridden in docker-compose for the Celery worker container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]