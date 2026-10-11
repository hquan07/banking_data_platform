"""Compare a bounded Kafka snapshot with PostgreSQL and ClickHouse by payment ID."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.payment_contract import normalize_payment_event
from shared.reconciliation.payment import (
    compare_records,
    partition_quarantined_events,
    payment_store_outcome,
    snapshot_window_key,
)
from shared.reconciliation.persistence import persist_outcome


def kafka_snapshot(tail_per_partition):
    from kafka import KafkaConsumer, TopicPartition

    consumer = KafkaConsumer(
        bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"),
        enable_auto_commit=False,
        group_id=None,
        consumer_timeout_ms=5000,
    )
    try:
        partitions = consumer.partitions_for_topic("payment-events")
        if not partitions:
            raise RuntimeError("payment-events topic does not exist")
        assigned = [TopicPartition("payment-events", number) for number in sorted(partitions)]
        consumer.assign(assigned)
        ends = consumer.end_offsets(assigned)
        for partition in assigned:
            consumer.seek(partition, max(0, ends[partition] - tail_per_partition))
        events = []
        invalid = 0
        deadline = time.monotonic() + 30
        while any(consumer.position(partition) < ends[partition] for partition in assigned):
            if time.monotonic() > deadline:
                raise TimeoutError("Could not read Kafka snapshot within 30 seconds")
            for partition, records in consumer.poll(timeout_ms=1000).items():
                for record in records:
                    if record.offset >= ends[partition]:
                        continue
                    try:
                        event = normalize_payment_event(json.loads(record.value))
                        event["_source"] = {
                            "topic": record.topic,
                            "partition": record.partition,
                            "offset": record.offset,
                        }
                        events.append(event)
                    except (ValueError, TypeError):
                        invalid += 1
        return events, invalid
    finally:
        consumer.close()


def dlq_source_snapshot(tail_per_partition):
    """Return exact payment-events source offsets proven quarantined by Spark."""
    from kafka import KafkaConsumer, TopicPartition

    consumer = KafkaConsumer(
        bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"),
        enable_auto_commit=False,
        group_id=None,
        consumer_timeout_ms=5000,
    )
    try:
        partitions = consumer.partitions_for_topic("payment-events-dlq")
        if not partitions:
            raise RuntimeError("payment-events-dlq topic does not exist")
        assigned = [TopicPartition("payment-events-dlq", number) for number in sorted(partitions)]
        consumer.assign(assigned)
        ends = consumer.end_offsets(assigned)
        for partition in assigned:
            consumer.seek(partition, max(0, ends[partition] - tail_per_partition))
        sources = set()
        deadline = time.monotonic() + 30
        while any(consumer.position(partition) < ends[partition] for partition in assigned):
            if time.monotonic() > deadline:
                raise TimeoutError("Could not read payment DLQ snapshot within 30 seconds")
            for partition, records in consumer.poll(timeout_ms=1000).items():
                for record in records:
                    if record.offset >= ends[partition]:
                        continue
                    try:
                        value = json.loads(record.value)
                        source = value.get("source")
                        if source is None:
                            source = {
                                "topic": value["source_topic"],
                                "partition": value["source_partition"],
                                "offset": value["source_offset"],
                            }
                        identity = (
                            source["topic"],
                            int(source["partition"]),
                            int(source["offset"]),
                        )
                    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                        continue
                    if identity[0] == "payment-events":
                        sources.add(identity)
        return sources
    finally:
        consumer.close()


def query_stores(payment_ids):
    import psycopg2
    from clickhouse_driver import Client

    postgres = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5433")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=10,
    )
    try:
        clickhouse = Client(
            host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
            port=int(os.environ.get("CLICKHOUSE_PORT", "9002")),
            database=os.environ["CLICKHOUSE_DB"],
            user=os.environ["CLICKHOUSE_USER"],
            password=os.environ["CLICKHOUSE_PASSWORD"],
            send_receive_timeout=10,
        )
    except Exception:
        postgres.close()
        raise
    pg_rows, ch_rows = [], []
    try:
        for start in range(0, len(payment_ids), 500):
            ids = payment_ids[start:start + 500]
            with postgres.cursor() as cursor:
                cursor.execute(
                    "SELECT payment_id, event_id FROM core_banking.payment_event WHERE payment_id = ANY(%s)",
                    (ids,),
                )
                pg_rows.extend(cursor.fetchall())
            ch_rows.extend(clickhouse.execute(
                "SELECT payment_id, event_id FROM payment_events FINAL WHERE payment_id IN %(ids)s",
                {"ids": tuple(ids)},
            ))
    finally:
        postgres.close()
        clickhouse.disconnect()
    return pg_rows, ch_rows


def persist_payment_results(
    run_id, events, quarantined, postgres_rows, clickhouse_rows,
    *, freshness_sla_seconds, sample_limit,
):
    import psycopg2

    connection = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5433")),
        dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"], connect_timeout=10,
    )
    observed_at = datetime.now(timezone.utc)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT created_at FROM pipeline_runs WHERE run_id = %s",
                (run_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Pipeline run not found: {run_id}")
        due_at = row[0] + timedelta(seconds=freshness_sla_seconds)
        window_key = snapshot_window_key(events)
        check_ids = {}
        for store, rows in (
            ("POSTGRESQL", postgres_rows), ("CLICKHOUSE", clickhouse_rows),
        ):
            outcome = payment_store_outcome(
                events, rows, quarantined_events=quarantined,
                observed_at=observed_at, due_at=due_at, sample_limit=sample_limit,
            )
            check_ids[store] = persist_outcome(
                connection, run_id=run_id, store=store,
                metric="payment_event_identity", window_key=window_key,
                freshness_sla_seconds=freshness_sla_seconds, outcome=outcome,
            )
        return check_ids
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tail-per-partition", type=int, default=1000)
    parser.add_argument("--run-id")
    parser.add_argument("--freshness-sla-seconds", type=int, default=300)
    parser.add_argument("--sample-limit", type=int, default=25)
    args = parser.parse_args()
    if args.tail_per_partition < 1:
        parser.error("--tail-per-partition must be positive")
    if args.freshness_sla_seconds < 0:
        parser.error("--freshness-sla-seconds must be non-negative")
    if not 1 <= args.sample_limit <= 25:
        parser.error("--sample-limit must be between 1 and 25")

    from dotenv import load_dotenv
    load_dotenv()
    events, invalid = kafka_snapshot(args.tail_per_partition)
    dlq_sources = dlq_source_snapshot(args.tail_per_partition)
    materialized, quarantined = partition_quarantined_events(events, dlq_sources)
    payment_ids = sorted({event["payment_id"] for event in materialized})
    pg_rows, ch_rows = query_stores(payment_ids) if payment_ids else ([], [])
    differences = compare_records(materialized, pg_rows, ch_rows)
    check_ids = None
    if args.run_id:
        check_ids = persist_payment_results(
            args.run_id, events, quarantined, pg_rows, ch_rows,
            freshness_sla_seconds=args.freshness_sla_seconds,
            sample_limit=args.sample_limit,
        )
    print(json.dumps({"sampled_valid_events": len(events), "sampled_invalid_events": invalid,
                      "quarantined_events": len(quarantined),
                      "materialization_expected": len(materialized),
                      "unique_payments": len(payment_ids),
                      "reconciliation_checks": check_ids, **differences}, indent=2))
    if any(differences.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
