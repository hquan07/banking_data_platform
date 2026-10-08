"""Opt-in transfer Kafka -> Neo4j -> AML alert test for 3/4/5-node cycles."""

import json
import os
import time
import uuid
from datetime import datetime, timezone

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_E2E") != "1", reason="requires the running Docker Compose stack"
)


def test_cycles_and_low_amount_false_positive():
    import psycopg2
    import requests
    from dotenv import load_dotenv
    from kafka import KafkaConsumer, KafkaProducer

    load_dotenv()
    suffix = uuid.uuid4().hex[:14]
    prefix = f"E2E_GRAPH_{suffix}_"
    neo4j_url = "http://localhost:7474/db/neo4j/tx/commit"

    def cypher(statement, parameters=None):
        response = requests.post(
            neo4j_url, auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
            json={"statements": [{"statement": statement, "parameters": parameters or {}}]},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        assert not payload["errors"], payload["errors"]
        return [item["row"] for item in payload["results"][0]["data"]]

    consumer = KafkaConsumer(
        "aml-events", bootstrap_servers="localhost:9094", group_id=f"e2e-graph-{suffix}",
        auto_offset_reset="latest", enable_auto_commit=False,
        value_deserializer=lambda payload: json.loads(payload.decode()),
    )
    producer = KafkaProducer(bootstrap_servers="localhost:9094", acks="all")
    connection = psycopg2.connect(
        host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    connection.autocommit = True
    try:
        consumer.poll(timeout_ms=1000)
        for node_count in (3, 4, 5):
            accounts = [f"{prefix}{node_count}_{i}" for i in range(node_count)]
            ids = set()
            for edge in range(node_count):
                event_id = f"e2e-graph-{suffix}-{node_count}-{edge}"
                ids.add(event_id)
                event = {
                    "schema_version": 1, "event_id": event_id, "trace_id": f"trace-{suffix}",
                    "from_account_id": accounts[edge],
                    "to_account_id": accounts[(edge + 1) % node_count],
                    "amount": "5000.00", "currency": "USD",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                producer.send(
                    "transfer-events", key=accounts[edge].encode(),
                    value=json.dumps(event).encode(),
                ).get(timeout=10)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    count = cypher(
                        "MATCH ()-[r:TRANSFERRED_TO {event_id: $id}]->() RETURN count(r)",
                        {"id": event_id},
                    )[0][0]
                    if count == 1:
                        break
                    time.sleep(0.25)
                else:
                    pytest.fail(f"Transfer edge {event_id} not stored in Neo4j")

            found = False
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and not found:
                for messages in consumer.poll(timeout_ms=1000).values():
                    found = found or any(
                        message.value.get("rule") == "CIRCULAR_TRANSFER"
                        and set(message.value.get("source_event_ids", [])) == ids
                        for message in messages
                    )
            assert found, f"No {node_count}-node AML cycle alert"
            producer.send("transfer-events", key=accounts[-1].encode(),
                          value=json.dumps(event).encode()).get(timeout=10)

        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM alerts WHERE account_id LIKE %s AND rule_name = 'CIRCULAR_TRANSFER'",
                    (prefix + "%",),
                )
                if cursor.fetchone()[0] == 3:
                    break
            time.sleep(0.5)
        else:
            pytest.fail("Graph AML alerts did not enter the case lifecycle")
        for node_count in (3, 4, 5):
            last_event_id = f"e2e-graph-{suffix}-{node_count}-{node_count - 1}"
            assert cypher(
                "MATCH ()-[r:TRANSFERRED_TO {event_id: $id}]->() RETURN count(r)",
                {"id": last_event_id},
            )[0][0] == 1

        accounts = [f"{prefix}LOW_{i}" for i in range(3)]
        low_ids = set()
        for edge in range(3):
            event_id = f"e2e-graph-{suffix}-low-{edge}"
            low_ids.add(event_id)
            event = {
                "schema_version": 1, "event_id": event_id, "trace_id": f"trace-{suffix}",
                "from_account_id": accounts[edge], "to_account_id": accounts[(edge + 1) % 3],
                "amount": "100.00" if edge == 1 else "5000.00", "currency": "USD",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            producer.send("transfer-events", key=accounts[edge].encode(),
                          value=json.dumps(event).encode()).get(timeout=10)
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            for messages in consumer.poll(timeout_ms=1000).values():
                assert all(set(message.value.get("source_event_ids", [])) != low_ids
                           for message in messages)
    finally:
        consumer.close()
        producer.close()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM alert_audit_log WHERE alert_id IN "
                           "(SELECT alert_id FROM alerts WHERE account_id LIKE %s)", (prefix + "%",))
            cursor.execute("DELETE FROM alerts WHERE account_id LIKE %s", (prefix + "%",))
        connection.close()
        cypher("MATCH (a:Account) WHERE a.id STARTS WITH $prefix DETACH DELETE a", {"prefix": prefix})
