#!/bin/bash
set -euo pipefail

echo "Initializing GadgetGrove system..."


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