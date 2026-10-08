#!/usr/bin/env python3
"""Replay source dataset rows to Kafka without generating synthetic rows."""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any

from kafka import KafkaProducer

from datasets.readers import iter_source_rows, map_source_row


def _send_json(producer: Any, topic: str, key: str, value: dict[str, Any]) -> Any:
    return producer.send(
        topic,
        key=key.encode("utf-8"),
        value=json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf-8"),
    )


def replay(
    producer: Any,
    dataset_id: str,
    raw_dir: Path,
    rate: float = 50,
    max_events: int = 0,
    start_row: int = 0,
    max_in_flight: int = 500,
) -> dict[str, int | str]:
    if rate < 0 or max_events < 0 or start_row < 0 or max_in_flight <= 0:
        raise ValueError(
            "rate, max_events and start_row must be non-negative; "
            "max_in_flight must be positive"
        )
    published = rejected = scanned = 0
    next_send = time.monotonic()
    pending = deque()

    for row_number, row in iter_source_rows(dataset_id, raw_dir):
        if row_number < start_row:
            continue
        if max_events and scanned >= max_events:
            break
        scanned += 1
        source_key = f"{dataset_id}:{row_number}"
        try:
            event = map_source_row(dataset_id, row_number, row)
            pending.append(_send_json(
                producer, "benchmark-events", event["event_id"], event,
            ))
            published += 1
        except (KeyError, TypeError, ValueError) as exc:
            pending.append(_send_json(producer, "benchmark-events-dlq", source_key, {
                "schema_version": 1,
                "dataset_id": dataset_id,
                "source_row_id": str(row_number),
                "error": str(exc),
            }))
            rejected += 1
        if len(pending) >= max_in_flight:
            pending.popleft().get(timeout=30)
        if rate:
            next_send += 1 / rate
            delay = next_send - time.monotonic()
            if delay > 0:
                time.sleep(delay)

    while pending:
        pending.popleft().get(timeout=30)
    producer.flush(timeout=30)
    return {
        "dataset_id": dataset_id,
        "start_row": start_row,
        "scanned": scanned,
        "published": published,
        "rejected": rejected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=os.environ.get("DATASET_ID", "ds3_paysim"))
    parser.add_argument("--raw-dir", type=Path, default=Path("datasets/raw"))
    parser.add_argument("--bootstrap", default=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "banking_kafka:9092"))
    parser.add_argument("--rate", type=float, default=float(os.environ.get("DATASET_REPLAY_RATE", "50")))
    parser.add_argument("--max-events", type=int, default=int(os.environ.get("DATASET_MAX_EVENTS", "0")))
    parser.add_argument("--start-row", type=int, default=int(os.environ.get("DATASET_START_ROW", "0")))
    parser.add_argument(
        "--max-in-flight", type=int,
        default=int(os.environ.get("DATASET_MAX_IN_FLIGHT", "500")),
    )
    args = parser.parse_args()

    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap,
        acks="all",
        retries=10,
    )
    try:
        summary = replay(
            producer, args.dataset, args.raw_dir, args.rate,
            args.max_events, args.start_row, args.max_in_flight,
        )
    finally:
        producer.close(timeout=30)
    print(json.dumps(summary, sort_keys=True))
    return 1 if summary["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
