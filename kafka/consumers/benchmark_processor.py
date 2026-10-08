#!/usr/bin/env python3
"""Persist benchmark events, evaluate source-specific rules and emit alerts."""

from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.structs import OffsetAndMetadata

from fraud.rules.benchmark_rules import EVALUATOR_VERSION, evaluate_benchmark_payload
from shared.benchmark_contract import normalize_benchmark_event


def build_alert(event: dict[str, Any], signal: dict[str, Any]) -> dict[str, Any]:
    payload = event["payload"]
    if event["dataset_id"] == "ds3_paysim":
        entity_id = payload["participant_ids"]["origin"]
        entity_type = "simulated_account"
        amount = payload.get("amount", 0)
        account_id = entity_id
    else:
        entity_id = event["event_id"]
        entity_type = "account_application"
        amount = 0
        account_id = None
    return {
        "event_id": event["event_id"],
        "trace_id": event["trace_id"],
        "dataset_id": event["dataset_id"],
        "entity_id": entity_id,
        "entity_type": entity_type,
        "account_id": account_id,
        "amount": amount,
        "rule": signal["rule"],
        "risk_score": signal["risk_score"],
        "risk_level": signal["risk_level"],
        "decision": signal["decision"],
        "evidence": signal["evidence"],
    }


def persist_evaluation(connection: Any, event: dict[str, Any], signals: list[dict[str, Any]]) -> None:
    event_time = event["event_time"]
    provenance = event["provenance"]
    max_score = max((signal["risk_score"] for signal in signals), default=0)
    rules = [signal["rule"] for signal in signals]
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO benchmark_events
                (event_id, trace_id, dataset_id, source_row_id, event_type,
                 relative_time_value, relative_time_unit, payload,
                 ground_truth_is_fraud, source_file, source_kind)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING
            """,
            (
                event["event_id"], event["trace_id"], event["dataset_id"],
                event["source_row_id"], event["event_type"], event_time["value"],
                event_time["unit"], json.dumps(event["payload"]),
                event["ground_truth"]["is_fraud"], provenance["source_file"],
                provenance["source_kind"],
            ),
        )
        cursor.execute(
            """
            INSERT INTO benchmark_evaluations
                (event_id, dataset_id, evaluator_version, predicted_fraud,
                 max_score, triggered_rules)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (event_id, evaluator_version) DO NOTHING
            """,
            (
                event["event_id"], event["dataset_id"], EVALUATOR_VERSION,
                bool(signals), max_score, json.dumps(rules),
            ),
        )


def run_consumer() -> None:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "banking_kafka:9092")
    connection = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "banking_postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    connection.autocommit = False
    consumer = KafkaConsumer(
        "benchmark-events",
        bootstrap_servers=bootstrap,
        group_id="benchmark-processor-v2",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    producer = KafkaProducer(bootstrap_servers=bootstrap, acks="all", retries=10)
    try:
        for message in consumer:
            source = {"topic": message.topic, "partition": message.partition, "offset": message.offset}
            try:
                event = normalize_benchmark_event(json.loads(message.value.decode("utf-8")))
                signals = evaluate_benchmark_payload(event["dataset_id"], event["payload"])
                persist_evaluation(connection, event, signals)
                connection.commit()
                for signal in signals:
                    alert = build_alert(event, signal)
                    producer.send(
                        "fraud-events",
                        key=alert["entity_id"].encode("utf-8"),
                        value=json.dumps(alert, separators=(",", ":")).encode("utf-8"),
                    ).get(timeout=30)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                connection.rollback()
                producer.send("benchmark-events-dlq", value=json.dumps({
                    "source": source,
                    "error": str(exc),
                }).encode("utf-8")).get(timeout=30)
            consumer.commit({
                TopicPartition(message.topic, message.partition):
                    OffsetAndMetadata(message.offset + 1, "")
            })
    finally:
        producer.close()
        consumer.close()
        connection.close()


if __name__ == "__main__":
    run_consumer()
