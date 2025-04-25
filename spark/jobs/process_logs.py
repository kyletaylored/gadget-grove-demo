from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, MapType
from pyspark.sql.functions import col, to_timestamp, lit, current_timestamp, to_json
import os
import shutil
from pathlib import Path
from ddtrace import patch_all

patch_all()

# Config
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "events")
POSTGRES_URL = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
POSTGRES_JDBC_VERSION = os.getenv("POSTGRES_JDBC_VERSION", "42.7.2")

RAW_DIR = Path("/data")
ARCHIVE_DIR = Path("/data/archive")
SPARK_MASTER = os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077")

# Schema
BASE_SCHEMA = StructType([
    StructField("type", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("server_timestamp", StringType(), True),
    StructField("sessionId", StringType(), True),
    StructField("userId", StringType(), True),
    StructField("client_ip", StringType(), True),
    StructField("user_agent", StringType(), True),
    StructField("url", StringType(), True),
    StructField("path", StringType(), True),
    StructField("properties", MapType(StringType(), StringType()), True),
    StructField("_queue", StringType(), True),
    StructField("_processed_at", StringType(), True),
    StructField("_corrupt_record", StringType(), True),
])


def archive_files(queue_dir: Path):
    archive_path = ARCHIVE_DIR / queue_dir.name
    archive_path.mkdir(parents=True, exist_ok=True)
    for file in queue_dir.glob("**/*.json"):
        relative = file.relative_to(queue_dir)
        dest = archive_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file), str(dest))


def process_queue_data(spark, queue_name):
    queue_dir = RAW_DIR / queue_name
    json_path = str(queue_dir / "**/*.json")

    if not queue_dir.exists():
        print(f"[!] No directory for queue: {queue_name}")
        return 0

    df = spark.read \
        .option("mode", "PERMISSIVE") \
        .option("columnNameOfCorruptRecord", "_corrupt_record") \
        .schema(BASE_SCHEMA) \
        .json(json_path)

    df = df.filter(col("_corrupt_record").isNull())
    if "_corrupt_record" in df.columns:
        df = df.drop("_corrupt_record")

    print("[DEBUG] Schema:")
    df.printSchema()
    print("[DEBUG] Sample:")
    df.show(5, truncate=False)

    if df.rdd.isEmpty():
        print(f"[!] No valid records in {queue_name}")
        return 0

    df = df.withColumn("processed_timestamp", current_timestamp()) \
        .withColumn("timestamp", to_timestamp(col("timestamp"))) \
        .withColumn("server_timestamp", to_timestamp(col("server_timestamp"))) \
        .withColumn("queue_name", lit(queue_name)) \
        .withColumn("properties", to_json(col("properties"))) \
        .withColumn("session_id", col("sessionId")).drop("sessionId") \
        .withColumn("user_id", col("userId")).drop("userId")

    table_name = f"raw_data.{queue_name.replace('-', '_')}"
    count = df.count()

    if count > 0:
        df.write \
          .format("jdbc") \
          .option("url", POSTGRES_URL) \
          .option("dbtable", table_name) \
          .option("user", POSTGRES_USER) \
          .option("password", POSTGRES_PASSWORD) \
          .option("driver", "org.postgresql.Driver") \
          .mode("append") \
          .save()

        print(f"[✓] Inserted {count} records to {table_name}")
        archive_files(queue_dir)

    return count


def main():
    spark = SparkSession.builder \
        .appName("Process RabbitMQ Event Data") \
        .master(SPARK_MASTER) \
        .config("spark.jars", "/opt/bitnami/spark/jars/postgresql.jar") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    queues = ["page_views", "user_events",
              "ecommerce_events", "analytics_events", "event_queue"]
    total = 0

    for q in queues:
        try:
            total += process_queue_data(spark, q)
        except Exception as e:
            print(f"[X] Error processing {q}: {e}")

    print(f"[✓] Total processed: {total}")
    spark.stop()


if __name__ == "__main__":
    main()
