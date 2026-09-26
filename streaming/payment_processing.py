import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# Define the schema of the JSON payload from Kafka
payment_schema = StructType([
    StructField("payment_id", StringType(), True),
    StructField("trace_id", StringType(), True),
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
        .appName("PaymentStreamingProcessor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262") \
        .config("spark.hadoop.fs.s3a.endpoint", os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")) \
        .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", "minioadmin")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def process_stream(spark):
    # Read from Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("subscribe", "payment-events") \
        .option("startingOffsets", "latest") \
        .load()
    
    # Parse JSON and separate valid/invalid for DLQ
    parsed_df = df.selectExpr("CAST(value AS STRING) as raw_value") \
        .withColumn("data", from_json(col("raw_value"), payment_schema))
    
    valid_df = parsed_df.filter(col("data").isNotNull()).select("data.*")
    dlq_df = parsed_df.filter(col("data").isNull()).select(col("raw_value").alias("value"))
    
    # Write malformed events to DLQ topic
    dlq_query = dlq_df \
        .writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("topic", "payment-events-dlq") \
        .option(
            "checkpointLocation",
            os.environ.get("SPARK_CHECKPOINT_DIR", "s3a://checkpoints") + "/payment_processor_dlq",
        ) \
        .start()
        
    # Write to console (for debugging)
    console_query = valid_df \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .start()
        
    # Write to PostgreSQL
    # Note: Requires postgresql jdbc driver when submitting
    db_url = (
        f"jdbc:postgresql://{os.environ.get('POSTGRES_HOST', 'localhost')}:"
        f"{os.environ.get('POSTGRES_PORT', '5433')}/"
        f"{os.environ.get('POSTGRES_DB', 'banking_data_platform')}"
    )
    db_properties = {
        "user": os.environ.get("POSTGRES_USER", ""),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
        "driver": "org.postgresql.Driver"
    }
    
    def write_to_postgres(batch_df, batch_id):
        # Convert timestamp string back to actual timestamp if needed, but jdbc usually handles string-to-timestamp implicitly for simple formats, or we could cast it.
        # For MVP, we will cast it.
        from pyspark.sql.functions import to_timestamp
        casted_df = batch_df.withColumn("timestamp", to_timestamp("timestamp"))
        
        casted_df.write \
            .jdbc(url=db_url, table="core_banking.payment_event", mode="append", properties=db_properties)
            
    db_query = valid_df \
        .writeStream \
        .foreachBatch(write_to_postgres) \
        .option(
            "checkpointLocation",
            os.environ.get("SPARK_CHECKPOINT_DIR", "s3a://checkpoints") + "/payment_processor",
        ) \
        .start()
        
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    process_stream(spark)
