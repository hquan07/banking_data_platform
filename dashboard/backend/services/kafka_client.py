"""Kafka consumer and WebSocket connection manager."""
import asyncio
import json
import os
from fastapi import WebSocket
from prometheus_client import Counter, Histogram
from datetime import datetime, timezone
from core.db import pg_conn
from services.kafka_payload import decode_message


# =============================================
# WebSocket Connection Manager
# =============================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, subprotocol: str | None = None):
        await websocket.accept(subprotocol=subprotocol)
        self.active_connections.append(websocket)
        print(f"Client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"Client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                WEBSOCKET_BROADCAST_FAILURES.inc()
                print(f"Error sending message: {e}")
                self.disconnect(connection)


manager = ConnectionManager()
kafka_ready = asyncio.Event()

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVER", "localhost:9092")

# Metrics
DATA_FRESHNESS = Histogram(
    "data_freshness_seconds", 
    "Time from event generation to backend consumption"
)
WEBSOCKET_BROADCAST_FAILURES = Counter(
    "websocket_broadcast_failures_total", "Failed WebSocket sends"
)

# =============================================
# Kafka Consumer
# =============================================
def persist_alert(data: dict) -> bool:
    """Insert once; duplicate deliveries do not change alert state or audit time."""
    if pg_conn is None:
        raise RuntimeError("PostgreSQL is unavailable for alert persistence")
    event_id = data.get("event_id")
    account_id = data.get("account_id")
    rule = data.get("rule")
    if not event_id or not account_id or not rule:
        raise ValueError("Alert requires event_id, account_id and rule")
    amount = data.get("amount") or 0
    risk_score = data.get("risk_score", data.get("fraud_score", 0))
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts
                (event_id, trace_id, payment_id, account_id, rule_name, amount,
                 risk_score, risk_level, decision)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id, rule_name) WHERE event_id IS NOT NULL DO NOTHING
            RETURNING alert_id
            """,
            (
                event_id, data.get("trace_id"), data.get("payment_id"), account_id, rule, amount,
                risk_score, data.get("risk_level", "MEDIUM"),
                data.get("decision", "REVIEW"),
            ),
        )
        return cur.fetchone() is not None


async def consume_kafka():
    """Commit offsets only after alert persistence, and retry connection failures."""
    from aiokafka import AIOKafkaConsumer, TopicPartition

    while True:
        consumer = AIOKafkaConsumer(
            "payment-events", "fraud-events", "aml-events",
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id="dashboard-stream-v1",
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        retry = False
        try:
            await consumer.start()
            kafka_ready.set()
            async for msg in consumer:
                data = decode_message(msg.topic, msg.value)
                if data is None:
                    print(
                        f"Skipping invalid payment payload at {msg.topic} "
                        f"partition={msg.partition} offset={msg.offset}; Spark routes it to DLQ"
                    )
                    await consumer.commit({TopicPartition(msg.topic, msg.partition): msg.offset + 1})
                    continue
                inserted = True
                if msg.topic in ("fraud-events", "aml-events"):
                    inserted = persist_alert(data)
                await consumer.commit()
                if "timestamp" in data:
                    try:
                        event_time = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                        latency = (datetime.now(timezone.utc) - event_time).total_seconds()
                        if latency > 0:
                            DATA_FRESHNESS.observe(latency)
                    except (ValueError, TypeError):
                        pass
                if inserted:
                    await manager.broadcast({"topic": msg.topic, "data": data})
        except Exception as exc:
            print(f"Kafka consumer failed; retrying in 5 seconds: {exc}")
            retry = True
        finally:
            kafka_ready.clear()
            try:
                await consumer.stop()
            except Exception as exc:
                print(f"Kafka consumer cleanup failed: {exc}")
        if retry:
            await asyncio.sleep(5)
