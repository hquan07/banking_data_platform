import great_expectations as gx
import pandas as pd

def run_dq_checks(data_path):
    print(f"Bắt đầu chạy Data Quality Checks cho dữ liệu tại {data_path}...")
    
    # Khởi tạo GX Context (trong production sẽ cấu hình kết nối tới S3/MinIO)
    context = gx.get_context(mode="ephemeral")
    
    # Mock dữ liệu để demo kiểm tra (trong thực tế sẽ đọc từ MinIO: pd.read_parquet(data_path))
    data = {
        "customer_id": ["CUS_1", "CUS_2", "CUS_3", None], # Có 1 lỗi Null
        "balance": [100.5, 5000.0, -50.0, 200.0],         # Có 1 lỗi số âm
        "account_status": ["ACTIVE", "ACTIVE", "CLOSED", "ACTIVE"]
    }
    df = pd.DataFrame(data)
    
    # Đăng ký Data Source
    datasource = context.sources.add_pandas(name="banking_pandas_datasource")
    data_asset = datasource.add_dataframe_asset(name="customer_asset")
    
    # Build Batch Request
    batch_request = data_asset.build_batch_request(dataframe=df)
    
    # Tạo Validator và Expectation Suite
    context.add_or_update_expectation_suite("customer_suite")
    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name="customer_suite"
    )
    
    print("Đang áp dụng các luật kiểm tra dữ liệu...")
    # 1. Kiểm tra không được NULL
    validator.expect_column_values_to_not_be_null(column="customer_id")
    
    # 2. Kiểm tra số dư không được âm
    validator.expect_column_values_to_be_between(column="balance", min_value=0)
    
    # 3. Kiểm tra trạng thái tài khoản hợp lệ
    validator.expect_column_values_to_be_in_set(
        column="account_status", 
        value_set=["ACTIVE", "CLOSED", "SUSPENDED"]
    )
    
    # Lưu luật
    validator.save_expectation_suite(discard_failed_expectations=False)
    
    # Chạy kiểm tra
    checkpoint = context.add_or_update_checkpoint(
        name="customer_checkpoint",
        validations=[{
            "batch_request": batch_request,
            "expectation_suite_name": "customer_suite"
        }]
    )
    
    print("Đang đánh giá kết quả...")
    results = checkpoint.run()
    
    if not results["success"]:
        print("[LỖI NGHIÊM TRỌNG] Data Quality Check THẤT BẠI!")
        print("Pipeline sẽ bị chặn, không nạp dữ liệu rác vào ClickHouse DWH.")
        # Bắn lỗi để Airflow đánh dấu Task là FAILED
        raise ValueError("Data Quality checks failed.")
    else:
        print("[THÀNH CÔNG] Dữ liệu sạch, sẵn sàng nạp vào Data Warehouse.")

if __name__ == "__main__":
    try:
        run_dq_checks("s3a://banking-lake/silver/customers/")
    except Exception as e:
        print(e)
