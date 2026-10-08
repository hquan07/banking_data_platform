from datetime import datetime, timezone

import pandas as pd

from data_quality.customer_expectations import evaluate_customer_silver


NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


def good_row(**changes):
    row = {
        "customer_id": "CUS_1", "account_id": "ACC_1", "account_type": "SAVINGS",
        "balance": 100, "account_status": "ACTIVE", "first_name": "A***",
        "last_name": "B***", "email": "***@example.com", "phone": "*******1234",
        "address": "REDACTED", "processed_at": NOW,
    }
    return {**row, **changes}


def test_valid_silver_record_passes():
    summary, invalid = evaluate_customer_silver(pd.DataFrame([good_row()]), {"ACC_1"}, NOW)
    assert summary["success"] and summary["invalid_count"] == 0
    assert invalid.empty


def test_invalid_records_are_quarantined_with_specific_failures():
    frame = pd.DataFrame([
        good_row(),
        good_row(customer_id="CUS_2", account_id="ACC_2", balance=-2,
                 account_status="UNKNOWN", email="private@example.com", address="123 Street"),
    ])
    summary, invalid = evaluate_customer_silver(frame, {"ACC_1"}, NOW)
    assert not summary["success"] and summary["invalid_count"] == 1
    assert invalid.iloc[0]["account_id"] == "ACC_2"
    for rule in ("balance_non_negative", "account_status_enum", "email_masked",
                 "address_masked", "account_referential_integrity"):
        assert rule in invalid.iloc[0]["_dq_errors"]


def test_duplicate_account_rate_and_timestamp():
    frame = pd.DataFrame([
        good_row(),
        good_row(customer_id="CUS_2", processed_at="not-a-timestamp"),
    ])
    summary, invalid = evaluate_customer_silver(frame, {"ACC_1"}, NOW)
    assert summary["duplicate_rate"] == 1.0
    assert summary["checks"]["processed_at_valid"]["failed_rows"] == 1
    assert len(invalid) == 2
