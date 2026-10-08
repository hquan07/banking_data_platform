import pytest

from datasets.schema_mapping import (
    DS1_FEATURES,
    DS4_FEATURES,
    map_ds1,
    map_ds3,
    map_ds4,
)
from shared.benchmark_contract import normalize_benchmark_event


def test_ds1_preserves_features_without_fabricating_identity():
    row = {"Time": 42, "Amount": 19.95, "Class": 1}
    row.update({name: index / 10 for index, name in enumerate(DS1_FEATURES)})
    event = map_ds1(row, 7)

    assert event["event_id"] == "ds1_creditcard:7"
    assert len(event["payload"]["pca_features"]) == 28
    assert "account_id" not in event["payload"]
    assert "currency" not in event["payload"]
    assert event["ground_truth"]["is_fraud"] is True


def test_ds3_preserves_all_transaction_types_and_synthetic_provenance():
    event = map_ds3({
        "step": 3,
        "type": "CASH_IN",
        "amount": 100,
        "nameOrig": "C1",
        "oldbalanceOrg": 10,
        "newbalanceOrig": 110,
        "nameDest": "C2",
        "oldbalanceDest": 50,
        "newbalanceDest": 0,
        "isFraud": 0,
        "isFlaggedFraud": 0,
    }, 12)

    assert event["payload"]["transaction_type"] == "CASH_IN"
    assert event["provenance"]["source_kind"] == "synthetic_simulation"
    assert normalize_benchmark_event(event) == event


def test_ds4_maps_application_features_without_payment_fields():
    row = {name: 0 for name in DS4_FEATURES}
    row.update({"month": 6, "fraud_bool": 1, "source": "INTERNET", "device_os": "windows"})
    event = map_ds4(row, 99)

    assert event["event_type"] == "account_application"
    assert event["event_time"]["unit"] == "month_index"
    assert len(event["payload"]["features"]) == len(DS4_FEATURES)
    assert "amount" not in event["payload"]


def test_contract_rejects_fabricated_calendar_origin():
    row = {"Time": 42, "Amount": 19.95, "Class": 0}
    row.update({name: 0 for name in DS1_FEATURES})
    event = map_ds1(row, 1)
    event["event_time"]["origin"] = "2026-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="origin"):
        normalize_benchmark_event(event)
