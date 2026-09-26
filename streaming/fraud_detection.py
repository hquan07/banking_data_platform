import os
import sys
import uuid
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_timestamp, to_json, struct
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# Ensure modules in other folders can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fraud.rules.large_amount import apply_large_amount_rule
from fraud.rules.velocity import apply_velocity_rule
from fraud.rules.velocity_redis import process_velocity_with_redis
from fraud.rules.shared_device import apply_shared_device_rule
from aml.rules.structuring import apply_structuring_rule

import pandas as pd
import joblib
from pyspark.sql.functions import pandas_udf, PandasUDFType

# Tải model (giả định script chạy trên môi trường có file fraud_model.pkl)
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fraud", "scoring", "fraud_model.pkl")
try:
    rf_model = joblib.load(MODEL_PATH)
    print(f"Loaded ML model from {MODEL_PATH}")
except Exception as e:
    print(f"Failed to load ML model: {e}")
    rf_model = None

# Định nghĩa Pandas UDF để chạy dự đoán trên Spark Workers
@pandas_udf("double")
def predict_fraud_udf(amount: pd.Series, hour_of_day: pd.Series, velocity_1h: pd.Series, diff_from_avg: pd.Series, is_international: pd.Series) -> pd.Series:
    if rf_model is None:
        return pd.Series([0.0] * len(amount))
    
    # Tạo DataFrame để đưa vào mô hình scikit-learn
    df = pd.DataFrame({
        'amount': amount,
        'hour_of_day': hour_of_day,
        'velocity_1h': velocity_1h,
        'diff_from_avg': diff_from_avg,
        'is_international': is_international
    })
    
    # Dự đoán xác suất rủi ro (lấy probability của class 1)
    probs = rf_model.predict_proba(df)[:, 1]
    return pd.Series(probs)

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
        .appName("FraudDetectionEngine") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262") \
        .config("spark.hadoop.fs.s3a.endpoint", os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")) \
        .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", "minioadmin")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def start_fraud_engine(spark):
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("subscribe", "payment-events") \
        .option("startingOffsets", "latest") \
        .load()
    
    parsed_df = df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), payment_schema).alias("data")) \
        .select("data.*") \
        .withColumn("event_time", to_timestamp(col("timestamp")))
        
    watermarked_df = parsed_df.withWatermark("event_time", "10 minutes")

    # ==========================================
    # RULE 1: MACHINE LEARNING (Stateless/Batch)
    # ==========================================
    # Giả lập trích xuất thêm các features cho ML từ dữ liệu luồng
    from pyspark.sql.functions import hour, rand, when, lit
    
    ml_features_df = parsed_df \
        .withColumn("hour_of_day", hour(col("event_time"))) \
        .withColumn("velocity_1h", (rand() * 10).cast("int")) \
        .withColumn("diff_from_avg", rand() * 10) \
        .withColumn("is_international", when(col("location") != "VN", 1).otherwise(0))
        
    ml_scored_df = ml_features_df.withColumn(
        "ml_risk_score", 
        predict_fraud_udf(
            col("amount"), col("hour_of_day"), col("velocity_1h"), 
            col("diff_from_avg"), col("is_international")
        )
    )
    
    # Lọc ra các giao dịch có xác suất gian lận > 70%
    high_risk_df = ml_scored_df.filter(col("ml_risk_score") > 0.70).withColumn(
        "rule", lit("ML_MODEL_FRAUD")
    )
    
    query_ml_txn = high_risk_df \
        .selectExpr("CAST(payment_id AS STRING) AS key", "to_json(struct(*)) AS value") \
        .writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")) \
        .option("topic", "fraud-events") \
        .option("checkpointLocation", os.environ.get("SPARK_CHECKPOINT_DIR", "s3a://checkpoints") + "/ml_fraud") \
        .start()

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
        .start()

    # ==========================================
    # RULE 5: SHARED DEVICE (Entity Resolution)
    # ==========================================
    shared_device_df = apply_shared_device_rule(watermarked_df)

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
