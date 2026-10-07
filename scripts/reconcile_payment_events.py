"""Compare a bounded Kafka snapshot with PostgreSQL and ClickHouse by payment ID."""

import argparse
import json
import os
import time

from shared.payment_contract import normalize_payment_event


def compare_records(events, postgres_rows, clickhouse_rows):
    """Return IDs missing or inconsistent across the two materialized stores."""
    expected = {event["payment_id"]: event["event_id"] for event in events}
    postgres = dict(postgres_rows)
    clickhouse = dict(clickhouse_rows)
    return {
        "missing_postgres": sorted(set(expected) - set(postgres)),
        "missing_clickhouse": sorted(set(expected) - set(clickhouse)),
        "postgres_event_mismatch": sorted(
            payment_id for payment_id in expected.keys() & postgres.keys()
            if expected[payment_id] != postgres[payment_id]
        ),
        "clickhouse_event_mismatch": sorted(
            payment_id for payment_id in expected.keys() & clickhouse.keys()
            if expected[payment_id] != clickhouse[payment_id]
        ),
    }


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
                        events.append(normalize_payment_event(json.loads(record.value)))
                    except (ValueError, TypeError):
                        invalid += 1
        return events, invalid
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tail-per-partition", type=int, default=1000)
    args = parser.parse_args()
    if args.tail_per_partition < 1:
        parser.error("--tail-per-partition must be positive")

    from dotenv import load_dotenv
    load_dotenv()
    events, invalid = kafka_snapshot(args.tail_per_partition)
    payment_ids = sorted({event["payment_id"] for event in events})
    pg_rows, ch_rows = query_stores(payment_ids) if payment_ids else ([], [])
    differences = compare_records(events, pg_rows, ch_rows)
    print(json.dumps({"sampled_valid_events": len(events), "sampled_invalid_events": invalid,
                      "unique_payments": len(payment_ids), **differences}, indent=2))
    if any(differences.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
