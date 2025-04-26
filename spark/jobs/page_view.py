from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, to_json, to_timestamp, struct
import os
import shutil
from pathlib import Path

# ----------------------------
# Configuration
# ----------------------------
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "events")
POSTGRES_URL = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
SPARK_MASTER = os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077")

RAW_DIR = Path("/data")
ARCHIVE_DIR = Path("/data/archive")

# ----------------------------
# Helper Functions
# ----------------------------


def archive_files(queue_dir: Path):
    archive_path = ARCHIVE_DIR / queue_dir.name
    archive_path.mkdir(parents=True, exist_ok=True)

    for file in queue_dir.glob("**/*.json"):
        relative = file.relative_to(queue_dir)
        dest = archive_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file), str(dest))


def process_page_views(spark):
    queue_name = "page_views"
    queue_dir = RAW_DIR / queue_name / "page_view"
    json_path = str(queue_dir / "*.json")

    if not queue_dir.exists():
        print(f"[!] Directory {queue_dir} does not exist.")
        return 0

    df = spark.read \
        .option("mode", "PERMISSIVE") \
        .json(json_path)

    print("[DEBUG] Schema:")
    df.printSchema()

    print("[DEBUG] Sample:")
    df.show(5, truncate=False)

    if df.rdd.isEmpty():
        print(f"[!] No data found in {queue_dir}.")
        return 0

    # Fill in missing fields for raw_data.page_views schema
    df_transformed = df \
        .withColumn("session_id", col("sessionId")) \
        .withColumn("queue_name", col("_queue")) \
        .withColumn("processed_timestamp", to_timestamp(col("_processed_at"))) \
        .withColumn("timestamp", to_timestamp(col("timestamp"))) \
        .withColumn("server_timestamp", lit(None).cast("timestamp")) \
        .withColumn("user_id", lit(None).cast("string")) \
        .withColumn("client_ip", lit(None).cast("string")) \
        .withColumn("user_agent", lit(None).cast("string")) \
        .withColumn("properties", to_json(struct())) \
        .drop("sessionId", "_queue", "_processed_at")

    df_transformed.write \
        .format("jdbc") \
        .option("url", POSTGRES_URL) \
        .option("dbtable", "raw_data.page_views") \
        .option("user", POSTGRES_USER) \
        .option("password", POSTGRES_PASSWORD) \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()

    row_count = df_transformed.count()
    print(f"[\u2713] Inserted {row_count} rows into raw_data.page_views.")

    archive_files(queue_dir)
    return row_count

# ----------------------------
# Main Entrypoint
# ----------------------------


def main():
    spark = SparkSession.builder \
        .appName("Process RabbitMQ Event Data") \
        .master(SPARK_MASTER) \
        .config("spark.jars", "/opt/bitnami/spark/jars/postgresql.jar") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    total_processed = process_page_views(spark)

    print(
        f"[\u2713] Completed processing. Total records processed: {total_processed}")

    spark.stop()


if __name__ == "__main__":
    main()
