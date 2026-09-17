from pyspark.sql.functions import col, lit

def apply_large_amount_rule(parsed_df, threshold=10000.0):
    return parsed_df.filter(col("amount") > threshold) \
        .withColumn("fraud_score", lit(80)) \
        .withColumn("risk_level", lit("HIGH")) \
        .withColumn("triggered_rules", lit("LARGE_TRANSACTION")) \
        .withColumn("decision", lit("REVIEW")) \
        .withColumn("alert_time", col("event_time")) \
        .select(
            col("payment_id"),
            col("fraud_score"),
            col("risk_level"),
            col("triggered_rules"),
            col("decision"),
            col("alert_time").alias("timestamp")
        )
