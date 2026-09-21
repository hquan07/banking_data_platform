import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

def create_spark_session():
    # We include ClickHouse JDBC driver to write from Spark directly to ClickHouse
    return SparkSession.builder \
        .appName("ClickHouseWarehousePipeline") \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.6.0,com.clickhouse:clickhouse-jdbc:0.4.6") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
        .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", "")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD", "")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def run_pipeline(spark):
    print("Starting ClickHouse Warehouse Pipeline...")
    
    # 1. EXTRACT (Read from Data Lake - MinIO Silver Layer)
    print("Extracting customer data from MinIO (Silver)...")
    s3_path = "s3a://banking-lake/silver/customers/"
    try:
        silver_df = spark.read.parquet(s3_path)
    except Exception as e:
        print(f"Failed to read from MinIO, make sure customer_pipeline.py has run: {e}")
        return
        
    # 2. TRANSFORM (Prepare for ClickHouse Star Schema)
    dim_customer_df = silver_df.select(
        col("customer_id"),
        col("first_name"),
        col("last_name"),
        col("email"),
        col("phone"),
        col("address"),
        col("city"),
        col("account_id"),
        col("account_type"),
        col("balance"),
        col("account_status")
    )
    
    # 3. LOAD (Write to ClickHouse)
    print("Loading data into ClickHouse DWH (Gold Layer)...")
    clickhouse_url = "jdbc:clickhouse://localhost:8123/banking_warehouse"
    clickhouse_properties = {
        "user": os.environ.get("CLICKHOUSE_USER", ""),
        "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
        "driver": "com.clickhouse.jdbc.ClickHouseDriver"
    }
    
    try:
        # Note: In a real environment, the table should be created in ClickHouse with MergeTree engine first.
        # Spark JDBC will create a basic table if it doesn't exist, but it might not be optimal MergeTree.
        dim_customer_df.write.jdbc(
            url=clickhouse_url, 
            table="dim_customer", 
            mode="overwrite", 
            properties=clickhouse_properties
        )
        print("Successfully loaded into ClickHouse!")
    except Exception as e:
        print(f"Error writing to ClickHouse: {e}")

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    run_pipeline(spark)
