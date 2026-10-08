"""Deterministic, explicitly synthetic transfer scenarios for the AML demo.

Print JSONL by default. Publishing requires --publish and is refused in
APP_MODE=production. No payment event is repurposed as a transfer.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.transfer_contract import normalize_transfer_event


def build_scenario(run_id: str, scenario: str, start_time: datetime) -> list[dict]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", run_id):
        raise ValueError("run_id must be 1-32 letters, digits, _ or -")
    if scenario not in {"cycle3", "cycle4", "cycle5", "low_amount"}:
        raise ValueError("unsupported scenario")
    if start_time.tzinfo is None:
        raise ValueError("start_time must be timezone-aware")
    count = 3 if scenario == "low_amount" else int(scenario[-1])
    accounts = [f"DEMO_{run_id}_{scenario}_A{i}" for i in range(count)]
    events = []
    for index in range(count):
        events.append(normalize_transfer_event({
            "schema_version": 1,
            "event_id": f"demo-transfer-{run_id}-{scenario}-{index}",
            "trace_id": f"demo-trace-{run_id}-{scenario}",
            "from_account_id": accounts[index],
            "to_account_id": accounts[(index + 1) % count],
            "amount": "100.00" if scenario == "low_amount" and index == 1 else "5000.00",
            "currency": "USD",
            "timestamp": (start_time + timedelta(seconds=index)).isoformat(),
            "data_origin": "synthetic_demo",
            "scenario": scenario,
        }))
    return events


def build_all(run_id: str, start_time: datetime) -> list[dict]:
    return [event for scenario in ("cycle3", "cycle4", "cycle5", "low_amount")
            for event in build_scenario(run_id, scenario, start_time)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Unique ID to avoid mixing repeated demo runs")
    parser.add_argument("--scenario", choices=("all", "cycle3", "cycle4", "cycle5", "low_amount"), default="all")
    parser.add_argument("--start-time", help="ISO-8601 timestamp; defaults to current UTC time")
    parser.add_argument("--publish", action="store_true", help="Send to Kafka instead of printing JSONL")
    parser.add_argument("--bootstrap", default="localhost:9094")
    args = parser.parse_args()
    start = datetime.fromisoformat(args.start_time.replace("Z", "+00:00")) if args.start_time else datetime.now(timezone.utc)
    events = build_all(args.run_id, start) if args.scenario == "all" else build_scenario(args.run_id, args.scenario, start)
    if not args.publish:
        for event in events:
            print(json.dumps(event, sort_keys=True))
        return
    if os.environ.get("APP_MODE", "integration").lower() == "production":
        parser.error("synthetic transfer publishing is forbidden in APP_MODE=production")
    from kafka import KafkaProducer
    producer = KafkaProducer(bootstrap_servers=args.bootstrap, acks="all", retries=10)
    try:
        for event in events:
            producer.send("transfer-events", key=event["from_account_id"].encode(),
                          value=json.dumps(event).encode()).get(timeout=20)
    finally:
        producer.close()
    print(f"Published {len(events)} synthetic transfer events for {args.run_id}")


if __name__ == "__main__":
    main()
