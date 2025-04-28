#!/bin/bash
set -e

# Create schemas and tables
echo "Creating PostgreSQL schemas in database '$POSTGRES_DB'..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
-- Drops all raw_data tables cleanly before recreation
DROP SCHEMA IF EXISTS raw_data CASCADE;
DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS analytics CASCADE;

-- Recreate the schemas
CREATE SCHEMA IF NOT EXISTS raw_data;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Create fresh raw_data tables matching Spark output
CREATE TABLE raw_data.page_views (
    id SERIAL PRIMARY KEY,
    type VARCHAR(255),
    timestamp TIMESTAMPTZ,
    server_timestamp TIMESTAMPTZ,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    client_ip VARCHAR(50),
    user_agent TEXT,
    url TEXT,
    path TEXT,
    properties JSONB,
    queue_name VARCHAR(100),
    processed_timestamp TIMESTAMPTZ
);

CREATE TABLE raw_data.user_events (
    id SERIAL PRIMARY KEY,
    type VARCHAR(255),
    event VARCHAR(255),
    timestamp TIMESTAMPTZ,
    server_timestamp TIMESTAMPTZ,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    client_ip VARCHAR(50),
    user_agent TEXT,
    properties JSONB,
    queue_name VARCHAR(100),
    processed_timestamp TIMESTAMPTZ
);

CREATE TABLE raw_data.ecommerce_events (
    id SERIAL PRIMARY KEY,
    type VARCHAR(255),
    event VARCHAR(255),
    timestamp TIMESTAMPTZ,
    server_timestamp TIMESTAMPTZ,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    client_ip VARCHAR(50),
    user_agent TEXT,
    properties JSONB,
    queue_name VARCHAR(100),
    processed_timestamp TIMESTAMPTZ
);

CREATE TABLE raw_data.analytics_events (
    id SERIAL PRIMARY KEY,
    type VARCHAR(255),
    event VARCHAR(255),
    timestamp TIMESTAMPTZ,
    server_timestamp TIMESTAMPTZ,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    client_ip VARCHAR(50),
    user_agent TEXT,
    properties JSONB,
    queue_name VARCHAR(100),
    processed_timestamp TIMESTAMPTZ
);

CREATE TABLE raw_data.event_queue (
    id SERIAL PRIMARY KEY,
    type VARCHAR(255),
    timestamp TIMESTAMPTZ,
    server_timestamp TIMESTAMPTZ,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    client_ip VARCHAR(50),
    user_agent TEXT,
    url TEXT,
    path TEXT,
    properties JSONB,
    queue_name VARCHAR(100),
    processed_timestamp TIMESTAMPTZ
);
EOF

# Create Datadog user and setup permissions
echo "Configuring PostgreSQL for Datadog monitoring..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" <<EOSQL
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

# Enable pg_stat_statements in template1 for future databases
echo "Enabling pg_stat_statements in template1..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d template1 -c \
  "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Setup datadog schema and explain_statement function in all databases
echo "Setting up datadog schema in all databases..."
for dbname in $(psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT datname FROM pg_database WHERE datistemplate = false;"); do
  echo "Setting up datadog schema in database: $dbname"
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$dbname" <<EOSQL
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

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
EOSQL
done

# Create Prefect database if it doesn't exist
echo "Creating Prefect database if it doesn't exist..."
DB_EXISTS=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1 FROM pg_database WHERE datname='${PREFECT_DB}'")

# Create the database if it doesn't exist
if [ "$DB_EXISTS" != "1" ]; then
    echo "Creating Prefect database..."
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE \"${PREFECT_DB}\""
fi