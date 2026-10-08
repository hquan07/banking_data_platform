import json
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

module_path = Path(__file__).resolve().parents[2] / "kafka/retry/payment_retry_worker.py"
spec = importlib.util.spec_from_file_location("payment_retry_worker", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
route_retry = module.route_retry


def valid_payment():
    return {
        "schema_version": 1, "event_id": "retry-event-1", "trace_id": "retry-trace-1",
        "payment_id": "retry-payment-1", "customer_id": "C1", "account_id": "A1",
        "merchant_id": "M1", "amount": 12.5, "currency": "USD",
        "payment_method": "CARD", "channel": "ONLINE", "device_id": "D1",
        "location": "VN", "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "CREATED",
    }


def test_approved_retry_replays_stable_event():
    envelope = {"schema_version": 1, "approved": True, "attempt": 1, "event": valid_payment()}
    topic, key, event = route_retry(json.dumps(envelope).encode())
    assert (topic, key) == ("payment-events", "retry-payment-1")
    assert event["event_id"] == "retry-event-1"


def test_unapproved_or_malformed_retry_goes_to_dlq():
    for payload in (b"not json", json.dumps({"schema_version": 1, "approved": False, "attempt": 1,
                                              "event": valid_payment()}).encode()):
        topic, key, error = route_retry(payload)
        assert (topic, key) == ("payment-events-dlq", None)
        assert error["source_topic"] == "payment-events-retry"
