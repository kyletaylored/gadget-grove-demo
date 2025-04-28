#!/bin/sh
set -e

# Wait until Agent's config is fully generated
echo "Waiting for Datadog Agent to initialize..."
until [ -f /etc/datadog-agent/datadog-docker.yaml ]; do
  sleep 1
done

echo "Datadog Agent initialized. Installing Prefect integration..."
agent integration install -r -w /tmp/datadog_prefect-1.0.0-py3-none-any.whl

echo "Starting Datadog Agent..."
exec agent run
