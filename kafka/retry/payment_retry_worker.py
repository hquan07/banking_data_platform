"""Replay approved payment retries; commit only after Kafka acknowledges the outcome."""

import json
import os
import sys

from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.structs import OffsetAndMetadata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from shared.payment_contract import normalize_payment_event


def route_retry(payload: bytes) -> tuple[str, str | None, dict]:
    """Return destination topic, partition key and payload for one retry."""
    try:
        envelope = json.loads(payload)
        if not isinstance(envelope, dict) or envelope.get("schema_version") != 1:
            raise ValueError("Unsupported retry envelope")
        if envelope.get("approved") is not True or envelope.get("attempt") != 1:
            raise ValueError("Retry requires explicit approval and first attempt")
        if not isinstance(envelope.get("event"), dict):
            raise ValueError("Retry event must be an object")
        event = normalize_payment_event(envelope.get("event"))
        return "payment-events", event["payment_id"], event
    except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
        return "payment-events-dlq", None, {
            "raw_value": payload.decode("utf-8", errors="replace"),
            "validation_error": f"retry_rejected:{type(exc).__name__}",
            "source_topic": "payment-events-retry",
        }


def main():
    broker = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "banking_kafka:9092")
    consumer = KafkaConsumer(
        "payment-events-retry", bootstrap_servers=broker,
        group_id="payment-retry-worker-v1", auto_offset_reset="earliest",
        enable_auto_commit=False, max_poll_records=100,
    )
    producer = KafkaProducer(
        bootstrap_servers=broker, acks="all",
        value_serializer=lambda item: json.dumps(item, separators=(",", ":")).encode("utf-8"),
    )
    try:
        for message in consumer:
            topic, key, value = route_retry(message.value)
            # A replay after an acknowledgement but before this commit is safe:
            # event_id/payment_id are stable and the payment sinks are idempotent.
            producer.send(topic, key=key.encode() if key else None, value=value).get(timeout=15)
            consumer.commit({TopicPartition(message.topic, message.partition): OffsetAndMetadata(message.offset + 1, "")})
            print(json.dumps({"event": "payment_retry_routed", "topic": topic,
                              "source_partition": message.partition, "source_offset": message.offset}))
    finally:
        producer.close()
        consumer.close()


if __name__ == "__main__":
    main()
