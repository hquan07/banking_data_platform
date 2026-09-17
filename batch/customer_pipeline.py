import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp

def create_spark_session():
    return SparkSession.builder \
        .appName("CustomerBatchPipeline") \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.6.0") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def run_pipeline(spark):
    print("Starting Customer Batch Pipeline...")
    
    db_url = "jdbc:postgresql://localhost:5433/banking_data_platform"
    db_properties = {
        "user": "banking_user",
        "password": "banking_password",
        "driver": "org.postgresql.Driver"
    }
    
    # 1. EXTRACT (Read from Postgres Core Banking)
    print("Extracting customer data from Core Banking...")
    customer_df = spark.read.jdbc(url=db_url, table="core_banking.customer", properties=db_properties)
    account_df = spark.read.jdbc(url=db_url, table="core_banking.account", properties=db_properties)
    
    # 2. TRANSFORM (Join and clean)
    print("Transforming data (Bronze -> Silver)...")
    silver_df = customer_df.join(account_df, "customer_id", "left") \
        .select(
            customer_df["customer_id"],
            customer_df["first_name"],
            customer_df["last_name"],
            customer_df["email"],
            customer_df["phone"],
            customer_df["address"],
            customer_df["city"],
            account_df["account_id"],
            account_df["account_type"],
            account_df["balance"],
            account_df["status"].alias("account_status")
        ) \
        .withColumn("processed_at", current_timestamp())
    
    # 3. LOAD to Data Lake (MinIO)
    print("Loading data into MinIO Data Lake (Silver Layer)...")
    s3_path = "s3a://banking-lake/silver/customers/"
    
    # We must ensure the bucket exists in MinIO or handle it.
    # We will assume 'banking-lake' bucket is created manually or by another script.
    # For MVP robustness, we just write. Spark will create the folder, but MinIO needs the bucket.
    
    try:
        silver_df.write.mode("overwrite").parquet(s3_path)
        print("Successfully written to Data Lake!")
    except Exception as e:
        print(f"Warning: Could not write to MinIO (Bucket might not exist yet): {e}")

    # 4. LOAD to Data Warehouse (Postgres DWH)
    print("Loading data into Data Warehouse (Gold Layer / Star Schema)...")
    dim_customer_df = customer_df.select(
        col("customer_id"),
        col("first_name"),
        col("last_name"),
        col("email"),
        col("phone"),
        col("address"),
        col("city"),
        col("country")
    )
    dim_customer_df.write.jdbc(url=db_url, table="data_warehouse.dim_customer", mode="append", properties=db_properties)
    print("Successfully loaded into DWH!")

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    run_pipeline(spark)
