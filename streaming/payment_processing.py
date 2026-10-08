import os
from datetime import timezone
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, struct, to_json
from payment_schema import parse_payment_stream

CLICKHOUSE_PAYMENT_DDL = """
CREATE TABLE IF NOT EXISTS payment_events (
    payment_id String, event_id String, trace_id String, customer_id String,
    account_id String, merchant_id String, amount Decimal(18, 2), currency String,
    payment_method String, channel String, location String, device_id String,
    status String, event_time DateTime64(3, 'UTC'),
    ingested_at DateTime64(3, 'UTC') DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(ingested_at) ORDER BY payment_id
"""
PAYMENT_COLUMNS = (
    "payment_id", "event_id", "schema_version", "trace_id", "customer_id",
    "account_id", "merchant_id", "amount", "currency", "payment_method",
    "channel", "location", "device_id", "status", "timestamp",
)
CLICKHOUSE_INSERT = (
    "INSERT INTO payment_events (payment_id, event_id, trace_id, customer_id, "
    "account_id, merchant_id, amount, currency, payment_method, channel, "
    "location, device_id, status, event_time) VALUES"
)
CANONICAL_PAYMENT_SELECT = """
    SELECT payment_id, event_id, trace_id, customer_id, account_id,
           merchant_id, amount, currency, payment_method, channel,
           location, device_id, status, timestamp
    FROM core_banking.payment_event WHERE payment_id = ANY(%s)
"""


def clickhouse_client():
    from clickhouse_driver import Client

    return Client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ.get("CLICKHOUSE_PORT", "9000")),
        database=os.environ["CLICKHOUSE_DB"],
        user=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
        send_receive_timeout=10,
    )


def payment_values(row):
    values = row.asDict()
    timestamp = values["timestamp"]
    values["timestamp"] = timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp.astimezone(timezone.utc)
    return tuple(values[field] for field in PAYMENT_COLUMNS)


def clickhouse_values(postgres_row):
    values = list(postgres_row)
    for index in (5, 10, 11):
        values[index] = values[index] or ""
    return tuple(values)

def create_spark_session():
    return SparkSession.builder \
        .appName("PaymentStreamingProcessor") \
        .config("spark.sql.session.timeZone", "UTC") \
        .getOrCreate()

def process_stream(spark):
    client = clickhouse_client()
    try:
        client.execute(CLICKHOUSE_PAYMENT_DDL)
    finally:
        client.disconnect()

    # Read from Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("subscribe", "payment-events") \
        .option("startingOffsets", "earliest") \
        .option("maxOffsetsPerTrigger", os.environ.get("SPARK_MAX_OFFSETS_PER_TRIGGER", "1000")) \
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

        payment_df = batch_df.select(*PAYMENT_COLUMNS[:-1], col("event_time").alias("timestamp"))
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
                        rows.append(payment_values(row))
                        if len(rows) >= 500:
                            execute_values(cursor, insert_sql, rows, page_size=500)
                            rows.clear()
                    if rows:
                        execute_values(cursor, insert_sql, rows, page_size=500)
        finally:
            conn.close()

        # ClickHouse receives canonical PostgreSQL rows only. If a malformed
        # duplicate event_id was rejected in PostgreSQL, it cannot appear in
        # ClickHouse. A failed ClickHouse write makes Spark replay the batch.
        read_conn = psycopg2.connect(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            connect_timeout=10,
        )
        try:
            ch = clickhouse_client()
            try:
                with read_conn.cursor() as cursor:
                    ids = []
                    for row in batch_df.select("payment_id").toLocalIterator():
                        ids.append(row.payment_id)
                        if len(ids) >= 500:
                            cursor.execute(CANONICAL_PAYMENT_SELECT, (ids,))
                            rows = [clickhouse_values(item) for item in cursor.fetchall()]
                            if rows:
                                ch.execute(CLICKHOUSE_INSERT, rows)
                            ids.clear()
                    if ids:
                        cursor.execute(CANONICAL_PAYMENT_SELECT, (ids,))
                        rows = [clickhouse_values(item) for item in cursor.fetchall()]
                        if rows:
                            ch.execute(CLICKHOUSE_INSERT, rows)
            finally:
                ch.disconnect()
        finally:
            read_conn.close()
            
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
