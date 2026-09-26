import pyspark.sql.functions as F
from pyspark.sql.window import Window

def apply_shared_device_rule(df):
    """
    Phát hiện thiết bị (device_id) được chia sẻ bởi nhiều tài khoản (account_id) trong 1 giờ.
    Nếu > 2 tài khoản dùng chung thiết bị => cảnh báo.
    """
    # This rule requires tracking state by device_id over time.
    # We will use windowing by device_id.
    
    # We count unique account_id per device_id over a sliding window
    window_spec = df \
        .withWatermark("event_time", "1 hours") \
        .groupBy(
            F.window(F.col("event_time"), "1 hours"),
            F.col("device_id")
        ) \
        .agg(
            F.countDistinct("account_id").alias("unique_accounts"),
            F.first("payment_id").alias("payment_id"),
            F.first("account_id").alias("account_id"),
            F.first("amount").alias("amount"),
            F.first("event_time").alias("event_time")
        )
        
    # If a device has more than 2 unique accounts
    flagged_df = window_spec.filter(F.col("unique_accounts") > 2)
    
    # Format to match the alert schema
    result_df = flagged_df.select(
        F.col("payment_id"),
        F.col("account_id"),
        F.col("amount"),
        F.lit(80).alias("risk_score"),
        F.lit("SHARED_DEVICE").alias("rule")
    )
    
    return result_df
