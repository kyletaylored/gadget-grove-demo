#!/bin/bash
set -e

echo "Starting FastAPI (Uvicorn) on port 8000..."
ddtrace-run uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "Starting Dash dashboard on port 8050..."
ddtrace-run python dashboard.py &

# Wait for either process to exit
wait -n
