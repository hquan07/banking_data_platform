"""Approved retry is acknowledged into payment-events with unchanged IDs."""

import json
import os
import time
import uuid
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_E2E") != "1", reason="requires live Compose stack")


def test_approved_payment_retry_reaches_primary_topic():
    from kafka import KafkaConsumer, KafkaProducer
    from shared.payment_contract import normalize_payment_event

    suffix = uuid.uuid4().hex[:12]
    event = normalize_payment_event({
        "schema_version": 1, "event_id": f"retry-e2e-{suffix}",
        "trace_id": f"retry-trace-{suffix}", "payment_id": f"RETRY_E2E_{suffix}",
        "customer_id": f"C_{suffix}", "account_id": f"A_{suffix}",
        "merchant_id": "RETRY_TEST", "amount": 10, "currency": "USD",
        "payment_method": "CARD", "channel": "ONLINE", "location": "VN",
        "device_id": f"D_{suffix}", "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "CREATED",
    })
    consumer = KafkaConsumer(
        "payment-events", bootstrap_servers="localhost:9094",
        group_id=f"retry-e2e-{suffix}", auto_offset_reset="latest",
        enable_auto_commit=False, value_deserializer=lambda item: json.loads(item),
    )
    producer = KafkaProducer(
        bootstrap_servers="localhost:9094", acks="all",
        value_serializer=lambda item: json.dumps(item).encode(),
    )
    try:
        consumer.poll(timeout_ms=1000)
        producer.send("payment-events-retry", key=event["payment_id"].encode(), value={
            "schema_version": 1, "approved": True, "attempt": 1,
            "reason": "automated E2E approval fixture", "event": event,
        }).get(timeout=10)
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            for messages in consumer.poll(timeout_ms=1000).values():
                if any(message.value.get("event_id") == event["event_id"] for message in messages):
                    return
        pytest.fail("Approved retry was not replayed to payment-events")
    finally:
        producer.close()
        consumer.close()
