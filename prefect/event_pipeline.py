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


@task(retries=2, retry_delay_seconds=10)
def run_spark_job():
    """Run the Spark job script and return result and log info."""
    print(f"Running Spark job: {SPARK_SCRIPT}")
    result = subprocess.run(["spark-submit", SPARK_SCRIPT],
                            capture_output=True, text=True)
    print(result.stdout)
    return result


@task(retries=2, retry_delay_seconds=10)
def analyze_spark_output(result) -> dict:
    """Analyze Spark result and prepare artifact data."""
    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    # TODO: Replace with actual counts loaded during spark job
    return {
        "status": "success",
        "table_counts": {
            "page_views": 3421,
            "user_events": 1980,
            "ecommerce_events": 875,
            "analytics_events": 142,
            "event_queue": 700
        }
    }


@task(retries=2, retry_delay_seconds=10)
def generate_spark_artifacts(analysis: dict):
    """Generate markdown and table artifacts for Spark results."""
    if analysis["status"] == "success":
        create_markdown_artifact(
            key="spark-status",
            markdown="Spark job completed successfully and wrote data to PostgreSQL.",
            description="Spark job completed successfully"
        )

        rows = [{"Queue": k, "Rows Ingested": v}
                for k, v in analysis["table_counts"].items()]
        create_table_artifact(
            key="spark-ingestion-summary",
            table=rows,
            description="Summary of rows ingested by queue"
        )


@flow(name="gadgetgrove-dbt-pipeline", retries=2, retry_delay_seconds=10)
def run_dbt_transform():
    """Run dbt transformations inside the container"""
    print("Running dbt transformations...")

    result = subprocess.run([
        "dbt", "run",
        "--project-dir", DBT_PROJECT_DIR,
        "--profiles-dir", DBT_PROFILES_DIR
    ], capture_output=True, text=True)

    print("[✓] dbt run output:\n", result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"[X] dbt run failed:\n{result.stderr}")
    return True


@flow(name="gadgetgrove-analytics-pipeline", retries=2, retry_delay_seconds=10)
def run_pipeline():
    """Main pipeline flow with Spark and dbt as sub-tasks"""
    result = run_spark_job()
    try:
        analysis = analyze_spark_output(result)
        generate_spark_artifacts(analysis)
        print("Pipeline completed successfully")
    except Exception as e:
        create_markdown_artifact(
            key="spark-status",
            markdown=f"Spark job failed:\n```\n{str(e)}\n```",
            description="Spark job failed"
        )
        raise


@task(retries=2, retry_delay_seconds=10)
def cleanup_old_files():
    """Delete files older than RETENTION_HOURS in the archive directory and return stats."""
    now = datetime.now()
    cutoff = now - timedelta(hours=RETENTION_HOURS)
    deleted_counts = {}
    total_deleted = 0

    for queue_dir in ARCHIVE_DIR.iterdir():
        if not queue_dir.is_dir():
            continue

        deleted_for_queue = 0
        for file in queue_dir.rglob("*.json"):
            modified = datetime.fromtimestamp(file.stat().st_mtime)
            if modified < cutoff:
                file.unlink()
                deleted_for_queue += 1

        if deleted_for_queue:
            deleted_counts[queue_dir.name] = deleted_for_queue
            total_deleted += deleted_for_queue

    return deleted_counts, total_deleted


@task(retries=2, retry_delay_seconds=10)
def create_cleanup_artifact(deleted_counts: dict, total_deleted: int):
    now = datetime.now()
    if total_deleted:
        table_md = "| Queue | Files Deleted |\n|--------|----------------|"
        for queue, count in deleted_counts.items():
            table_md += f"\n| {queue} | {count} |"

        markdown = f"""
        ### Archive Cleanup Report

        A total of **{total_deleted}** file(s) were deleted from the archive.

        {table_md}

        _Updated at {now.strftime('%Y-%m-%d %H:%M:%S')}_
        """
        create_markdown_artifact(
            key="archive-cleanup-report",
            markdown=markdown,
            description=f"Deleted {total_deleted} archived files during cleanup task."
        )


@flow(name="gadgetgrove-cleanup-archive", retries=2, retry_delay_seconds=10)
def cleanup_archived_files():
    """Flow to clean up archived files on a schedule"""
    deleted_counts, total_deleted = cleanup_old_files()
    create_cleanup_artifact(deleted_counts, total_deleted)
