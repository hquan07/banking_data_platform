"""Run-level benchmark reconciliation across Kafka and materialized stores."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from .engine import reconcile_count, reconcile_records
from .persistence import persist_outcome


def _run_context(connection: Any, run_id: str):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT dataset_id, created_at, COALESCE(completed_at, updated_at) "
            "FROM pipeline_runs WHERE run_id = %s",
            (run_id,),
        )
        run = cursor.fetchone()
        if run is None:
            raise ValueError(f"Pipeline run not found: {run_id}")
        cursor.execute(
            "SELECT topic, partition, start_offset, end_offset "
            "FROM pipeline_run_offsets WHERE run_id = %s ORDER BY topic, partition",
            (run_id,),
        )
        offsets = cursor.fetchall()
        cursor.execute(
            "SELECT counter_name, counter_value FROM pipeline_run_counters WHERE run_id = %s",
            (run_id,),
        )
        counters = dict(cursor.fetchall())
    return run, offsets, counters


def _kafka_records(run_id: str, offsets, bootstrap: str):
    from kafka import KafkaConsumer, TopicPartition

    consumer = KafkaConsumer(
        bootstrap_servers=bootstrap, enable_auto_commit=False,
        group_id=None, consumer_timeout_ms=3000,
    )
    by_topic: dict[str, list[tuple[str, str]]] = {}
    try:
        for topic, partition, start, end in offsets:
            if end is None or end <= start:
                continue
            topic_partition = TopicPartition(topic, partition)
            consumer.assign([topic_partition])
            consumer.seek(topic_partition, start)
            records = by_topic.setdefault(topic, [])
            while consumer.position(topic_partition) < end:
                polled = consumer.poll(timeout_ms=1000, max_records=500)
                if not polled:
                    raise TimeoutError(f"Kafka window unavailable: {topic}:{partition}:{start}-{end}")
                for message in polled.get(topic_partition, []):
                    if message.offset >= end:
                        continue
                    try:
                        payload = json.loads(message.value)
                    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                        continue
                    if payload.get("run_id") != run_id:
                        continue
                    identity = payload.get("event_id") or payload.get("payload_fingerprint")
                    if identity:
                        records.append((str(identity), str(identity)))
    finally:
        consumer.close()
    return by_topic


def _postgres_records(connection: Any, run_id: str):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT event_id, event_id FROM benchmark_events WHERE run_id = %s",
            (run_id,),
        )
        events = cursor.fetchall()
        cursor.execute(
            "SELECT event_id, event_id FROM benchmark_evaluations WHERE run_id = %s",
            (run_id,),
        )
        evaluations = cursor.fetchall()
        cursor.execute(
            """
            SELECT evaluation.event_id || ':' || rule.value,
                   evaluation.event_id || ':' || rule.value
            FROM benchmark_evaluations evaluation
            CROSS JOIN LATERAL jsonb_array_elements_text(evaluation.triggered_rules) rule(value)
            WHERE evaluation.run_id = %s
            """,
            (run_id,),
        )
        expected_alerts = cursor.fetchall()
        cursor.execute(
            "SELECT event_id || ':' || rule_name, event_id || ':' || rule_name "
            "FROM alerts WHERE run_id = %s AND rule_name <> 'TRANSFER_CASHOUT_SEQUENCE'",
            (run_id,),
        )
        alerts = cursor.fetchall()
    return events, evaluations, expected_alerts, alerts


def _neo4j_records(run_id: str):
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH ()-[event:BENCHMARK_TRANSACTION]->() "
                "WHERE event.run_id = $run_id RETURN event.event_id AS event_id",
                run_id=run_id,
            )
            return [(row["event_id"], row["event_id"]) for row in result]
    finally:
        driver.close()


def reconcile_benchmark_run(
    connection: Any,
    run_id: str,
    *,
    freshness_sla_seconds: int = 300,
    sample_limit: int = 25,
    kafka_bootstrap: str | None = None,
) -> dict[str, str]:
    if freshness_sla_seconds < 0:
        raise ValueError("freshness_sla_seconds must be non-negative")
    (dataset_id, _created_at, terminal_at), offsets, counters = _run_context(connection, run_id)
    observed_at = datetime.now(timezone.utc)
    due_at = terminal_at + timedelta(seconds=freshness_sla_seconds)
    window_key = ",".join(
        f"{topic}:p{partition}:{start}-{end}"
        for topic, partition, start, end in offsets
    ) or "no-offsets"
    kafka = _kafka_records(
        run_id, offsets,
        kafka_bootstrap or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"),
    )
    source_events = kafka.get("benchmark-events", [])
    dlq_events = kafka.get("benchmark-events-dlq", [])
    events, evaluations, expected_alerts, alerts = _postgres_records(connection, run_id)

    checks = {
        ("KAFKA", "accepted_events"): reconcile_count(
            counters.get("published", 0) + counters.get("rejected", 0),
            len(source_events) + len(dlq_events), observed_at=observed_at, due_at=due_at,
            sample_limit=sample_limit,
        ),
        ("POSTGRESQL", "benchmark_events"): reconcile_records(
            source_events, events, observed_at=observed_at, due_at=due_at,
            sample_limit=sample_limit,
        ),
        ("EVALUATIONS", "benchmark_evaluations"): reconcile_records(
            source_events, evaluations, observed_at=observed_at, due_at=due_at,
            sample_limit=sample_limit,
        ),
        ("ALERTS", "rule_alerts"): reconcile_records(
            expected_alerts, alerts, observed_at=observed_at, due_at=due_at,
            sample_limit=sample_limit,
        ),
        ("DLQ", "quarantined_events"): reconcile_count(
            counters.get("rejected", 0), len(dlq_events),
            observed_at=observed_at, due_at=due_at,
            sample_ids=[identity for identity, _ in dlq_events], sample_limit=sample_limit,
        ),
    }
    if dataset_id == "ds3_paysim":
        checks[("NEO4J", "benchmark_edges")] = reconcile_records(
            source_events, _neo4j_records(run_id),
            observed_at=observed_at, due_at=due_at, sample_limit=sample_limit,
        )

    check_ids = {}
    for (store, metric), outcome in checks.items():
        check_ids[f"{store}:{metric}"] = persist_outcome(
            connection, run_id=run_id, store=store, metric=metric,
            window_key=window_key, freshness_sla_seconds=freshness_sla_seconds,
            outcome=outcome,
        )
    return check_ids
