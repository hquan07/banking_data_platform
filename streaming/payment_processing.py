import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# Define the schema of the JSON payload from Kafka
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
        .appName("PaymentStreamingProcessor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
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
    
    # Parse JSON
    parsed_df = df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), payment_schema).alias("data")) \
        .select("data.*")
    
    # Write to console (for debugging)
    console_query = parsed_df \
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
            
    db_query = parsed_df \
        .writeStream \
        .foreachBatch(write_to_postgres) \
        .option(
            "checkpointLocation",
            os.environ.get("SPARK_CHECKPOINT_DIR", "/tmp/checkpoints/payment_processor"),
        ) \
        .start()
        
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    process_stream(spark)
