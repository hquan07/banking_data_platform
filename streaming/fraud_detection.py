import os
import sys
import uuid
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# Ensure modules in other folders can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fraud.rules.large_amount import apply_large_amount_rule
from fraud.rules.velocity import apply_velocity_rule
from fraud.rules.velocity_redis import process_velocity_with_redis
from aml.rules.structuring import apply_structuring_rule

payment_schema = StructType([
    StructField("payment_id", StringType(), True),
    StructField("customer_id", StringType(), True),
    StructField("account_id", StringType(), True),
    StructField("merchant_id", StringType(), True),
    StructField("amount", DoubleType(), True),
    StructField("currency", StringType(), True),
    StructField("payment_method", StringType(), True),
    StructField("channel", StringType(), True),
    StructField("location", StringType(), True),
    StructField("device_id", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("status", StringType(), True)
])

def create_spark_session():
    return SparkSession.builder \
        .appName("FraudDetectionEngine") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
        .getOrCreate()

def start_fraud_engine(spark):
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "payment-events") \
        .option("startingOffsets", "latest") \
        .load()
    
    parsed_df = df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), payment_schema).alias("data")) \
        .select("data.*") \
        .withColumn("event_time", to_timestamp(col("timestamp")))
        
    watermarked_df = parsed_df.withWatermark("event_time", "10 minutes")

    # ==========================================
    # RULE 1: LARGE TRANSACTION (Stateless)
    # ==========================================
    large_txn_df = apply_large_amount_rule(parsed_df)
    
    query_large_txn = large_txn_df \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .start()

    # ==========================================
    # RULE 2: HIGH VELOCITY (Stateful)
    # ==========================================
    velocity_df = apply_velocity_rule(watermarked_df)

    query_velocity = velocity_df \
        .writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", False) \
        .start()

    # ==========================================
    # RULE 3: AML STRUCTURING (Stateful)
    # ==========================================
    structuring_df = apply_structuring_rule(watermarked_df)

    query_structuring = structuring_df \
        .writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", False) \
        .start()

    # ==========================================
    # RULE 4: HIGH VELOCITY (REDIS STATEFUL)
    # ==========================================
    query_redis = parsed_df \
        .writeStream \
        .outputMode("update") \
        .foreachBatch(process_velocity_with_redis) \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    start_fraud_engine(spark)
