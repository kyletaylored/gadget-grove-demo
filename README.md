# 🛍️ GadgetGrove Analytics Pipeline

Welcome to the GadgetGrove demo project — a fully containerized e-commerce analytics pipeline built with modern data tools. This setup simulates event ingestion, Spark-based transformation, dbt modeling, and analytics dashboarding, all with observability via Datadog.

## ⚙️ Architecture Overview

```mermaid
flowchart TB
  subgraph WebApp
    A[User Traffic Simulator] --> B[FastAPI Web App]
    B --> C[Event JSON files]
  end

  subgraph Data Pipeline
    C --> D[Prefect Flow: Spark Task]
    D --> E[Spark Job: PySpark]
    E --> F[(PostgreSQL)]
    F --> G[dbt Transformations]
    G --> H[Analytics Dashboard (Dash)]
  end

  subgraph Observability
    D --> I[Datadog Artifacts]
    E --> I
    G --> I
    H --> I
  end

  subgraph Archive + Cleanup
    D --> J[Archive JSON Files]
    J --> K[Cleanup (Scheduled Prefect Flow)]
  end
```

---

## 🧪 Tech Stack

| Layer           | Tooling                                |
| --------------- | -------------------------------------- |
| Event Ingestion | JSON files written from user simulator |
| Data Processing | Apache Spark (PySpark), PostgreSQL     |
| Transformation  | dbt-core                               |
| Orchestration   | Prefect v2 (Dockerized agent + server) |
| Dashboard       | Plotly Dash                            |
| Observability   | Datadog (APM, logs, artifacts)         |

---

## 🚀 Quickstart

> **Note:** Ensure Docker + Docker Compose are installed. You’ll also need Python if you plan to edit dbt flows or dashboards locally.

```bash
# 1. Clone the repository
git clone https://github.com/your-org/gadgetgrove-demo.git
cd gadgetgrove-demo

# 2. Configure environment
cp .env.example .env   # Edit as needed

# 3. Build and start services
make up  # Builds and runs with Git metadata for Datadog

# 4. Visit the dashboard
open http://localhost:8050
```

---

## 📊 Observability

This pipeline is integrated with Datadog for:

- Distributed Tracing (`ddtrace`)
- Task-based Artifacts (`prefect.artifacts`)
- Metrics (via PostgreSQL + Datadog agent)
- Spark + container logs (autodiscovery enabled)

---

## 🧼 Cleanup Jobs

Archived JSON files from Spark are stored in `/data/archive`. A scheduled Prefect flow runs hourly to delete files older than `ARCHIVE_RETENTION_HOURS` (default: 1 hour).

Artifacts are automatically created to report:

- Number of files cleaned
- Breakdown by queue type

---

## 👩‍💻 Contributing & Local Development

### Working with dbt

```bash
make dbt # Runs `dbt run` inside the container with mounted volumes
```

### Developing Dash

Edit files in `dashboard/`, then reload the app at `http://localhost:8050`.

### Debugging Spark

Logs are available via the Spark UI:

```bash
open http://localhost:4040
```

---

## 🧠 Tips for New Developers

- **Prefect flows** live in `prefect/event_pipeline.py`
- **Spark jobs** live in `spark/jobs/`
- **dbt models** are in `dbt/models/`
- Use `make build` and `make up` to bootstrap consistently
- Prefect is used for orchestration and artifact reporting
- If something breaks, check `docker compose logs -f`

---

## 📎 Project Metadata

- Uses Git SHA as the version tag for Datadog
- All services are instrumented for APM visibility
- Containers share a `.env` file for consistent config
