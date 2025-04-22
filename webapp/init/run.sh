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

# Create Datadog user and setup permissions for metrics
echo "Configuring PostgreSQL for Datadog monitoring..."

PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$POSTGRES_PORT" <<EOSQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'datadog') THEN
    EXECUTE format('CREATE USER datadog WITH PASSWORD %L', '${DATADOG_PG_PASSWORD}');
  END IF;
END
\$\$;

ALTER ROLE datadog INHERIT;
CREATE SCHEMA IF NOT EXISTS datadog;
GRANT USAGE ON SCHEMA datadog TO datadog;
GRANT USAGE ON SCHEMA public TO datadog;
GRANT pg_monitor TO datadog;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE OR REPLACE FUNCTION datadog.explain_statement(
   l_query TEXT,
   OUT explain JSON
)
RETURNS SETOF JSON AS \$\$
DECLARE
  curs REFCURSOR;
  plan JSON;
BEGIN
  OPEN curs FOR EXECUTE pg_catalog.concat('EXPLAIN (FORMAT JSON) ', l_query);
  FETCH curs INTO plan;
  CLOSE curs;
  RETURN QUERY SELECT plan;
END;
\$\$
LANGUAGE 'plpgsql'
RETURNS NULL ON NULL INPUT
SECURITY DEFINER;
EOSQL

echo "PostgreSQL Datadog monitoring user and permissions configured."

echo "Ensuring 'datadog' schema and explain_statement function exist in all databases..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d postgres -p "$POSTGRES_PORT" -tAc \
  "SELECT datname FROM pg_database WHERE datistemplate = false;" | while read -r dbname; do
    echo " - Setting up datadog schema in database: $dbname"
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$dbname" -p "$POSTGRES_PORT" <<EOSQL
CREATE SCHEMA IF NOT EXISTS datadog;
GRANT USAGE ON SCHEMA datadog TO datadog;
GRANT USAGE ON SCHEMA public TO datadog;
GRANT pg_monitor TO datadog;

CREATE OR REPLACE FUNCTION datadog.explain_statement(
   l_query TEXT,
   OUT explain JSON
)
RETURNS SETOF JSON AS \$\$
DECLARE
  curs REFCURSOR;
  plan JSON;
BEGIN
  OPEN curs FOR EXECUTE pg_catalog.concat('EXPLAIN (FORMAT JSON) ', l_query);
  FETCH curs INTO plan;
  CLOSE curs;
  RETURN QUERY SELECT plan;
END;
\$\$
LANGUAGE 'plpgsql'
RETURNS NULL ON NULL INPUT
SECURITY DEFINER;
EOSQL
done

echo "Datadog schema and explain function ensured in all databases."

echo "Enabling pg_stat_statements in template1 for all future databases..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d template1 -p "$POSTGRES_PORT" -c \
  "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;" \
  && echo "pg_stat_statements enabled in template1." \
  || echo "Warning: Could not enable pg_stat_statements in template1."

echo "Ensuring pg_stat_statements is enabled on all existing databases..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d postgres -p "$POSTGRES_PORT" -tAc \
  "SELECT datname FROM pg_database WHERE datistemplate = false;" | while read -r dbname; do
    echo " - Enabling pg_stat_statements in database: $dbname"
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$dbname" -p "$POSTGRES_PORT" -c \
      "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;" \
      && echo "   (✔ success)" || echo "   (failed or already exists)"
done
echo "pg_stat_statements is now ensured for current and future databases."


# Ensure RabbitMQ queues exist
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

# Set Prefect profile config to use Postgres
echo "Ensuring Prefect database '$PREFECT_DB' exists..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" -tc \
  "SELECT 1 FROM pg_database WHERE datname = '${PREFECT_DB}'" | grep -q 1 \
  || PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" -c \
  "CREATE DATABASE ${PREFECT_DB};"
echo "Prefect database ensured."

# Prefect Deployment Setup
echo "Ensuring Prefect process work pool '$WORK_POOL' exists..."
if prefect work-pool inspect "$WORK_POOL" >/dev/null 2>&1; then
  echo "Deleting existing work pool '$WORK_POOL'..."
  prefect work-pool delete "$WORK_POOL"
fi

prefect work-pool create "$WORK_POOL" --type process
echo "Created process work pool '$WORK_POOL'"

echo "Registering deployments from prefect.yaml..."
cd /app/prefect
prefect deploy --all
cd -
echo "Prefect deployments registered."

echo "Initialization complete."