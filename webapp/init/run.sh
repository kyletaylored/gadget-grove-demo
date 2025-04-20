#!/bin/bash
set -euo pipefail

echo "Initializing GadgetGrove system..."

# 1. Create PostgreSQL schemas
echo "Creating PostgreSQL schemas in database '$POSTGRES_DB'..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$POSTGRES_PORT" <<EOF
CREATE SCHEMA IF NOT EXISTS raw_data;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Create tables for raw data
CREATE TABLE IF NOT EXISTS raw_data.page_views (
  id SERIAL PRIMARY KEY,
  type VARCHAR(255),
  timestamp TIMESTAMP,
  server_timestamp TIMESTAMP,
  session_id VARCHAR(255),
  user_id VARCHAR(255),
  client_ip VARCHAR(50),
  user_agent TEXT,
  url TEXT,
  path TEXT,
  properties JSONB,
  queue_name VARCHAR(100),
  processed_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_data.user_events (
  id SERIAL PRIMARY KEY,
  type VARCHAR(255),
  event VARCHAR(255),
  timestamp TIMESTAMP,
  server_timestamp TIMESTAMP,
  session_id VARCHAR(255),
  user_id VARCHAR(255),
  client_ip VARCHAR(50),
  user_agent TEXT,
  properties JSONB,
  queue_name VARCHAR(100),
  processed_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_data.ecommerce_events (
  id SERIAL PRIMARY KEY,
  type VARCHAR(255),
  event VARCHAR(255),
  timestamp TIMESTAMP,
  server_timestamp TIMESTAMP,
  session_id VARCHAR(255),
  user_id VARCHAR(255),
  client_ip VARCHAR(50),
  user_agent TEXT,
  properties JSONB,
  queue_name VARCHAR(100),
  processed_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_data.analytics_events (
  id SERIAL PRIMARY KEY,
  type VARCHAR(255),
  event VARCHAR(255),
  timestamp TIMESTAMP,
  server_timestamp TIMESTAMP,
  session_id VARCHAR(255),
  user_id VARCHAR(255),
  client_ip VARCHAR(50),
  user_agent TEXT,
  properties JSONB,
  queue_name VARCHAR(100),
  processed_timestamp TIMESTAMP
);

-- Legacy table for backward compatibility
CREATE TABLE IF NOT EXISTS raw_data.events (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(255),
  event_type VARCHAR(100),
  timestamp TIMESTAMP,
  path VARCHAR(255),
  product_id VARCHAR(100),
  value NUMERIC,
  transaction_id VARCHAR(255),
  reason VARCHAR(255)
);
EOF
echo "PostgreSQL schemas and tables created."

# 2. Ensure RabbitMQ queues exist
echo "Declaring RabbitMQ queues..."
if ! command -v curl &> /dev/null; then
  echo "Installing curl and jq..."
  if command -v apk &> /dev/null; then
    apk add --no-cache curl jq
  else
    apt-get update && apt-get install -y curl jq
  fi
fi

# Create all required queues
for QUEUE in "$RABBITMQ_QUEUE" "page_views" "user_events" "ecommerce_events" "analytics_events" "traffic_generation" "data_processing"; do
  echo "Declaring queue: $QUEUE"
  curl -u guest:guest -H "content-type:application/json" \
    -X PUT -d '{"durable":true}' \
    http://rabbitmq:15672/api/queues/%2F/$QUEUE
done
echo "RabbitMQ queues ensured."

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
prefect variable set work_pool "${WORK_POOL}" --overwrite

# Create work pool if not already defined
if ! prefect work-pool inspect "$WORK_POOL" > /dev/null 2>&1; then
  prefect work-pool create "$WORK_POOL" --type process
  echo "Created work pool '$WORK_POOL'"
else
  echo "Work pool '$WORK_POOL' already exists"
fi

echo "Registering deployment via prefect.yaml..."
cd /app/prefect
prefect deploy --all
cd -
echo "Prefect deployment registered."

echo "Initialization complete."