# ---------- Stage 1: Builder ----------
FROM python:3.11-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    jq \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /install

# Install Python dependencies into a temp dir
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install/deps --no-cache-dir -r requirements.txt

# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim-bookworm

# Define a non-root user
ARG NB_USER=celeryuser
ARG NB_UID=1000
RUN adduser --disabled-password --gecos "" --uid ${NB_UID} ${NB_USER}

WORKDIR /app

# Install runtime system packages only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy app source code
COPY --chown=${NB_USER}:${NB_USER} . .

# Copy only installed Python packages
COPY --from=builder /install/deps /usr/local

# Make sure start.sh is executable
RUN chmod +x /app/start.sh

# Set environment variables from args
ARG GIT_COMMIT_SHA
ARG GIT_REPOSITORY_URL
ENV DD_GIT_COMMIT_SHA=$GIT_COMMIT_SHA
ENV DD_GIT_REPOSITORY_URL=$GIT_REPOSITORY_URL

# Use non-root user
USER ${NB_USER}

CMD ["/app/start.sh"]
