"""Opt-in check that invalid Kafka payments land in the DLQ with source metadata."""

import json
import os
import time
import uuid

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
