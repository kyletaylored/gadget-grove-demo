FROM python:3.11-slim

WORKDIR /app

# Install PostgreSQL client + curl + jq (also used in run.sh)
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

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
