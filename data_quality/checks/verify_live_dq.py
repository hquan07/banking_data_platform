"""Run a disposable good/bad customer Silver DQ round trip in the Airflow container."""

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from great_expectations_check import postgres_connection, run_dq_checks, storage_options  # noqa: E402


def main():
    suffix = uuid.uuid4().hex
    s3 = boto3.client(
        "s3", endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
    )
    keys = []
    run_ids = []
    customer_id = f"E2E_CUS_{suffix[:16]}"
    account_id = f"E2E_ACC_{suffix[:16]}"
    with postgres_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO core_banking.customer (customer_id, first_name, last_name) "
                "VALUES (%s, 'E2E', 'DQ')", (customer_id,),
            )
            cursor.execute(
                "INSERT INTO core_banking.account (account_id, customer_id, account_type, status) "
                "VALUES (%s, %s, 'SAVINGS', 'ACTIVE')", (account_id, customer_id),
            )
    original_run_id = os.environ.get("AIRFLOW_CTX_DAG_RUN_ID")
    try:
        for expected_success in (True, False):
            run_id = f"e2e-dq-{suffix}-{'good' if expected_success else 'bad'}"
            run_ids.append(run_id)
            key = f"e2e/customer-dq/{run_id}.parquet"
            keys.extend((key, f"quality/results/customers/{run_id}.json",
                         f"quarantine/customers/{run_id}.parquet"))
            frame = pd.DataFrame([{
                "customer_id": customer_id, "account_id": account_id,
                "account_type": "SAVINGS", "balance": 10 if expected_success else -1,
                "account_status": "ACTIVE", "first_name": "A***", "last_name": "B***",
                "email": "***@example.com", "phone": "*******1234",
                "address": "REDACTED" if expected_success else "unmasked address",
                "processed_at": datetime.now(timezone.utc),
            }])
            path = f"s3://banking-lake/{key}"
            frame.to_parquet(path, index=False, storage_options=storage_options())
            os.environ["AIRFLOW_CTX_DAG_RUN_ID"] = run_id
            if expected_success:
                result = run_dq_checks(path)
                assert result["success"] and result["invalid_count"] == 0
            else:
                try:
                    run_dq_checks(path)
                except ValueError as exc:
                    assert run_id in str(exc)
                else:
                    raise AssertionError("Bad Silver record did not fail DQ")
                quarantined = pd.read_parquet(
                    f"s3://banking-lake/quarantine/customers/{run_id}.parquet",
                    storage_options=storage_options(),
                )
                assert len(quarantined) == 1
                assert "balance_non_negative" in quarantined.iloc[0]["_dq_errors"]
            with postgres_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT success, invalid_count FROM dq_run_results WHERE run_id = %s", (run_id,))
                    assert cursor.fetchone() == (expected_success, 0 if expected_success else 1)
        print("DQ good/bad E2E passed")
    finally:
        if original_run_id is None:
            os.environ.pop("AIRFLOW_CTX_DAG_RUN_ID", None)
        else:
            os.environ["AIRFLOW_CTX_DAG_RUN_ID"] = original_run_id
        with postgres_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM dq_run_results WHERE run_id = ANY(%s)", (run_ids,))
                cursor.execute("DELETE FROM core_banking.account WHERE account_id = %s", (account_id,))
                cursor.execute("DELETE FROM core_banking.customer WHERE customer_id = %s", (customer_id,))
        for key in keys:
            s3.delete_object(Bucket="banking-lake", Key=key)


if __name__ == "__main__":
    main()
