"""Opt-in live check for Kafka -> Spark -> PostgreSQL/ClickHouse/fraud Kafka."""

import json
import os
import time
import uuid
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote
from base64 import b64encode

import pytest

from shared.payment_contract import normalize_payment_event


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_E2E") != "1", reason="requires the running Docker Compose stack"
)


def test_payment_reaches_both_stores_and_fraud_topic():
    from dotenv import load_dotenv
    from kafka import KafkaConsumer, KafkaProducer
    import psycopg2

    load_dotenv()
    suffix = uuid.uuid4().hex[:16]
    payment_id = f"E2E_{suffix}"
    event = normalize_payment_event({
        "schema_version": 1,
        "event_id": f"e2e-event-{suffix}",
        "trace_id": f"e2e-trace-{suffix}",
        "payment_id": payment_id,
        "customer_id": f"E2E_CUS_{suffix}",
        "account_id": f"E2E_ACC_{suffix}",
        "merchant_id": "E2E_MERCHANT",
        "amount": 20000.00,
        "currency": "USD",
        "payment_method": "CARD",
        "channel": "ONLINE",
        "device_id": f"E2E_DEV_{suffix}",
        "location": "VN",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "CREATED",
    })

    consumer = KafkaConsumer(
        "fraud-events",
        bootstrap_servers="localhost:9094",
        group_id=f"e2e-{suffix}",
        auto_offset_reset="latest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    producer = KafkaProducer(
        bootstrap_servers="localhost:9094",
        acks="all",
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    try:
        consumer.poll(timeout_ms=1000)  # establish the current end offset
        producer.send("payment-events", key=payment_id.encode(), value=event).get(timeout=10)
        print(f"E2E payment_id={payment_id}")

        postgres_found = clickhouse_found = fraud_found = False
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if not postgres_found:
                with psycopg2.connect(
                    host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
                    user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
                ) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT count(*) FROM core_banking.payment_event WHERE payment_id = %s AND event_id = %s",
                            (payment_id, event["event_id"]),
                        )
                        postgres_found = cursor.fetchone()[0] == 1

            if not clickhouse_found:
                credentials = b64encode(
                    f'{os.environ["CLICKHOUSE_USER"]}:{os.environ["CLICKHOUSE_PASSWORD"]}'.encode()
                ).decode()
                query = (
                    "SELECT count() FROM payment_events FINAL "
                    f"WHERE payment_id = '{payment_id}' AND event_id = '{event['event_id']}'"
                )
                request = Request(
                    f'http://localhost:8123/?database={quote(os.environ["CLICKHOUSE_DB"])}',
                    data=query.encode(), headers={"Authorization": f"Basic {credentials}"},
                )
                with urlopen(request, timeout=10) as response:
                    clickhouse_found = response.read().strip() == b"1"

            if not fraud_found:
                for messages in consumer.poll(timeout_ms=2000).values():
                    fraud_found = fraud_found or any(
                        message.value.get("payment_id") == payment_id
                        and message.value.get("rule") == "LARGE_TRANSACTION"
                        for message in messages
                    )

            if postgres_found and clickhouse_found and fraud_found:
                return
            time.sleep(2)

        pytest.fail(
            f"E2E {payment_id}: postgres={postgres_found}, "
            f"clickhouse={clickhouse_found}, fraud={fraud_found}"
        )
    finally:
        producer.close()
        consumer.close()
