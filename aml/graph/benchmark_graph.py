#!/usr/bin/env python3
"""PaySim graph sink isolated from real Account nodes and calendar time."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.structs import OffsetAndMetadata

from shared.benchmark_contract import normalize_benchmark_event


def graph_record(event: dict[str, Any]) -> dict[str, Any] | None:
    if event["dataset_id"] != "ds3_paysim":
        return None
    payload = event["payload"]
    participants = payload.get("participant_ids") or {}
    origin = participants.get("origin")
    destination = participants.get("destination")
    if not origin or not destination:
        raise ValueError("missing_paysim_participants")
    try:
        source_row_number = int(event["source_row_id"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("invalid_paysim_source_row") from None
    if source_row_number < 0:
        raise ValueError("invalid_paysim_source_row")
    return {
        "event_id": event["event_id"],
        "trace_id": event["trace_id"],
        "dataset_id": event["dataset_id"],
        "origin_id": f"{event['dataset_id']}:{origin}",
        "origin_display_id": origin,
        "destination_id": f"{event['dataset_id']}:{destination}",
        "destination_display_id": destination,
        "source_row_number": source_row_number,
        "transaction_type": payload["transaction_type"],
        "amount": float(payload["amount"]),
        "relative_step": float(event["event_time"]["value"]),
        "ground_truth_is_fraud": event["ground_truth"]["is_fraud"],
    }


def build_sequence_alert(transfer: dict[str, Any], cashout: dict[str, Any]) -> dict[str, Any]:
    source_ids = [transfer["event_id"], cashout["event_id"]]
    digest = hashlib.sha256(":".join(source_ids).encode("utf-8")).hexdigest()
    sequence_id = f"ds3_paysim:rows:{transfer['source_row_number']}-{cashout['source_row_number']}"
    return {
        "event_id": f"benchmark-sequence:{digest}",
        "trace_id": cashout["trace_id"],
        "dataset_id": "ds3_paysim",
        "entity_id": sequence_id,
        "entity_type": "benchmark_sequence",
        "account_id": None,
        "amount": round(cashout["amount"] + transfer["amount"], 2),
        "rule": "TRANSFER_CASHOUT_SEQUENCE",
        "risk_score": 70,
        "risk_level": "MEDIUM",
        "decision": "REVIEW",
        "source_event_ids": source_ids,
        "evidence": {
            "match_basis": "adjacent_source_rows_same_step_and_amount",
            "participant_linked": False,
            "transfer_amount": transfer["amount"],
            "cashout_amount": cashout["amount"],
            "transfer_step": transfer["relative_step"],
            "cashout_step": cashout["relative_step"],
        },
    }


class BenchmarkGraph:
    def __init__(self, uri: str, user: str, password: str):
        from neo4j import GraphDatabase

        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        with self.driver.session() as session:
            session.run(
                "CREATE CONSTRAINT benchmark_account_id_unique IF NOT EXISTS "
                "FOR (n:BenchmarkAccount) REQUIRE n.id IS UNIQUE"
            ).consume()
            session.run(
                "MATCH ()-[event:BENCHMARK_TRANSACTION]->() "
                "WHERE event.source_row_number IS NULL "
                "SET event.source_row_number = toInteger(split(event.event_id, ':')[1])"
            ).consume()

    def close(self) -> None:
        self.driver.close()

    def record(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            counterparts = session.execute_write(self._write_and_find_sequence, record)
        alerts = []
        for counterpart in counterparts:
            if record["transaction_type"] == "TRANSFER":
                alerts.append(build_sequence_alert(record, counterpart))
            else:
                alerts.append(build_sequence_alert(counterpart, record))
        return alerts

    @staticmethod
    def _write_and_find_sequence(tx: Any, record: dict[str, Any]) -> list[dict[str, Any]]:
        tx.run(
            """
            MERGE (origin:BenchmarkAccount {id: $origin_id})
            ON CREATE SET origin.display_id = $origin_display_id,
                          origin.dataset_id = $dataset_id,
                          origin.provenance = 'synthetic_simulation'
            MERGE (destination:BenchmarkAccount {id: $destination_id})
            ON CREATE SET destination.display_id = $destination_display_id,
                          destination.dataset_id = $dataset_id,
                          destination.provenance = 'synthetic_simulation'
            MERGE (origin)-[event:BENCHMARK_TRANSACTION {event_id: $event_id}]->(destination)
            SET event.trace_id = $trace_id,
                event.transaction_type = $transaction_type,
                event.amount = $amount,
                event.relative_step = $relative_step,
                event.source_row_number = $source_row_number,
                event.ground_truth_is_fraud = $ground_truth_is_fraud
            """,
            **record,
        ).consume()
        if record["transaction_type"] not in {"TRANSFER", "CASH_OUT"}:
            return []
        counterpart_type = "CASH_OUT" if record["transaction_type"] == "TRANSFER" else "TRANSFER"
        counterpart_row = record["source_row_number"] + (1 if record["transaction_type"] == "TRANSFER" else -1)
        result = tx.run(
            """
            MATCH (origin:BenchmarkAccount)-[other:BENCHMARK_TRANSACTION]->
                  (destination:BenchmarkAccount)
            WHERE other.transaction_type = $counterpart_type
              AND other.source_row_number = $counterpart_row
              AND other.relative_step = $relative_step
              AND abs(other.amount - $amount) <= 0.01
            RETURN other.event_id AS event_id,
                   other.trace_id AS trace_id,
                   origin.display_id AS origin_display_id,
                   destination.display_id AS destination_display_id,
                   other.source_row_number AS source_row_number,
                   other.transaction_type AS transaction_type,
                   other.amount AS amount,
                   other.relative_step AS relative_step
            LIMIT 1
            """,
            counterpart_type=counterpart_type,
            counterpart_row=counterpart_row,
            relative_step=record["relative_step"],
            amount=record["amount"],
        )
        return [dict(item) for item in result]


def run_consumer() -> None:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "banking_kafka:9092")
    graph = BenchmarkGraph(
        os.environ["NEO4J_URI"], os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]
    )
    consumer = KafkaConsumer(
        "benchmark-events",
        bootstrap_servers=bootstrap,
        group_id="benchmark-graph-v1",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    producer = KafkaProducer(bootstrap_servers=bootstrap, acks="all", retries=10)
    try:
        for message in consumer:
            event = normalize_benchmark_event(json.loads(message.value.decode("utf-8")))
            record = graph_record(event)
            if record is not None:
                for alert in graph.record(record):
                    producer.send(
                        "aml-events",
                        key=alert["entity_id"].encode("utf-8"),
                        value=json.dumps(alert, separators=(",", ":")).encode("utf-8"),
                    ).get(timeout=30)
            consumer.commit({
                TopicPartition(message.topic, message.partition):
                    OffsetAndMetadata(message.offset + 1, "")
            })
    finally:
        producer.close()
        consumer.close()
        graph.close()


if __name__ == "__main__":
    run_consumer()
