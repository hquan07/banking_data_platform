import os


def read_silver(spark, path):
    return spark.read.parquet(path)


def write_clickhouse(dim_customer_df, url, properties):
    dim_customer_df.write.jdbc(
        url=url,
        table="dim_customer",
        mode="overwrite",
        properties=properties,
    )


def write_postgres(dim_customer_df, url, properties):
    dim_customer_df.write.jdbc(
        url=url,
        table="data_warehouse.dim_customer",
        mode="append",
        properties=properties,
    )

def create_spark_session():
    from pyspark.sql import SparkSession

    # We include ClickHouse JDBC driver to write from Spark directly to ClickHouse
    return SparkSession.builder \
        .appName("ClickHouseWarehousePipeline") \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.6.0,com.clickhouse:clickhouse-jdbc:0.4.6") \
        .config("spark.hadoop.fs.s3a.endpoint", os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")) \
        .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", "")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD", "")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def run_pipeline(spark):
    from pyspark.sql.functions import col

    print("Starting ClickHouse Warehouse Pipeline...")
    
    # 1. EXTRACT (Read from Data Lake - MinIO Silver Layer)
    print("Extracting customer data from MinIO (Silver)...")
    s3_path = "s3a://banking-lake/silver/customers/"
    silver_df = read_silver(spark, s3_path)
        
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
    clickhouse_url = (
        f"jdbc:clickhouse://{os.environ.get('CLICKHOUSE_HOST', 'localhost')}:"
        f"{os.environ.get('CLICKHOUSE_HTTP_PORT', '8123')}/"
        f"{os.environ.get('CLICKHOUSE_DB', 'banking_warehouse')}"
    )
    clickhouse_properties = {
        "user": os.environ.get("CLICKHOUSE_USER", ""),
        "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
        "driver": "com.clickhouse.jdbc.ClickHouseDriver"
    }
    
    # Fail the task on sink errors instead of reporting a successful run.
    write_clickhouse(dim_customer_df, clickhouse_url, clickhouse_properties)
    print("Successfully loaded into ClickHouse!")

    # Gold writes run only after the Silver quality task succeeds in Airflow.
    postgres_url = (
        f"jdbc:postgresql://{os.environ.get('POSTGRES_HOST', 'localhost')}:"
        f"{os.environ.get('POSTGRES_PORT', '5433')}/"
        f"{os.environ.get('POSTGRES_DB', 'banking_data_platform')}"
    )
    postgres_properties = {
        "user": os.environ.get("POSTGRES_USER", ""),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
        "driver": "org.postgresql.Driver",
    }
    postgres_customer_df = silver_df.select(
        col("customer_id"), col("first_name"), col("last_name"), col("gender"),
        col("country"), col("email"), col("phone"), col("address"), col("city"),
    ).dropDuplicates(["customer_id"])
    from pyspark.sql.functions import lit

    postgres_customer_df = postgres_customer_df.withColumn("customer_type", lit(None).cast("string")) \
        .withColumn("effective_start_date", lit(None).cast("timestamp")) \
        .withColumn("effective_end_date", lit(None).cast("timestamp")) \
        .withColumn("is_current", lit(True))
    write_postgres(postgres_customer_df, postgres_url, postgres_properties)
    print("Successfully loaded into PostgreSQL DWH!")

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    run_pipeline(spark)
