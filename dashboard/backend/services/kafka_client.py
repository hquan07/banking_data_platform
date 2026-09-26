"""
Kafka consumer, WebSocket manager, mock data simulator, and XAI helper.
"""
import asyncio
import json
import os
import random
import time

from fastapi import WebSocket
from core.db import pg_conn, redis_client


# =============================================
# WebSocket Connection Manager
# =============================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
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
                print(f"Error sending message: {e}")
                self.disconnect(connection)


manager = ConnectionManager()

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVER", "localhost:9092")

# =============================================
# XAI Helper: Generate mock explanation
# =============================================
XAI_REASONS = {
    "HIGH_VELOCITY": [
        "Tần suất giao dịch tăng {pct}% so với trung bình 30 ngày",
        "Số lượng giao dịch trong 1 phút vượt ngưỡng cho phép",
        "Giao dịch từ thiết bị mới chưa được xác minh",
        "Giao dịch thực hiện ngoài giờ hành chính ({time})",
    ],
    "STRUCTURING_SUSPICION": [
        "Phát hiện {count} giao dịch liên tiếp dưới ngưỡng báo cáo",
        "Tổng giá trị chia nhỏ đạt ${total} trong {hours} giờ",
        "Mô hình chia nhỏ (Smurfing) khớp với độ tin cậy {conf}%",
        "Tài khoản nhận tiền nằm trong danh sách giám sát",
    ],
    "CIRCULAR_TRANSFER": [
        "Phát hiện chuỗi chuyển tiền vòng tròn qua {count} tài khoản",
        "Tổng giá trị luân chuyển đạt ${total}",
        "Thời gian hoàn thành vòng: {mins} phút (bất thường)",
        "Tài khoản trung gian có lịch sử cảnh báo trước đó",
    ],
}


def generate_xai_explanation(rule_name: str, risk_score: int, amount: float) -> str:
    """Sinh ra lời giải thích dạng text cho một cảnh báo dựa trên ngưỡng thực tế."""
    try:
        from core.db import pg_conn
        if pg_conn:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT threshold, window_seconds, max_count FROM rules WHERE name = %s", (rule_name,))
                rule_config = cur.fetchone()
                
            if rule_config:
                threshold, window_seconds, max_count = rule_config
                if rule_name == "HIGH_VELOCITY" and max_count:
                    reasons = [f"Giao dịch vi phạm giới hạn tần suất: vượt quá {max_count} giao dịch trong {window_seconds} giây."]
                elif rule_name == "LARGE_AMOUNT" and threshold:
                    reasons = [f"Giao dịch có số tiền ({amount}) vượt quá ngưỡng cho phép ({threshold})."]
                elif rule_name == "STRUCTURING_SUSPICION" and threshold:
                    reasons = [f"Phát hiện dấu hiệu chia nhỏ giao dịch với số tiền {amount} liên quan đến hạn mức {threshold}."]
                else:
                    reasons = [f"Vi phạm luật {rule_name}. Điểm rủi ro: {risk_score}."]
                return json.dumps(reasons, ensure_ascii=False)
    except Exception as e:
        print(f"Error fetching rule for XAI: {e}")
        
    return json.dumps([f"Vi phạm quy tắc {rule_name} do hệ thống AI phát hiện với điểm rủi ro {risk_score}."], ensure_ascii=False)


# =============================================
# Load active rules from DB for mock simulation
# =============================================
def get_active_rules() -> dict:
    """Load active rules from Postgres and cache to Redis if available."""
    rules = {}
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT name, threshold, window_seconds, max_count, is_active FROM rules WHERE is_active = TRUE")
                for row in cur.fetchall():
                    rules[row[0]] = {"threshold": float(row[1]), "window_seconds": row[2], "max_count": row[3]}
            # Cache to Redis if available
            if redis_client:
                redis_client.set("active_rules", json.dumps(rules, default=str), ex=60)
        except Exception as e:
            print(f"Error loading rules: {e}")

    if not rules:
        rules = {
            "HIGH_VELOCITY": {"threshold": 10000, "window_seconds": 60, "max_count": 1},
            "STRUCTURING_SUSPICION": {"threshold": 9000, "window_seconds": 3600, "max_count": 5},
            "CIRCULAR_TRANSFER": {"threshold": 5000, "window_seconds": 300, "max_count": 3},
        }
    return rules


# =============================================
# Kafka Consumer
# =============================================
async def consume_kafka():
    """Connect to Kafka and broadcast events to WebSocket clients."""
    try:
        from aiokafka import AIOKafkaConsumer

        print(f"Connecting to Kafka at {KAFKA_BOOTSTRAP}...")
        consumer = AIOKafkaConsumer(
            'payment-events', 'fraud-events', 'aml-events',
            bootstrap_servers=KAFKA_BOOTSTRAP,
            auto_offset_reset='latest',
        )
        await consumer.start()
        print("Kafka Consumer started. Listening for events...")
        try:
            async for msg in consumer:
                data = json.loads(msg.value.decode('utf-8'))
                payload = {"topic": msg.topic, "data": data}
                await manager.broadcast(payload)

                # Lưu vào Postgres nếu là cảnh báo
                if msg.topic in ['fraud-events', 'aml-events'] and pg_conn:
                    try:
                        rule = data.get("rule", "ML_MODEL_FRAUD")
                        amount = data.get("amount", 0)
                        risk_score = data.get("risk_score", 90)
                        xai = generate_xai_explanation(rule, risk_score, amount)
                        event_id = data.get("event_id") or data.get("payment_id")
                        with pg_conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO alerts
                                    (event_id, payment_id, account_id, rule_name, amount,
                                     risk_score, risk_level, decision, xai_explanation)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (event_id, rule_name) WHERE event_id IS NOT NULL
                                DO UPDATE SET updated_at = NOW()
                                """,
                                (
                                    event_id, data.get("payment_id"), data.get("account_id"),
                                    rule, amount, risk_score,
                                    data.get("risk_level", "HIGH" if risk_score >= 85 else "MEDIUM"),
                                    data.get("decision", "REVIEW"), xai,
                                ),
                            )
                    except Exception as e:
                        print(f"Lỗi lưu Postgres: {e}")
        finally:
            await consumer.stop()
    except Exception as e:
        print(f"Kafka connection failed: {e}. Dashboard will not receive live events.")


# =============================================
# Mock Event Simulator
# =============================================
# Global TPS config
current_tps = 2


async def simulate_events():
    """Generate mock transaction and alert data for demo purposes."""
    print("MOCK MODE: Bắt đầu gửi dữ liệu giả lập (High Throughput)...")

    rule_cache = {}
    rule_cache_time = 0

    while True:
        global current_tps
        num_tx = current_tps

        if num_tx == 0:
            await asyncio.sleep(1)
            continue

        # Reload rules from DB/Redis every 30 seconds
        now = time.time()
        if now - rule_cache_time > 30:
            rule_cache = get_active_rules()
            rule_cache_time = now

        for _ in range(num_tx):
            # Gửi transaction
            tx = {
                "transaction_id": f"TX_{random.randint(10000, 99999)}",
                "account_id": f"ACC_{random.randint(1, 100)}",
                "amount": round(random.uniform(10.0, 5000.0), 2),
                "lat": random.uniform(8.5, 23.3),
                "lng": random.uniform(102.1, 109.4),
            }
            await manager.broadcast({"topic": "payment-events", "data": tx})

            # Thỉnh thoảng gửi cảnh báo
            if random.random() < 0.015:
                active_rule_names = list(rule_cache.keys()) if rule_cache else ["HIGH_VELOCITY", "STRUCTURING_SUSPICION", "CIRCULAR_TRANSFER"]
                rule_name = random.choice(active_rule_names)

                alert = {
                    "event_id": tx["transaction_id"],
                    "account_id": tx["account_id"],
                    "rule": rule_name,
                    "amount": tx["amount"],
                    "risk_score": random.randint(70, 99),
                }
                topic = "aml-events" if "STRUCTURING" in alert["rule"] or "CIRCULAR" in alert["rule"] else "fraud-events"
                await manager.broadcast({"topic": topic, "data": alert})

                if pg_conn:
                    try:
                        xai = generate_xai_explanation(rule_name, alert["risk_score"], alert["amount"])
                        with pg_conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO alerts
                                    (event_id, account_id, rule_name, amount,
                                     risk_score, risk_level, decision, xai_explanation)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (event_id, rule_name) WHERE event_id IS NOT NULL
                                DO UPDATE SET updated_at = NOW()
                                """,
                                (
                                    alert.get("event_id"), alert["account_id"], alert["rule"],
                                    alert["amount"], alert["risk_score"],
                                    "HIGH" if alert["risk_score"] >= 85 else "MEDIUM",
                                    "REVIEW", xai,
                                ),
                            )
                    except Exception:
                        pass

            await asyncio.sleep(1.0 / num_tx)
