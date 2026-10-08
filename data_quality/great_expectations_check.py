"""Run the customer Silver expectation suite and persist each run's evidence."""

import json
import os
import re
import uuid
from datetime import datetime, timezone

import boto3
import pandas as pd
import psycopg2

from customer_expectations import evaluate_customer_silver


BUCKET = "banking-lake"


def storage_options():
    return {
        "key": os.environ["MINIO_ROOT_USER"],
        "secret": os.environ["MINIO_ROOT_PASSWORD"],
        "client_kwargs": {"endpoint_url": os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")},
    }


def postgres_connection():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5433")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def safe_run_id():
    raw = os.environ.get("AIRFLOW_CTX_DAG_RUN_ID") or uuid.uuid4().hex
    return re.sub(r"[^A-Za-z0-9_.-]", "_", raw)[:120]


def run_dq_checks(data_path):
    run_id = safe_run_id()
    frame = pd.read_parquet(data_path, storage_options=storage_options())
    with postgres_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT account_id FROM core_banking.account")
            reference_accounts = {row[0] for row in cursor.fetchall()}

    summary, invalid = evaluate_customer_silver(frame, reference_accounts)
    result = {
        **summary, "run_id": run_id, "source_path": data_path,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if not invalid.empty:
        quarantine_path = f"s3://{BUCKET}/quarantine/customers/{run_id}.parquet"
        invalid.to_parquet(quarantine_path, index=False, storage_options=storage_options())
        result["quarantine_path"] = quarantine_path

    s3 = boto3.client(
        "s3", endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        region_name="us-east-1",
    )
    s3.put_object(
        Bucket=BUCKET, Key=f"quality/results/customers/{run_id}.json",
        Body=json.dumps(result).encode("utf-8"), ContentType="application/json",
    )
    with postgres_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO dq_run_results
                    (run_id, source_path, row_count, invalid_count, duplicate_rate, success,
                     checks, quarantine_path)
                   VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                   ON CONFLICT (run_id) DO UPDATE SET
                     source_path = EXCLUDED.source_path, row_count = EXCLUDED.row_count,
                     invalid_count = EXCLUDED.invalid_count, duplicate_rate = EXCLUDED.duplicate_rate,
                     success = EXCLUDED.success, checks = EXCLUDED.checks,
                     quarantine_path = EXCLUDED.quarantine_path, checked_at = NOW()""",
                (run_id, data_path, summary["row_count"], summary["invalid_count"],
                 summary["duplicate_rate"], summary["success"],
                 json.dumps(summary["checks"]), result.get("quarantine_path")),
            )
    print(json.dumps({"run_id": run_id, "success": summary["success"],
                      "invalid_count": summary["invalid_count"]}))
    if not summary["success"]:
        raise ValueError(f"Customer Silver DQ failed for run {run_id}; see quarantine_path")
    return result


if __name__ == "__main__":
    run_dq_checks(os.environ.get("DQ_DATA_PATH", "s3://banking-lake/silver/customers/"))
