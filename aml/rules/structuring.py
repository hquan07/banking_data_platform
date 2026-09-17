from pyspark.sql.functions import col, lit, window, count, sum as _sum

def apply_structuring_rule(watermarked_df, threshold_amount=10000.0, sum_threshold=9000.0, count_threshold=3, window_duration="1 hour"):
    return watermarked_df \
        .filter(col("amount") < threshold_amount) \
        .groupBy(
            window(col("event_time"), window_duration),
            col("account_id")
        ) \
        .agg(
            count("payment_id").alias("txn_count"),
            _sum("amount").alias("total_amount")
        ) \
        .filter((col("txn_count") >= count_threshold) & (col("total_amount") > sum_threshold)) \
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
