"""Idempotent Kafka transfer graph sink and 3–5 edge AML cycle detector."""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.structs import OffsetAndMetadata
from neo4j import GraphDatabase

from shared.transfer_contract import normalize_transfer_event


class BankingGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        with self.driver.session() as session:
            for label in ("Customer", "Account", "Merchant"):
                session.run(
                    f"CREATE CONSTRAINT {label.lower()}_id_unique IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                ).consume()

    def close(self):
        self.driver.close()

    def record_transaction(self, event, source):
        event = normalize_transfer_event(event)
        with self.driver.session() as session:
            paths = session.execute_write(self._write_and_find_cycles, event, source)
        alerts = []
        for path in paths:
            ids = sorted([event["event_id"], *path["event_ids"]])
            cycle_id = "graph-" + hashlib.sha256(":/".join(ids).encode()).hexdigest()
            alerts.append({
                "event_id": cycle_id, "trace_id": event["trace_id"],
                "account_id": event["from_account_id"], "rule": "CIRCULAR_TRANSFER",
                "amount": round(float(event["amount"]) + path["path_amount"], 2),
                "currency": event["currency"], "risk_score": 90, "risk_level": "HIGH",
                "decision": "REVIEW", "timestamp": event["timestamp"],
                "source_event_ids": ids,
            })
        return alerts

    @staticmethod
    def _write_and_find_cycles(tx, event, source):
        tx.run(
            """MERGE (a:Account {id: $from_account_id})
               MERGE (b:Account {id: $to_account_id})
               MERGE (a)-[t:TRANSFERRED_TO {event_id: $event_id}]->(b)
               ON CREATE SET t.amount = $amount, t.currency = $currency,
                   t.event_time = datetime($event_time), t.trace_id = $trace_id,
                   t.source_topic = $source_topic, t.source_partition = $source_partition,
                   t.source_offset = $source_offset""",
            from_account_id=event["from_account_id"], to_account_id=event["to_account_id"],
            event_id=event["event_id"], amount=float(event["amount"]),
            currency=event["currency"], event_time=event["timestamp"],
            trace_id=event["trace_id"], source_topic=source["topic"],
            source_partition=source["partition"], source_offset=source["offset"],
        ).consume()
        event_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        window_start = (event_time - timedelta(hours=1)).astimezone(timezone.utc).isoformat()
        result = tx.run(
            """MATCH (b:Account {id: $to_account_id}), (a:Account {id: $from_account_id})
               MATCH p = (b)-[:TRANSFERRED_TO*2..4]->(a)
               WHERE all(r IN relationships(p) WHERE
                   r.event_time >= datetime($window_start)
                   AND r.event_time <= datetime($event_time)
                   AND r.amount >= $min_amount AND r.currency = $currency)
                 AND all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
               RETURN [r IN relationships(p) | r.event_id] AS event_ids,
                      reduce(total = 0.0, r IN relationships(p) | total + r.amount) AS path_amount
               LIMIT 20""",
            to_account_id=event["to_account_id"], from_account_id=event["from_account_id"],
            window_start=window_start, event_time=event["timestamp"],
            min_amount=float(os.environ.get("GRAPH_MIN_TRANSFER_AMOUNT", "1000")),
            currency=event["currency"],
        )
        return [dict(record) for record in result]


def run_consumer():
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "banking_kafka:9092")
    graph = BankingGraph(
        os.environ["NEO4J_URI"], os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]
    )
    consumer = KafkaConsumer(
        "transfer-events", bootstrap_servers=bootstrap, group_id="neo4j-aml-v1",
        enable_auto_commit=False, auto_offset_reset="earliest",
    )
    producer = KafkaProducer(bootstrap_servers=bootstrap, acks="all", retries=10)
    try:
        for message in consumer:
            source = {"topic": message.topic, "partition": message.partition, "offset": message.offset}
            try:
                event = normalize_transfer_event(json.loads(message.value.decode("utf-8")))
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                payload = {"raw_value": message.value.decode("utf-8", errors="replace"),
                           "validation_error": str(exc), "source": source}
                producer.send("transfer-events-dlq", value=json.dumps(payload).encode()).get(timeout=20)
                print(json.dumps({"event": "transfer_rejected", "source": source,
                                  "reason": str(exc)}), flush=True)
            else:
                alerts = graph.record_transaction(event, source)
                for alert in alerts:
                    producer.send(
                        "aml-events", key=alert["account_id"].encode(),
                        value=json.dumps(alert).encode(),
                    ).get(timeout=20)
                print(json.dumps({"event": "transfer_processed", "event_id": event["event_id"],
                                  "trace_id": event["trace_id"], "source": source,
                                  "alert_count": len(alerts)}), flush=True)
            consumer.commit({TopicPartition(message.topic, message.partition):
                             OffsetAndMetadata(message.offset + 1, "")})
    finally:
        producer.close()
        consumer.close()
        graph.close()


if __name__ == "__main__":
    run_consumer()
