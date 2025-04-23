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

# Accept build arguments
ARG GIT_COMMIT_SHA
ARG GIT_REPOSITORY_URL

# Set as environment variables
ENV DD_GIT_COMMIT_SHA=$GIT_COMMIT_SHA
ENV DD_GIT_REPOSITORY_URL=$GIT_REPOSITORY_URL

# The default CMD is for the web application.
# Make sure start.sh is executable
RUN chmod +x /app/start.sh

# Start both servers
CMD ["/app/start.sh"]