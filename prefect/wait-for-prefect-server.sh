#!/bin/bash
set -e

until curl -sf http://prefect-server:4200/api/health; do
  echo "Waiting for Prefect server..."
  sleep 5
done

echo "Prefect server is up. Starting agent..."
exec prefect worker start --pool default-agent-pool
