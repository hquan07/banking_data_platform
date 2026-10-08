import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


def write_silver(silver_df, path):
    silver_df.write.mode("overwrite").parquet(path)

def create_spark_session():
    from pyspark.sql import SparkSession

    return SparkSession.builder \
        .appName("CustomerBatchPipeline") \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.6.0") \
        .config("spark.hadoop.fs.s3a.endpoint", os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")) \
        .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", "")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD", "")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def run_pipeline(spark):
    from pyspark.sql.functions import current_timestamp, regexp_replace, concat, substring, lit

    print("Starting Customer Batch Pipeline...")
    
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5433")
    db = os.environ.get("POSTGRES_DB", "banking_data_platform")
    db_url = f"jdbc:postgresql://{host}:{port}/{db}"
    db_properties = {
        "user": os.environ.get("POSTGRES_USER", ""),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
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
            concat(substring(customer_df["first_name"], 1, 1), lit("***")).alias("first_name"),
            concat(substring(customer_df["last_name"], 1, 1), lit("***")).alias("last_name"),
            regexp_replace(customer_df["email"], "^(.*)@(.*)$", "***@$2").alias("email"),
            concat(lit("*******"), substring(customer_df["phone"], -4, 4)).alias("phone"),
            lit("REDACTED").alias("address"),
            customer_df["country"],
            customer_df["gender"],
            account_df["account_id"],
            account_df["account_type"],
            account_df["balance"],
            account_df["status"].alias("account_status"),
            lit(None).cast("string").alias("city")
        ) \
        .withColumn("processed_at", current_timestamp())
    
    # 3. LOAD to Data Lake (MinIO)
    print("Loading data into MinIO Data Lake (Silver Layer)...")
    s3_path = "s3a://banking-lake/silver/customers/"
    
    # A failed Silver write must fail the Airflow task; otherwise downstream
    # quality checks can inspect stale data while this run still loads Gold.
    write_silver(silver_df, s3_path)
    print("Successfully written to Data Lake!")

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    run_pipeline(spark)
