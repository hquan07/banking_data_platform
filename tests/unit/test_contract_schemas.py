import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from datasets.schema_mapping import DS1_FEATURES, map_ds1
from shared.alert_contract import normalize_alert_event
from shared.benchmark_contract import normalize_benchmark_event, require_benchmark_run
from shared.contract_error import ContractError, build_dlq_envelope, payload_fingerprint
from shared.payment_contract import normalize_payment_event
from shared.transfer_contract import normalize_transfer_event


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "shared/contracts/v1"
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures/contracts/v1"


def validate(name, payload):
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)


@pytest.mark.parametrize("schema_name,fixture_name", [
    ("payment-event.json", "payment.valid.json"),
    ("transfer-event.json", "transfer.valid.json"),
    ("benchmark-event.json", "benchmark.valid.json"),
    ("alert-envelope.json", "alert.valid.json"),
])
def test_valid_contract_fixtures(schema_name, fixture_name):
    validate(schema_name, json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8")))


@pytest.mark.parametrize("schema_name,fixture_name", [
    ("payment-event.json", "payment.invalid.json"),
    ("transfer-event.json", "transfer.invalid.json"),
    ("benchmark-event.json", "benchmark.invalid.json"),
    ("alert-envelope.json", "alert.invalid.json"),
])
def test_invalid_contract_fixtures(schema_name, fixture_name):
    with pytest.raises(ValidationError):
        validate(schema_name, json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8")))


def payment():
    return {
        "schema_version": 1, "event_id": "event-1", "trace_id": "trace-1",
        "payment_id": "payment-1", "customer_id": "customer-1", "account_id": "account-1",
        "merchant_id": "merchant-1", "amount": 12.34, "currency": "USD",
        "payment_method": "CARD", "channel": "ONLINE", "location": "VN",
        "device_id": "device-1", "timestamp": "2026-10-07T05:00:00Z", "status": "CREATED",
    }


def transfer():
    return {
        "schema_version": 1, "event_id": "transfer-1", "trace_id": "trace-1",
        "from_account_id": "A", "to_account_id": "B", "amount": "12.50",
        "currency": "USD", "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def test_runtime_normalizers_publish_schema_valid_events():
    normalized_payment = normalize_payment_event(payment())
    normalized_transfer = normalize_transfer_event(transfer())
    row = {"Time": 42, "Amount": 19.95, "Class": 1}
    row.update({name: index / 10 for index, name in enumerate(DS1_FEATURES)})
    normalized_benchmark = normalize_benchmark_event(map_ds1(row, 7))

    validate("payment-event.json", normalized_payment)
    validate("transfer-event.json", normalized_transfer)
    validate("benchmark-event.json", normalized_benchmark)


def test_alert_validator_and_schema_have_matching_common_fields():
    alert = normalize_alert_event({
        "schema_version": 1, "event_id": "alert-1", "trace_id": "trace-1",
        "run_id": "11111111-1111-4111-8111-111111111111",
        "rule": "LARGE_TRANSACTION", "risk_score": 80, "risk_level": "HIGH",
        "decision": "REVIEW", "amount": 12000,
    })
    validate("alert-envelope.json", alert)


def test_benchmark_consumers_require_a_uuid_run_id():
    row = {"Time": 42, "Amount": 19.95, "Class": 1}
    row.update({name: index / 10 for index, name in enumerate(DS1_FEATURES)})
    benchmark = map_ds1(row, 7)

    with pytest.raises(ContractError, match="invalid_run_id"):
        require_benchmark_run(benchmark)

    benchmark["run_id"] = "11111111-1111-4111-8111-111111111111"
    assert require_benchmark_run(benchmark)["run_id"] == benchmark["run_id"]


def test_contract_error_and_dlq_envelope_never_copy_sensitive_payload():
    raw = b'{"schema_version":2,"trace_id":"trace-safe","account":"secret"}'
    error = ContractError("payment", 1, "unsupported_schema_version", json.loads(raw), "payment-events")
    envelope = build_dlq_envelope(
        error, raw, {"topic": "payment-events", "partition": 2, "offset": 9}, contract="payment",
    )
    assert envelope["trace_id"] == "trace-safe"
    assert envelope["payload_fingerprint"] == payload_fingerprint(raw)
    assert "secret" not in json.dumps(envelope)
    validate("dlq-envelope.json", envelope)


@pytest.mark.parametrize("normalizer,payload", [
    (normalize_payment_event, {**payment(), "schema_version": 2}),
    (normalize_transfer_event, {**transfer(), "amount": -1}),
])
def test_invalid_contracts_raise_structured_error(normalizer, payload):
    with pytest.raises(ContractError) as captured:
        normalizer(payload)
    assert captured.value.payload_fingerprint
    assert captured.value.reason
