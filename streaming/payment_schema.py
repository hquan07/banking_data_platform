"""Spark parser and validation for payment-events v1."""

from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType, IntegerType, StringType, StructField, StructType

PAYMENT_SCHEMA = StructType([
    StructField("schema_version", IntegerType()),
    StructField("event_id", StringType()),
    StructField("trace_id", StringType()),
    StructField("payment_id", StringType()),
    StructField("customer_id", StringType()),
    StructField("account_id", StringType()),
    StructField("merchant_id", StringType()),
    StructField("amount", DecimalType(18, 2)),
    StructField("currency", StringType()),
    StructField("payment_method", StringType()),
    StructField("channel", StringType()),
    StructField("location", StringType()),
    StructField("device_id", StringType()),
    StructField("timestamp", StringType()),
    StructField("status", StringType()),
])


def parse_payment_stream(kafka_df):
    """Return parsed events with validation_error for quarantine routing."""
    parsed = kafka_df.select(
        F.col("value").cast("string").alias("raw_value"),
        F.col("topic").alias("source_topic"),
        F.col("partition").alias("source_partition"),
        F.col("offset").alias("source_offset"),
    ).withColumn("data", F.from_json("raw_value", PAYMENT_SCHEMA))
    parsed = parsed.select("raw_value", "source_topic", "source_partition", "source_offset", "data.*")
    parsed = parsed.withColumn("event_time", F.to_timestamp("timestamp"))
    missing_id = None
    for field, maximum in (("event_id", 120), ("trace_id", 50), ("payment_id", 50), ("customer_id", 50), ("account_id", 50)):
        condition = F.col(field).isNull() | (F.length(F.trim(F.col(field))) == 0) | (F.length(F.col(field)) > maximum)
        missing_id = condition if missing_id is None else missing_id | condition
    return parsed.withColumn(
        "validation_error",
        F.when(F.col("schema_version").isNull() | (F.col("schema_version") != 1), "unsupported_schema_version")
        .when(missing_id, "missing_identifier")
        .when(
            F.col("amount").isNull()
            | (F.col("amount") <= 0)
            | (F.col("amount") > 99999999999.99)
            | ~F.get_json_object("raw_value", "$.amount").rlike(r"^[0-9]+(\.[0-9]{1,2})?$"),
            "invalid_amount",
        )
        .when(F.length(F.col("merchant_id")) > 50, "invalid_merchant_id")
        .when(F.length(F.col("device_id")) > 50, "invalid_device_id")
        .when(F.length(F.col("location")) > 100, "invalid_location")
        .when(F.col("currency").isNull() | ~F.col("currency").rlike("^[A-Z]{3}$"), "invalid_currency")
        .when(F.col("payment_method").isNull() | ~F.col("payment_method").isin("CARD", "BANK_TRANSFER", "QR"), "invalid_payment_method")
        .when(F.col("channel").isNull() | ~F.col("channel").isin("POS", "ONLINE", "ATM"), "invalid_channel")
        .when(F.col("status").isNull() | ~F.col("status").isin("CREATED", "PENDING", "SUCCESS", "FAILED"), "invalid_status")
        .when(F.col("event_time").isNull(), "invalid_timestamp"),
    )
