from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, from_json, to_timestamp, lit, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, MapType, ArrayType
import os
from pathlib import Path

# Database configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "events")
POSTGRES_URL = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Data paths
PROCESSING_DIR = Path("/data/processing")
RAW_DIR = Path("/data/raw")

# Common fields schema (extend as needed)
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
    StructField("_processed_at", StringType(), True)
])


def process_queue_data(spark, queue_name):
    """Process data from a specific queue"""
    queue_dir = RAW_DIR / queue_name

    if not queue_dir.exists():
        print(f"No data found for queue: {queue_name}")
        return

    # Path for all JSON files in this queue
    json_path = str(queue_dir) + "/**/*.json"

    # Read all JSON files recursively
    print(f"Reading data from {json_path}")
    df = spark.read.schema(BASE_SCHEMA).json(json_path)

    if df.count() == 0:
        print(f"No records found for queue: {queue_name}")
        return

    # Common transformations
    df = df.withColumn("processed_timestamp", current_timestamp()) \
           .withColumn("timestamp", to_timestamp(col("timestamp"))) \
           .withColumn("server_timestamp", to_timestamp(col("server_timestamp"))) \
           .withColumn("queue_name", lit(queue_name))

    # Write to the appropriate table
    table_name = f"raw_data.{queue_name.replace('-', '_')}"

    df.write \
      .format("jdbc") \
      .option("url", POSTGRES_URL) \
      .option("dbtable", table_name) \
      .option("user", POSTGRES_USER) \
      .option("password", POSTGRES_PASSWORD) \
      .option("driver", "org.postgresql.Driver") \
      .mode("append") \
      .save()

    print(f"Wrote {df.count()} records to {table_name}")

    # Move processed files
    # TODO: Add code to move or delete processed files

    return df


def main():
    # Initialize Spark
    spark = SparkSession.builder \
        .appName("Process RabbitMQ Event Data") \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
        .getOrCreate()

    # Process each queue
    queues = ["page_views", "user_events",
              "ecommerce_events", "analytics_events", "event_queue"]

    total_records = 0
    for queue in queues:
        try:
            df = process_queue_data(spark, queue)
            if df:
                total_records += df.count()
        except Exception as e:
            print(f"Error processing {queue}: {e}")

    print(f"Total processed records: {total_records}")

    spark.stop()


if __name__ == "__main__":
    main()
