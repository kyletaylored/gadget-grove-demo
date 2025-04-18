from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

import os
from datetime import datetime

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "events")
POSTGRES_URL = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

RAW_DATA_PATH = "/data/processing"

EVENT_SCHEMA = StructType([
    StructField("session_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("path", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("value", DoubleType(), True),
    StructField("transaction_id", StringType(), True),
    StructField("reason", StringType(), True),
])


def main():
    spark = SparkSession.builder \
        .appName("Process Raw E-Commerce Events") \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
        .getOrCreate()

    df = spark.read \
        .schema(EVENT_SCHEMA) \
        .json(RAW_DATA_PATH)

    df = df.withColumn("timestamp", to_timestamp(col("timestamp")))

    df.write \
        .format("jdbc") \
        .option("url", POSTGRES_URL) \
        .option("dbtable", "raw_data.events") \
        .option("user", POSTGRES_USER) \
        .option("password", POSTGRES_PASSWORD) \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()

    print(f"[✓] Wrote {df.count()} records to raw_data.events")

    spark.stop()


if __name__ == "__main__":
    main()
