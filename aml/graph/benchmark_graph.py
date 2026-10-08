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
    return {
        "event_id": event["event_id"],
        "trace_id": event["trace_id"],
        "dataset_id": event["dataset_id"],
        "origin_id": f"{event['dataset_id']}:{origin}",
        "origin_display_id": origin,
        "destination_id": f"{event['dataset_id']}:{destination}",
        "destination_display_id": destination,
        "transaction_type": payload["transaction_type"],
        "amount": float(payload["amount"]),
        "relative_step": float(event["event_time"]["value"]),
        "ground_truth_is_fraud": event["ground_truth"]["is_fraud"],
    }


def build_chain_alert(cashout: dict[str, Any], inbound: dict[str, Any]) -> dict[str, Any]:
    source_ids = sorted([cashout["event_id"], inbound["event_id"]])
    digest = hashlib.sha256(":".join(source_ids).encode("utf-8")).hexdigest()
    return {
        "event_id": f"benchmark-chain:{digest}",
        "trace_id": cashout["trace_id"],
        "dataset_id": "ds3_paysim",
        "entity_id": cashout["origin_display_id"],
        "entity_type": "simulated_account",
        "account_id": cashout["origin_display_id"],
        "amount": round(cashout["amount"] + inbound["amount"], 2),
        "rule": "TRANSFER_CASHOUT_CHAIN",
        "risk_score": 85,
        "risk_level": "HIGH",
        "decision": "REVIEW",
        "source_event_ids": source_ids,
        "evidence": {
            "transfer_amount": inbound["amount"],
            "cashout_amount": cashout["amount"],
            "transfer_step": inbound["relative_step"],
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

    def close(self) -> None:
        self.driver.close()

    def record(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            inbound = session.execute_write(self._write_and_find_chain, record)
        return [build_chain_alert(record, item) for item in inbound]

    @staticmethod
    def _write_and_find_chain(tx: Any, record: dict[str, Any]) -> list[dict[str, Any]]:
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
            ON CREATE SET event.trace_id = $trace_id,
                          event.transaction_type = $transaction_type,
                          event.amount = $amount,
                          event.relative_step = $relative_step,
                          event.ground_truth_is_fraud = $ground_truth_is_fraud
            """,
            **record,
        ).consume()
        if record["transaction_type"] != "CASH_OUT":
            return []
        result = tx.run(
            """
            MATCH (victim:BenchmarkAccount)-[transfer:BENCHMARK_TRANSACTION]->
                  (mule:BenchmarkAccount {id: $origin_id})
            WHERE transfer.transaction_type = 'TRANSFER'
              AND transfer.relative_step <= $relative_step
              AND transfer.relative_step >= $relative_step - 24
              AND transfer.amount >= $amount * 0.80
              AND transfer.amount <= $amount * 1.20
            RETURN transfer.event_id AS event_id,
                   transfer.amount AS amount,
                   transfer.relative_step AS relative_step
            ORDER BY transfer.relative_step DESC
            LIMIT 20
            """,
            origin_id=record["origin_id"],
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
