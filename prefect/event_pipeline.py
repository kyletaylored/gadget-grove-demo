from prefect import flow, task
from prefect.artifacts import create_markdown_artifact, create_table_artifact
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import os
from ddtrace import patch_all

patch_all()

# Configuration
SPARK_SCRIPT = os.getenv("SPARK_SCRIPT", "/opt/spark/jobs/process_logs.py")
DBT_PROJECT_DIR = os.getenv("DBT_PROJECT_DIR", "/opt/dbt")
DBT_PROFILES_DIR = os.getenv("DBT_PROFILES_DIR", "/opt/dbt")

# Default location for archived files
ARCHIVE_DIR = Path("/data/archive")
RETENTION_HOURS = int(os.getenv("ARCHIVE_RETENTION_HOURS", "1"))


@task
def run_spark_job():
    """Run the Spark job to process data"""
    print(f"Running Spark job: {SPARK_SCRIPT}")
    result = subprocess.run(["spark-submit", SPARK_SCRIPT],
                            capture_output=True, text=True)
    print(result.stdout)

    if result.returncode != 0:
        create_markdown_artifact(
            key="spark-status",
            markdown=f"Spark job failed:\n```\n{result.stderr}\n```",
            description="Spark job failed"
        )
        raise Exception(f"Spark job failed:\n{result.stderr}")

    # TODO: Replace with actual counts loaded during spark job
    table_counts = {
        "page_views": 3421,
        "user_events": 1980,
        "ecommerce_events": 875,
        "analytics_events": 142,
        "event_queue": 700
    }

    create_markdown_artifact(
        key="spark-status",
        markdown="Spark job completed successfully and wrote data to PostgreSQL.",
        description="Spark job completed successfully"
    )

    rows = [{"Queue": k, "Rows Ingested": v} for k, v in table_counts.items()]
    create_table_artifact(key="spark-ingestion-summary",
                          table=rows,
                          description="Summary of rows ingested by queue")

    return True


@flow(name="gadgetgrove-dbt-pipeline")
def run_dbt_transform():
    """Run dbt transformations inside the container"""
    print("Running dbt transformations...")

    result = subprocess.run([
        "dbt", "run",
        "--project-dir", DBT_PROJECT_DIR,
        "--profiles-dir", DBT_PROFILES_DIR
    ], capture_output=True, text=True)

    print("[\u2713] dbt run output:\n", result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"[X] dbt run failed:\n{result.stderr}")
    return True


@flow(name="gadgetgrove-analytics-pipeline")
def run_pipeline():
    """Main pipeline flow with Spark and dbt as sub-tasks"""
    spark_success = run_spark_job()
    if spark_success:
        run_dbt_transform()
    print("Pipeline completed successfully")


@task
def cleanup_old_files():
    """Delete files older than RETENTION_HOURS in the archive directory"""
    now = datetime.now()
    cutoff = now - timedelta(hours=RETENTION_HOURS)
    deleted = 0

    for file in ARCHIVE_DIR.rglob("*"):
        if file.is_file():
            modified = datetime.fromtimestamp(file.stat().st_mtime)
            if modified < cutoff:
                file.unlink()
                deleted += 1

    print(
        f"[✓] Deleted {deleted} archived files older than {RETENTION_HOURS} hour(s)")
    return deleted


@flow(name="gadgetgrove-cleanup-archive")
def cleanup_archived_files():
    """Flow to clean up archived files on a schedule"""
    cleanup_old_files()
