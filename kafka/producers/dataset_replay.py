#!/usr/bin/env python3
"""Replay source dataset rows to Kafka without generating synthetic rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any

from kafka import KafkaProducer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from datasets.readers import iter_source_rows, map_source_row
from shared.contract_error import build_dlq_envelope

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_control import ReplayCancelled, ReplayRunControl


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
    run_id: str,
    rate: float = 50,
    max_events: int = 0,
    start_row: int = 0,
    max_in_flight: int = 500,
    controller: Any | None = None,
    control_interval: int = 100,
) -> dict[str, int | str]:
    try:
        run_id = str(uuid.UUID(run_id))
    except ValueError:
        raise ValueError("run_id must be a UUID") from None
    if rate < 0 or max_events < 0 or start_row < 0 or max_in_flight <= 0 or control_interval <= 0:
        raise ValueError(
            "rate, max_events and start_row must be non-negative; "
            "max_in_flight and control_interval must be positive"
        )
    replay_started = time.monotonic()
    published = rejected = scanned = 0
    next_send = time.monotonic()
    pending = deque()
    acknowledged = []
    cancelled = False

    def acknowledge_one():
        future, source_row, outcome = pending.popleft()
        metadata = future.get(timeout=30)
        acknowledged.append({
            "topic": metadata.topic,
            "partition": metadata.partition,
            "offset": metadata.offset,
            "source_row": source_row,
            "outcome": outcome,
        })

    def checkpoint(check_control=False):
        if controller is not None and acknowledged:
            controller.record_progress(acknowledged)
        acknowledged.clear()
        if controller is not None and check_control:
            controller.await_runnable()

    for row_number, row in iter_source_rows(dataset_id, raw_dir):
        if row_number < start_row:
            continue
        if max_events and scanned >= max_events:
            break
        scanned += 1
        source_key = f"{dataset_id}:{row_number}"
        try:
            event = map_source_row(dataset_id, row_number, row)
            event["run_id"] = run_id
            pending.append(_send_json(
                producer, "benchmark-events", f"{run_id}:{event['event_id']}", event,
            ))
            pending[-1] = (pending[-1], row_number, "published")
            published += 1
        except (KeyError, TypeError, ValueError) as exc:
            envelope = build_dlq_envelope(
                exc,
                row,
                {"topic": "dataset-replay", "partition": None, "offset": row_number},
                contract="benchmark",
            )
            envelope["run_id"] = run_id
            pending.append(_send_json(
                producer,
                "benchmark-events-dlq",
                f"{run_id}:{source_key}",
                envelope,
            ))
            pending[-1] = (pending[-1], row_number, "rejected")
            rejected += 1
        if len(pending) >= max_in_flight:
            acknowledge_one()
        if scanned % control_interval == 0:
            while pending:
                acknowledge_one()
            try:
                checkpoint(check_control=True)
            except ReplayCancelled:
                cancelled = True
                break
        if rate:
            next_send += 1 / rate
            delay = next_send - time.monotonic()
            if delay > 0:
                time.sleep(delay)

    while pending:
        acknowledge_one()
    if cancelled:
        checkpoint()
    else:
        try:
            checkpoint(check_control=True)
        except ReplayCancelled:
            cancelled = True
    producer.flush(timeout=30)
    elapsed_seconds = time.monotonic() - replay_started
    return {
        "dataset_id": dataset_id,
        "run_id": run_id,
        "start_row": start_row,
        "scanned": scanned,
        "published": published,
        "rejected": rejected,
        "cancelled": cancelled,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "observed_rate_eps": round(scanned / elapsed_seconds, 3) if elapsed_seconds else 0,
    }


def source_path(dataset_id: str, raw_dir: Path) -> Path:
    paths = {
        "ds1_creditcard": raw_dir / "creditcard/creditcard.csv",
        "ds3_paysim": raw_dir / "paysim/PS_20174392719_1491204439457_log.csv",
        "ds4_baf": raw_dir / "bank-account-fraud/Base.csv",
    }
    try:
        return paths[dataset_id]
    except KeyError:
        raise ValueError(f"unknown_dataset_id:{dataset_id}") from None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=os.environ.get("DATASET_ID", "ds3_paysim"))
    parser.add_argument("--raw-dir", type=Path, default=Path("datasets/raw"))
    parser.add_argument("--bootstrap", default=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "banking_kafka:9092"))
    parser.add_argument("--rate", type=float, default=float(os.environ.get("DATASET_REPLAY_RATE", "50")))
    parser.add_argument("--max-events", type=int, default=int(os.environ.get("DATASET_MAX_EVENTS", "0")))
    parser.add_argument("--start-row", type=int, default=int(os.environ.get("DATASET_START_ROW", "0")))
    parser.add_argument("--run-id", default=os.environ.get("PIPELINE_RUN_ID"))
    parser.add_argument("--dataset-version", default=os.environ.get("DATASET_VERSION"))
    parser.add_argument(
        "--control-interval", type=int,
        default=int(os.environ.get("DATASET_CONTROL_INTERVAL", "100")),
    )
    parser.add_argument(
        "--max-in-flight", type=int,
        default=int(os.environ.get("DATASET_MAX_IN_FLIGHT", "500")),
    )
    args = parser.parse_args()

    path = source_path(args.dataset, args.raw_dir)
    dataset_hash = sha256_file(path)
    dataset_version = args.dataset_version or f"sha256:{dataset_hash[:16]}"
    requested_end = args.start_row + args.max_events if args.max_events else None
    controller = ReplayRunControl.connect(args.run_id or None, {
        "dataset_id": args.dataset,
        "dataset_version": dataset_version,
        "dataset_hash": dataset_hash,
        "evaluator_version": "benchmark-rules-v2",
        "requested_rate": args.rate,
        "requested_start_offset": args.start_row,
        "requested_end_offset": requested_end,
    })
    effective_start_row = controller.resume_row(controller.requested_start_offset)
    effective_max_events = args.max_events
    if controller.requested_end_offset is not None:
        remaining = max(0, controller.requested_end_offset - effective_start_row)
        effective_max_events = min(args.max_events, remaining) if args.max_events else remaining

    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap,
        acks="all",
        retries=10,
    )
    try:
        summary = replay(
            producer, args.dataset, args.raw_dir, controller.run_id, args.rate,
            effective_max_events, effective_start_row, args.max_in_flight,
            controller=controller, control_interval=args.control_interval,
        )
        if not summary["cancelled"]:
            controller.complete()
    finally:
        producer.close(timeout=30)
        controller.close()
    print(json.dumps(summary, sort_keys=True))
    return 1 if summary["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
