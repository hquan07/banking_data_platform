from pyspark.sql.functions import col, lit, window, count

def apply_velocity_rule(watermarked_df, window_duration="5 minutes", count_threshold=5):
    return watermarked_df \
        .groupBy(
            window(col("event_time"), window_duration),
            col("account_id")
        ) \
        .agg(count("payment_id").alias("txn_count")) \
        .filter(col("txn_count") > count_threshold) \
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
