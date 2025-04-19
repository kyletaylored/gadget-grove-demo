#!/bin/bash
set -euo pipefail

echo "Initializing GadgetGrove system..."

# 0. Print environment for verification
echo "ENV CHECK:"
echo "  POSTGRES_USER: $POSTGRES_USER"
echo "  POSTGRES_DB: $POSTGRES_DB"
echo "  POSTGRES_HOST: $POSTGRES_HOST"
echo "  POSTGRES_PORT: $POSTGRES_PORT"
echo "  RABBITMQ_QUEUE: $RABBITMQ_QUEUE"
echo "  PREFECT_API_URL: $PREFECT_API_URL"
echo ""

# 1. Create PostgreSQL schemas
echo "Creating PostgreSQL schemas in database '$POSTGRES_DB'..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$POSTGRES_PORT" <<EOF
CREATE SCHEMA IF NOT EXISTS raw_data;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;
EOF
echo "PostgreSQL schemas created."

# 2. Ensure RabbitMQ queue exists
echo "Declaring RabbitMQ queue '$RABBITMQ_QUEUE'..."
if ! command -v curl &> /dev/null; then
  echo "Installing curl and jq..."
  if command -v apk &> /dev/null; then
    apk add --no-cache curl jq
  else
    apt-get update && apt-get install -y curl jq
  fi
fi

curl -u guest:guest -H "content-type:application/json" \
  -X PUT -d '{"durable":true}' \
  http://rabbitmq:15672/api/queues/%2F/$RABBITMQ_QUEUE
echo "RabbitMQ queue ensured."

# 3. Set Prefect profile config to use Postgres
echo "Ensuring Prefect database '$PREFECT_DB' exists..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" -tc \
  "SELECT 1 FROM pg_database WHERE datname = '${PREFECT_DB}'" | grep -q 1 \
  || PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" -c \
  "CREATE DATABASE ${PREFECT_DB};"
echo "Prefect database ensured."

# 4. Prefect Deployment Setup
# Ensure work pool exists
echo "Ensuring Prefect work pool '$WORK_POOL' exists..."

# Set Prefect variable for use in prefect.yaml templating
echo "Registering Prefect variable work_pool=${WORK_POOL}"
prefect variable set work_pool "${WORK_POOL}"

# Create work pool if not already defined
if ! prefect work-pool inspect "$WORK_POOL" > /dev/null 2>&1; then
  prefect work-pool create "$WORK_POOL" --type process
  echo "Created work pool '$WORK_POOL'"
else
  echo "Work pool '$WORK_POOL' already exists"
fi

echo "Registering deployment via prefect.yaml..."
cd /app/prefect
prefect deploy --ci
cd -
echo "Prefect deployment registered."

echo "Initialization complete."
