"""Opt-in HTTP gateway -> canonical Kafka topics integration check."""

import json
import os
import time
import uuid
from datetime import datetime, timezone

import pytest
import requests


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_E2E") != "1", reason="requires the running Docker Compose stack"
)


def test_gateway_auth_validation_and_topic_routing():
    from kafka import KafkaConsumer

    gateway = os.getenv("LIVE_GATEWAY_URL", "http://127.0.0.1:8085")
    api_key = os.getenv("LIVE_INGESTION_API_KEY", "integration-live-key-change-me")
    suffix = uuid.uuid4().hex[:16]
    payment_id = f"E2E_GATEWAY_PAY_{suffix}"
    from_account = f"E2E_GATEWAY_FROM_{suffix}"
    payment = {
        "schema_version": 1,
        "event_id": f"e2e-gateway-payment-{suffix}",
        "trace_id": f"e2e-gateway-trace-{suffix}",
        "payment_id": payment_id,
        "customer_id": f"E2E_GATEWAY_CUS_{suffix}",
        "account_id": f"E2E_GATEWAY_ACC_{suffix}",
        "merchant_id": "E2E_GATEWAY_MERCHANT",
        "amount": 125.50,
        "currency": "USD",
        "payment_method": "CARD",
        "channel": "ONLINE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS",
    }
    transfer = {
        "schema_version": 1,
        "event_id": f"e2e-gateway-transfer-{suffix}",
        "trace_id": f"e2e-gateway-trace-{suffix}",
        "from_account_id": from_account,
        "to_account_id": f"E2E_GATEWAY_TO_{suffix}",
        "amount": "250.00",
        "currency": "USD",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    consumer = KafkaConsumer(
        "payment-events", "transfer-events",
        bootstrap_servers="localhost:9094",
        group_id=f"e2e-live-gateway-{suffix}",
        auto_offset_reset="latest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    try:
        consumer.poll(timeout_ms=1000)
        unauthorized = requests.post(f"{gateway}/v1/events/payments", json=payment, timeout=10)
        assert unauthorized.status_code == 401
        invalid = requests.post(
            f"{gateway}/v1/events/payments", json={},
            headers={"X-Live-Source-Key": api_key}, timeout=10,
        )
        assert invalid.status_code == 422

        headers = {"X-Live-Source-Key": api_key, "X-Source-System": "integration-test"}
        payment_response = requests.post(
            f"{gateway}/v1/events/payments", json=payment, headers=headers, timeout=20,
        )
        transfer_response = requests.post(
            f"{gateway}/v1/events/transfers", json=transfer, headers=headers, timeout=20,
        )
        assert payment_response.status_code == transfer_response.status_code == 202

        found = set()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and len(found) < 2:
            for messages in consumer.poll(timeout_ms=1000).values():
                for message in messages:
                    if message.topic == "payment-events" and message.key == payment_id.encode():
                        assert message.value["event_id"] == payment["event_id"]
                        assert message.value["source_system"] == "integration-test"
                        found.add("payment")
                    if message.topic == "transfer-events" and message.key == from_account.encode():
                        assert message.value["event_id"] == transfer["event_id"]
                        assert message.value["source_system"] == "integration-test"
                        found.add("transfer")
        assert found == {"payment", "transfer"}
    finally:
        consumer.close()
