import os
import uuid
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, count, lit, when, to_timestamp, expr
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

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
        
    # We will use Watermarking for stateful processing
    watermarked_df = parsed_df.withWatermark("event_time", "10 minutes")

    db_url = "jdbc:postgresql://localhost:5433/banking_data_platform"
    db_properties = {
        "user": "banking_user",
        "password": "banking_password",
        "driver": "org.postgresql.Driver"
    }

    # ==========================================
    # RULE 1: LARGE TRANSACTION (Stateless)
    # Amount > 10,000 USD
    # ==========================================
    large_txn_df = parsed_df.filter(col("amount") > 10000.0) \
        .withColumn("fraud_score", lit(80)) \
        .withColumn("risk_level", lit("HIGH")) \
        .withColumn("triggered_rules", lit("LARGE_TRANSACTION")) \
        .withColumn("decision", lit("REVIEW")) \
        .withColumn("alert_time", col("event_time")) \
        .select(
            col("payment_id"), # In MVP we might map this to fact_payment if we look it up, but just store the ID for now
            col("fraud_score"),
            col("risk_level"),
            col("triggered_rules"),
            col("decision"),
            col("alert_time").alias("timestamp")
        )

    def write_large_txn_to_postgres(batch_df, batch_id):
        # In a real DWH, we would join with Dim Date and Fact Payment to get Surrogate Keys.
        # For simplicity, we just write to a console or raw alert table.
        # We will write directly to fact_fraud_alert for MVP, but since we don't have payment_sk easily without joining postgres,
        # we might just log it. Let's write to console for simplicity and robustness in MVP.
        pass
        
    query_large_txn = large_txn_df \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .start()

    # ==========================================
    # RULE 2: HIGH VELOCITY (Stateful)
    # > 5 transactions per account within 5 minutes
    # ==========================================
    velocity_df = watermarked_df \
        .groupBy(
            window(col("event_time"), "5 minutes"),
            col("account_id")
        ) \
        .agg(count("payment_id").alias("txn_count")) \
        .filter(col("txn_count") > 5) \
        .select(
            col("account_id"),
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("txn_count"),
            lit("HIGH_VELOCITY").alias("triggered_rules"),
            lit(70).alias("fraud_score"),
            lit("MEDIUM").alias("risk_level"),
            lit("MONITOR").alias("decision")
        )

    query_velocity = velocity_df \
        .writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", False) \
        .start()

    # ==========================================
    # RULE 3: AML STRUCTURING (Stateful)
    # Multiple small transactions summing to a large amount near threshold ($10,000)
    # e.g., > 3 transactions, total amount > $9,000 within 24 hours (we use 1 hour for demo)
    # ==========================================
    from pyspark.sql.functions import sum as _sum
    
    structuring_df = watermarked_df \
        .filter(col("amount") < 10000.0) \
        .groupBy(
            window(col("event_time"), "1 hour"),
            col("account_id")
        ) \
        .agg(
            count("payment_id").alias("txn_count"),
            _sum("amount").alias("total_amount")
        ) \
        .filter((col("txn_count") >= 3) & (col("total_amount") > 9000.0)) \
        .select(
            col("account_id"),
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("txn_count"),
            col("total_amount"),
            lit("STRUCTURING_AML_PATTERN").alias("triggered_rules"),
            lit(90).alias("fraud_score"),
            lit("CRITICAL").alias("risk_level"),
            lit("REVIEW").alias("decision")
        )

    query_structuring = structuring_df \
        .writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", False) \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    start_fraud_engine(spark)
