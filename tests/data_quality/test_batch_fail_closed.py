"""Batch I/O failures must reach Airflow instead of appearing successful."""

from unittest.mock import MagicMock

import pytest

from batch.customer_pipeline import write_silver
from batch.warehouse_pipeline import read_silver, write_clickhouse, write_postgres


def test_silver_write_failure_is_not_swallowed():
    frame = MagicMock()
    frame.write.mode.return_value.parquet.side_effect = OSError("MinIO unavailable")

    with pytest.raises(OSError, match="MinIO unavailable"):
        write_silver(frame, "s3a://banking-lake/silver/customers/")


def test_silver_read_failure_is_not_swallowed():
    spark = MagicMock()
    spark.read.parquet.side_effect = OSError("Silver missing")

    with pytest.raises(OSError, match="Silver missing"):
        read_silver(spark, "s3a://banking-lake/silver/customers/")


def test_gold_write_failure_is_not_swallowed():
    frame = MagicMock()
    frame.write.jdbc.side_effect = OSError("ClickHouse unavailable")

    with pytest.raises(OSError, match="ClickHouse unavailable"):
        write_clickhouse(frame, "jdbc:clickhouse://localhost:8123/banking_warehouse", {})


def test_postgres_gold_write_failure_is_not_swallowed():
    frame = MagicMock()
    frame.write.jdbc.side_effect = OSError("PostgreSQL unavailable")

    with pytest.raises(OSError, match="PostgreSQL unavailable"):
        write_postgres(frame, "jdbc:postgresql://localhost:5433/banking_data_platform", {})
