from prefect import flow, task
from pathlib import Path
import shutil
import subprocess
import os

# Directories
RAW_DIR = Path("/data/raw")
PROCESSING_DIR = Path("/data/processing")
ARCHIVE_DIR = Path("/data/archive")

# Configurtion
SPARK_SCRIPT = os.getenv("SPARK_SCRIPT", "/opt/spark/jobs/process_logs.py")
DBT_PROJECT_DIR = os.getenv("DBT_PROFILES_DIR", "/opt/dbt")

# RabbitMQ queues to process
QUEUES = [
    "page_views",
    "user_events",
    "ecommerce_events",
    "analytics_events",
    os.getenv("RABBITMQ_QUEUE", "event_queue")
]


@task
def list_raw_files():
    """List all JSON files that need processing"""
    all_files = []

    for queue in QUEUES:
        queue_dir = RAW_DIR / queue
        if queue_dir.exists():
            # Find all JSON files recursively
            files = list(queue_dir.glob("**/*.json"))
            all_files.extend(files)

    return all_files


@task
def move_files_to_processing(files: list[Path]) -> list[Path]:
    """Move files to processing directory, preserving structure"""
    PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
    moved = []

    for f in files:
        # Get relative path from RAW_DIR
        rel_path = f.relative_to(RAW_DIR)

        # Create destination path
        dest = PROCESSING_DIR / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(f), dest)
        moved.append(dest)

    print(f"Moved {len(moved)} files to processing directory")
    return moved


@task
def run_spark_job():
    """Run the Spark job to process data"""
    print(f"Running Spark job: {SPARK_SCRIPT}")
    result = subprocess.run(["spark-submit", SPARK_SCRIPT],
                            capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Spark job failed:\n{result.stderr}")
    return True


@task
def archive_processed_files(files: list[Path]):
    """Archive processed files, preserving structure"""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    for f in files:
        # Get relative path from PROCESSING_DIR
        rel_path = f.relative_to(PROCESSING_DIR)

        # Create destination path
        dest = ARCHIVE_DIR / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        if f.exists():  # Check if file still exists
            shutil.move(str(f), dest)

    print(f"Archived {len(files)} processed files")


@flow(name="gadgetgrove-dbt-flow")
def run_dbt_transform():
    """Run dbt transformations as a standalone flow"""
    print("Running dbt transformations")
    result = subprocess.run([
        "docker", "run", "--rm",
        "--network", "host",
        "-v", f"{DBT_PROJECT_DIR}:{DBT_PROJECT_DIR}",
        "-e", "DBT_PROFILES_DIR=" + DBT_PROJECT_DIR,
        "dbt-postgres-arm64:latest",
        "dbt", "run"
    ], capture_output=True, text=True)

    print("[✓] dbt run output:\n", result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"[X] dbt run failed:\n{result.stderr}")
    return True


@flow(name="gadgetgrove-analytics-pipeline")
def run_pipeline():
    """Main pipeline flow"""
    files = list_raw_files()
    if not files:
        print("No new files found to process.")
        return

    # Move files to processing directory
    moved = move_files_to_processing(files)

    # Process with Spark
    spark_success = run_spark_job()

    # Archive processed files
    if spark_success:
        archive_processed_files(moved)

        # Run dbt transformations
        run_dbt_transform()

    print("Pipeline completed successfully")


if __name__ == "__main__":
    run_pipeline()
