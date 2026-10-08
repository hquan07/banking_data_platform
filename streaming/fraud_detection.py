import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_json, struct
from payment_schema import parse_payment_stream

# Ensure modules in other folders can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fraud.rules.large_amount import apply_large_amount_rule
from fraud.rules.velocity import apply_velocity_rule
from fraud.rules.velocity_redis import process_velocity_with_redis
from fraud.rules.shared_device import apply_shared_device_rule
from aml.rules.structuring import apply_structuring_rule

def create_spark_session():
    return SparkSession.builder \
        .appName("FraudDetectionEngine") \
        .config("spark.sql.session.timeZone", "UTC") \
        .getOrCreate()

def start_fraud_engine(spark):
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("subscribe", "payment-events") \
        .option("startingOffsets", "earliest") \
        .option("maxOffsetsPerTrigger", os.environ.get("SPARK_MAX_OFFSETS_PER_TRIGGER", "1000")) \
        .option("failOnDataLoss", "true") \
        .load()
    
    parsed_df = parse_payment_stream(df).filter(col("validation_error").isNull())
        
    watermarked_df = parsed_df.withWatermark("event_time", "10 minutes")

    # No ML scoring until a real labeled dataset, time-split evaluation and
    # versioned model artifact have been approved. The legacy synthetic model
    # is deliberately never loaded or used for live case creation.
    from pyspark.sql.functions import lit

    # ==========================================
    # RULE 2: LARGE AMOUNT
    # ==========================================
    large_amount_df = apply_large_amount_rule(watermarked_df)
    query_large_amount = large_amount_df \
        .selectExpr("CAST(payment_id AS STRING) AS key", "to_json(struct(*)) AS value") \
        .writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("topic", "fraud-events") \
        .option("checkpointLocation", os.environ.get("SPARK_CHECKPOINT_DIR", "s3a://checkpoints") + "/large_amount") \
        .start()

    # ==========================================
    # RULE 3: HIGH VELOCITY (Stateful)
    # ==========================================
    velocity_df = apply_velocity_rule(watermarked_df)

    query_velocity = velocity_df \
        .withColumn("rule", lit("HIGH_VELOCITY")) \
        .selectExpr("CAST(account_id AS STRING) AS key", "to_json(struct(*)) AS value") \
        .writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("topic", "fraud-events") \
        .option("checkpointLocation", os.environ.get("SPARK_CHECKPOINT_DIR", "s3a://checkpoints") + "/velocity") \
        .start()

    # ==========================================
    # RULE 4: AML STRUCTURING (Stateful)
    # ==========================================
    structuring_df = apply_structuring_rule(watermarked_df)

    query_structuring = structuring_df \
        .withColumn("rule", lit("STRUCTURING_SUSPICION")) \
        .selectExpr("CAST(account_id AS STRING) AS key", "to_json(struct(*)) AS value") \
        .writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("topic", "aml-events") \
        .option("checkpointLocation", os.environ.get("SPARK_CHECKPOINT_DIR", "s3a://checkpoints") + "/structuring") \
        .start()

    # ==========================================
    # RULE 4: HIGH VELOCITY (REDIS STATEFUL)
    # ==========================================
    query_redis = parsed_df \
        .writeStream \
        .outputMode("update") \
        .foreachBatch(process_velocity_with_redis) \
        .option("checkpointLocation", os.environ.get("SPARK_CHECKPOINT_DIR", "/checkpoints/fraud-engine") + "/redis_velocity") \
        .start()

    # ==========================================
    # RULE 5: SHARED DEVICE (Entity Resolution)
    # ==========================================
    shared_device_df = apply_shared_device_rule(
        parsed_df.withWatermark("event_time", "1 hours")
    )

    query_shared_device = shared_device_df \
        .selectExpr("CAST(account_id AS STRING) AS key", "to_json(struct(*)) AS value") \
        .writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("topic", "fraud-events") \
        .option("checkpointLocation", os.environ.get("SPARK_CHECKPOINT_DIR", "s3a://checkpoints") + "/shared_device") \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    start_fraud_engine(spark)
