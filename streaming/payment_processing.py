import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, struct, to_json
from payment_schema import parse_payment_stream

def create_spark_session():
    return SparkSession.builder \
        .appName("PaymentStreamingProcessor") \
        .config("spark.sql.session.timeZone", "UTC") \
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
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "true") \
        .load()
    
    # Parse JSON and separate valid/invalid for DLQ
    parsed_df = parse_payment_stream(df)
    
    valid_df = parsed_df.filter(col("validation_error").isNull())
    dlq_df = parsed_df.filter(col("validation_error").isNotNull()).select(
        to_json(struct("raw_value", "validation_error", "source_topic", "source_partition", "source_offset")).alias("value")
    )
    
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
        
    # One transaction per microbatch. A failed batch rolls back; a retried
    # batch is harmless because payment_id and event_id are unique.
    def write_to_postgres(batch_df, batch_id):
        import psycopg2
        from psycopg2.extras import execute_values

        columns = [
            "payment_id", "event_id", "schema_version", "trace_id", "customer_id",
            "account_id", "merchant_id", "amount", "currency", "payment_method",
            "channel", "location", "device_id", "status",
        ]
        payment_df = batch_df.select(*columns, col("event_time").alias("timestamp"))
        insert_sql = """
            INSERT INTO core_banking.payment_event
                (payment_id, event_id, schema_version, trace_id, customer_id,
                 account_id, merchant_id, amount, currency, payment_method,
                 channel, location, device_id, status, timestamp)
            VALUES %s ON CONFLICT DO NOTHING
        """
        conn = psycopg2.connect(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            connect_timeout=10,
        )
        try:
            with conn:
                with conn.cursor() as cursor:
                    rows = []
                    for row in payment_df.toLocalIterator():
                        rows.append(tuple(row))
                        if len(rows) >= 500:
                            execute_values(cursor, insert_sql, rows, page_size=500)
                            rows.clear()
                    if rows:
                        execute_values(cursor, insert_sql, rows, page_size=500)
        finally:
            conn.close()
            
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
