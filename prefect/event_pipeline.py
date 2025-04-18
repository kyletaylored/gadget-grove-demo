from prefect import flow, task
from pathlib import Path
import shutil
import subprocess
import os

RAW_DIR = Path("/data/raw")
PROCESSING_DIR = Path("/data/processing")
ARCHIVE_DIR = Path("/data/archive")
SPARK_SCRIPT = "/opt/spark/jobs/process_logs.py"


@task
def list_raw_files():
    files = sorted(RAW_DIR.glob("*.json"))
    return files


@task
def move_files_to_processing(files: list[Path]) -> list[Path]:
    PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
    moved = []
    for f in files:
        dest = PROCESSING_DIR / f.name
        shutil.move(str(f), dest)
        moved.append(dest)
    return moved


@task
def run_spark_job():
    result = subprocess.run(["spark-submit", SPARK_SCRIPT],
                            capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Spark job failed:\n{result.stderr}")


@task
def archive_processed_files(files: list[Path]):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.move(str(f), ARCHIVE_DIR / f.name)


@flow(name="gadgetgrove-pipeline")
def run_pipeline():
    files = list_raw_files()
    if not files:
        print("No new files found.")
        return
    moved = move_files_to_processing(files)
    run_spark_job()
    archive_processed_files(moved)


@task
def run_dbt_transform():
    result = subprocess.run([
        "docker", "run", "--rm",
        "--network", "host",  # required so container can reach postgres-db
        "-v", f"{os.getcwd()}/dbt_project:/usr/app",
        "-e", "DBT_PROFILES_DIR=/usr/app",
        "dbt-postgres-arm64:latest",
        "dbt", "run"
    ], capture_output=True, text=True)

    print("[✓] dbt run output:\n", result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"[X] dbt run failed:\n{result.stderr}")


if __name__ == "__main__":
    run_pipeline()
