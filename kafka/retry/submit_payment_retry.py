"""Submit one corrected, approved payment event for a single retry attempt."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaProducer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from shared.payment_contract import normalize_payment_event


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-json", type=Path, required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--approve", action="store_true", required=True)
    args = parser.parse_args()
    event = normalize_payment_event(json.loads(args.event_json.read_text()))
    envelope = {
        "schema_version": 1, "approved": True, "attempt": 1,
        "reason": args.reason, "submitted_at": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    producer = KafkaProducer(
        bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"),
        acks="all", value_serializer=lambda item: json.dumps(item).encode("utf-8"),
    )
    try:
        result = producer.send("payment-events-retry", key=event["payment_id"].encode(), value=envelope).get(timeout=15)
        print(json.dumps({"topic": result.topic, "partition": result.partition,
                          "offset": result.offset, "event_id": event["event_id"]}))
    finally:
        producer.close()


if __name__ == "__main__":
    main()
