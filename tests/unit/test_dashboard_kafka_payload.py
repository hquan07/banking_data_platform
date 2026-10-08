"""Payment poison pills must not stop the dashboard's Kafka consumer."""

import json

import pytest

from dashboard.backend.services.kafka_payload import decode_message


def test_invalid_payment_payloads_are_skipped():
    assert decode_message("payment-events", b"not-json") is None
    assert decode_message("payment-events", b"[]") is None
    assert decode_message("payment-events", b'{"schema_version": 2}') is None


def test_valid_payment_is_decoded():
    event = {"schema_version": 1, "payment_id": "p-1"}
    assert decode_message("payment-events", json.dumps(event).encode()) == event


def test_invalid_alert_remains_a_retryable_error():
    with pytest.raises(json.JSONDecodeError):
        decode_message("fraud-events", b"not-json")
    with pytest.raises(ValueError, match="JSON object"):
        decode_message("aml-events", b"[]")
