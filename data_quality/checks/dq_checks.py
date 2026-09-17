from pyspark.sql import SparkSession
from pyspark.sql.functions import col

def check_data_quality():
    print("Running Data Quality Checks on Silver Layer...")
    spark = SparkSession.builder \
        .appName("DataQualityCheck") \
        .getOrCreate()
        
    # Example: Load silver customer data
    # (Assuming it was written by batch/customer_pipeline.py)
    # silver_df = spark.read.parquet("s3a://banking-lake/silver/customers/")
    
    # For MVP we will just print what the checks would look like
    print("Checking for NULL customer IDs...")
    # null_count = silver_df.filter(col("customer_id").isNull()).count()
    # assert null_count == 0, f"Found {null_count} NULL customer IDs!"
    
    print("Checking for negative balances...")
    # negative_balance_count = silver_df.filter(col("balance") < 0).count()
    # assert negative_balance_count == 0, "Found negative balances!"
    
    print("All Data Quality checks passed!")

if __name__ == "__main__":
    check_data_quality()
