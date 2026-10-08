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


def sequence_alerts(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one deterministic alert per source-row pair from batch matches."""
    alerts: dict[str, dict[str, Any]] = {}
    for match in matches:
        current = dict(match["current"])
        counterpart = dict(match["counterpart"])
        if current["transaction_type"] == "TRANSFER":
            alert = build_sequence_alert(current, counterpart)
        else:
            alert = build_sequence_alert(counterpart, current)
        alerts[alert["event_id"]] = alert
    return list(alerts.values())


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
                "CREATE INDEX benchmark_transaction_sequence_lookup IF NOT EXISTS "
                "FOR ()-[event:BENCHMARK_TRANSACTION]-() "
                "ON (event.transaction_type, event.source_row_number)"
            ).consume()
            session.run(
                "MATCH ()-[event:BENCHMARK_TRANSACTION]->() "
                "WHERE event.source_row_number IS NULL "
                "SET event.source_row_number = toInteger(split(event.event_id, ':')[1])"
            ).consume()

    def close(self) -> None:
        self.driver.close()

    def record(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        return self.record_batch([record])

    def record_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not records:
            return []
        with self.driver.session() as session:
            matches = session.execute_write(self._write_batch_and_find_sequences, records)
        return sequence_alerts(matches)

    @staticmethod
    def _write_batch_and_find_sequences(
        tx: Any, records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        tx.run(
            """
            UNWIND $records AS record
            MERGE (origin:BenchmarkAccount {id: record.origin_id})
            ON CREATE SET origin.display_id = record.origin_display_id,
                          origin.dataset_id = record.dataset_id,
                          origin.provenance = 'synthetic_simulation'
            MERGE (destination:BenchmarkAccount {id: record.destination_id})
            ON CREATE SET destination.display_id = record.destination_display_id,
                          destination.dataset_id = record.dataset_id,
                          destination.provenance = 'synthetic_simulation'
            MERGE (origin)-[event:BENCHMARK_TRANSACTION {event_id: record.event_id}]->(destination)
            SET event.trace_id = record.trace_id,
                event.transaction_type = record.transaction_type,
                event.amount = record.amount,
                event.relative_step = record.relative_step,
                event.source_row_number = record.source_row_number,
                event.ground_truth_is_fraud = record.ground_truth_is_fraud
            """,
            records=records,
        ).consume()
        candidates = []
        for record in records:
            if record["transaction_type"] not in {"TRANSFER", "CASH_OUT"}:
                continue
            candidate = dict(record)
            if record["transaction_type"] == "TRANSFER":
                candidate["counterpart_type"] = "CASH_OUT"
                candidate["counterpart_row"] = record["source_row_number"] + 1
            else:
                candidate["counterpart_type"] = "TRANSFER"
                candidate["counterpart_row"] = record["source_row_number"] - 1
            candidates.append(candidate)
        if not candidates:
            return []
        result = tx.run(
            """
            UNWIND $candidates AS current
            MATCH (origin:BenchmarkAccount)-[other:BENCHMARK_TRANSACTION]->
                  (destination:BenchmarkAccount)
            WHERE other.transaction_type = current.counterpart_type
              AND other.source_row_number = current.counterpart_row
              AND other.relative_step = current.relative_step
              AND abs(other.amount - current.amount) <= 0.01
            RETURN current,
                   {
                       event_id: other.event_id,
                       trace_id: other.trace_id,
                       origin_display_id: origin.display_id,
                       destination_display_id: destination.display_id,
                       source_row_number: other.source_row_number,
                       transaction_type: other.transaction_type,
                       amount: other.amount,
                       relative_step: other.relative_step
                   } AS counterpart
            """,
            candidates=candidates,
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
    batch_size = int(os.environ.get("BENCHMARK_GRAPH_BATCH_SIZE", "500"))
    if batch_size <= 0:
        raise ValueError("BENCHMARK_GRAPH_BATCH_SIZE must be positive")
    try:
        while True:
            polled = consumer.poll(timeout_ms=1000, max_records=batch_size)
            if not polled:
                continue
            records = []
            offsets = {}
            for topic_partition, messages in polled.items():
                for message in messages:
                    event = normalize_benchmark_event(json.loads(message.value.decode("utf-8")))
                    record = graph_record(event)
                    if record is not None:
                        records.append(record)
                offsets[TopicPartition(topic_partition.topic, topic_partition.partition)] = (
                    OffsetAndMetadata(messages[-1].offset + 1, "")
                )
            futures = []
            for alert in graph.record_batch(records):
                futures.append(producer.send(
                    "aml-events",
                    key=alert["entity_id"].encode("utf-8"),
                    value=json.dumps(alert, separators=(",", ":")).encode("utf-8"),
                ))
            for future in futures:
                future.get(timeout=30)
            consumer.commit(offsets)
    finally:
        producer.close()
        consumer.close()
        graph.close()


if __name__ == "__main__":
    run_consumer()
