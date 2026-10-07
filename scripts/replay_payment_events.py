"""Validate corrected payment JSONL and optionally publish it to Kafka.

Extract raw_value from payment-events-dlq, correct invalid events in a JSONL
file, then run this script. Keep event_id/payment_id unchanged for retries.
"""

import argparse
import json
import os

from shared.payment_contract import PAYMENT_TOPIC, normalize_payment_event


def load_events(path):
    with open(path, encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                yield normalize_payment_event(json.loads(line))
            except (ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid event on line {line_number}: {exc}") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSONL file containing corrected payment events")
    parser.add_argument("--publish", action="store_true", help="Send validated events to Kafka")
    args = parser.parse_args()
    count = sum(1 for _ in load_events(args.input))
    print(f"Validated {count} events")
    if not args.publish:
        return

    from kafka import KafkaProducer
    producer = KafkaProducer(
        bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"),
        acks="all",
        retries=10,
        value_serializer=lambda event: json.dumps(event).encode("utf-8"),
    )
    try:
        for event in load_events(args.input):
            producer.send(PAYMENT_TOPIC, key=event["payment_id"].encode("utf-8"), value=event).get(timeout=10)
    finally:
        producer.close()
    print(f"Published {count} events to {PAYMENT_TOPIC}")


if __name__ == "__main__":
    main()
