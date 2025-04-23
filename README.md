# GadgetGrove Analytics Pipeline

This project demonstrates a full-stack, containerized analytics pipeline for an e-commerce platform using FastAPI, Celery, RabbitMQ, Spark, dbt, PostgreSQL, and Prefect. It includes synthetic traffic generation, raw log ingestion, event processing, transformation, and a live dashboard.

## 🧩 System Overview

### Mermaid Diagram

```mermaid
flowchart TD
    %% Core Services
    webapp["webapp (FastAPI/Dash)"]
    celery_traffic["celery-traffic<br>(User Session Generator)"]
    celery_beat["celery-beat<br>(Task Scheduler)"]
    raw_consumer["raw-consumer<br>(RabbitMQ Consumer)"]
    rabbitmq["rabbitmq<br>(Message Broker)"]
    postgres["postgres-db<br>(Database)"]
    spark_master["spark-master"]
    spark_worker["spark-worker"]
    prefect_server["prefect-server<br>(Workflow Orchestrator)"]
    prefect_agent["prefect-agent<br>(Worker Pool)"]
    init["init<br>(Setup Script)"]

    %% Data flows
    celery_beat -->|schedules tasks| celery_traffic
    celery_traffic -->|simulates user browsing| webapp
    webapp -->|"captures analytics events<br>(both real & simulated)"| rabbitmq
    rabbitmq -->|page_views, user_events,<br>ecommerce_events,<br>analytics_events| raw_consumer
    raw_consumer -->|writes| log_files[("Log Files")]

    prefect_server -->|schedules jobs| prefect_agent
    prefect_agent -->|triggers| spark_worker
    spark_master -->|manages| spark_worker
    spark_worker -->|processes logs| log_files
    spark_worker -->|loads processed data| postgres

    prefect_agent -->|triggers| dbt["dbt transformations"]
    dbt -->|transforms data| postgres
    postgres -->|provides data| webapp

    %% Setup flow
    init -->|configures| postgres
    init -->|sets up queues| rabbitmq
    init -->|creates worker pool| prefect_server
    init -->|creates deployments| prefect_server

    %% Styling with improved contrast
    classDef webapp fill:#d580ff,stroke:#333,stroke-width:2px,color:#000
    classDef queue fill:#ffd966,stroke:#333,stroke-width:1px,color:#000
    classDef database fill:#4a86e8,stroke:#333,stroke-width:2px,color:#fff
    classDef processing fill:#6aa84f,stroke:#333,stroke-width:1px,color:#000
    classDef orchestration fill:#a64d79,stroke:#333,stroke-width:1px,color:#fff
    classDef setup fill:#666666,stroke:#333,stroke-width:1px,color:#fff

    class webapp,celery_traffic webapp
    class rabbitmq queue
    class postgres database
    class raw_consumer,spark_master,spark_worker processing
    class prefect_server,prefect_agent,celery_beat orchestration
    class init setup
```

---

## 🧱 Components Breakdown

| Service          | Purpose                                                                 |
| ---------------- | ----------------------------------------------------------------------- |
| `webapp`         | FastAPI + Dash UI for the e-commerce site and analytics dashboard       |
| `celery-traffic` | Simulates user traffic and publishes events to RabbitMQ                 |
| `celery-beat`    | Schedules periodic traffic generation                                   |
| `raw-consumer`   | Consumes RabbitMQ events and stores raw JSON logs on disk               |
| `rabbitmq`       | Message broker between traffic generation and raw consumer              |
| `postgres-db`    | Stores all app data, analytics tables (raw + transformed), and metadata |
| `spark-master`   | Spark coordinator for distributed processing of raw logs                |
| `spark-worker`   | Processes files for transformations into PostgreSQL                     |
| `prefect-server` | Orchestrates data pipeline flows (Spark + dbt)                          |
| `prefect-agent`  | Worker that executes Spark and dbt flows on a schedule                  |
| `dbt`            | Transforms raw*data.* into analytics.\_ views used by dashboard         |
| `init`           | Bootstraps queues, PostgreSQL schema, and registers Prefect deployments |
| `datadog-agent`  | Observability: collects APM, infra metrics, and integrations            |

---

## 🚀 Getting Started

- Install Docker + Docker Compose
- Clone this repo
- Configure `.env` with your Datadog API key and optional Git metadata
- Run the project:
  ```bash
  make build
  make up
  ```

See `Makefile` for available commands.

---

## 📊 Dashboard Access

- **WebApp**: http://localhost:8000/
- **Analytics Dashboard**: http://localhost:8050/
- **Prefect UI**: http://localhost:4200/

---

## 🧪 Synthetic Data Flow

1. Celery Beat schedules traffic every minute.
2. Celery Traffic worker generates events → RabbitMQ
3. Raw consumer (pika) logs JSON events → disk
4. Prefect agent triggers Spark job → transforms to PostgreSQL `raw_data.*`
5. dbt transforms → `analytics.*`
6. Analytics dashboard queries `analytics.*`

---

## 📦 Observability

All services are instrumented with `ddtrace` for:

- APM traces
- Logs
- Infra metrics
- Custom metrics (event counts, ingestion timing)

Prefect generates artifacts for:

- Spark ingestion summaries
- Archive cleanup reports
