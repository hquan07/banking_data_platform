"""Opt-in check that invalid Kafka payments land in the DLQ with source metadata."""

import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_E2E") != "1", reason="requires the running Docker Compose stack"
)


def test_malformed_and_unsupported_payment_events_reach_dlq():
    from kafka import KafkaConsumer, KafkaProducer

    suffix = uuid.uuid4().hex
    payloads = {
        f"not-json-{suffix}": "unsupported_schema_version",
        json.dumps({"schema_version": 2, "event_id": f"wrong-version-{suffix}"}): "unsupported_schema_version",
    }
    base_event = {
        "schema_version": 1, "event_id": f"late-{suffix}", "trace_id": f"late-{suffix[:12]}",
        "payment_id": f"LATE_{suffix[:16]}", "customer_id": "C_LATE", "account_id": "A_LATE",
        "merchant_id": "M_LATE", "amount": 10, "currency": "USD",
        "payment_method": "CARD", "channel": "ONLINE", "status": "CREATED",
    }
    payloads[json.dumps({**base_event, "timestamp": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()})] = "event_too_late"
    payloads[json.dumps({**base_event, "event_id": f"future-{suffix}",
                         "timestamp": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()})] = "event_in_future"
    consumer = KafkaConsumer(
        "payment-events-dlq",
        bootstrap_servers="localhost:9094",
        group_id=f"e2e-dlq-{suffix}",
        auto_offset_reset="latest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    producer = KafkaProducer(bootstrap_servers="localhost:9094", acks="all")
    try:
        consumer.poll(timeout_ms=1000)  # establish the current end offset
        for payload in payloads:
            producer.send("payment-events", key=suffix.encode(), value=payload.encode()).get(timeout=10)

        found = set()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline and len(found) < len(payloads):
            for messages in consumer.poll(timeout_ms=2000).values():
                for message in messages:
                    value = message.value
                    if value.get("raw_value") in payloads:
                        assert value["validation_error"] == payloads[value["raw_value"]]
                        assert value["source_topic"] == "payment-events"
                        assert isinstance(value["source_partition"], int)
                        assert isinstance(value["source_offset"], int)
                        found.add(value["raw_value"])

        assert found == set(payloads), f"DLQ missing {set(payloads) - found}"
    finally:
        producer.close()
        consumer.close()
