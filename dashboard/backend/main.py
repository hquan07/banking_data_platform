import asyncio
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaConsumer
from pydantic import BaseModel

class TPSConfig(BaseModel):
    tps: int

current_tps = 2

app = FastAPI(title="Banking Command Center API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

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

# Use localhost if running locally, or banking_kafka if running inside docker
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVER", "localhost:9092")

async def consume_kafka():
    # Note: in real production, error handling and reconnection logic is needed
    try:
        print(f"Connecting to Kafka at {KAFKA_BOOTSTRAP}...")
        consumer = AIOKafkaConsumer(
            'payment-events', 'fraud-events', 'aml-events',
            bootstrap_servers=KAFKA_BOOTSTRAP,
            auto_offset_reset='latest' # only get new messages for dashboard
        )
        await consumer.start()
        print("Kafka Consumer started. Listening for events...")
        try:
            async for msg in consumer:
                data = json.loads(msg.value.decode('utf-8'))
                # Broadcast payload to all connected frontend clients
                payload = {
                    "topic": msg.topic,
                    "data": data
                }
                await manager.broadcast(payload)
        finally:
            await consumer.stop()
    except Exception as e:
        print(f"Kafka connection failed: {e}. Dashboard will not receive live events.")

async def simulate_events():
    print("MOCK MODE: Bắt đầu gửi dữ liệu giả lập (High Throughput)...")
    import random
    import time
    while True:
        # Sinh ngẫu nhiên số lượng giao dịch mỗi giây để đồ thị nhảy múa
        global current_tps
        num_tx = current_tps
        
        if num_tx == 0:
            await asyncio.sleep(1)
            continue
            
        for _ in range(num_tx):
            # Gửi transaction
            tx = {
                "transaction_id": f"TX_{random.randint(10000, 99999)}",
                "account_id": f"ACC_{random.randint(1, 100)}",
                "amount": round(random.uniform(10.0, 5000.0), 2),
                "lat": random.uniform(8.5, 23.3),  # VN Latitude
                "lng": random.uniform(102.1, 109.4)  # VN Longitude
            }
            await manager.broadcast({"topic": "payment-events", "data": tx})
            
            # Thỉnh thoảng gửi cảnh báo (tỷ lệ thấp đi vì số lượng TX nhiều lên)
            if random.random() < 0.015:
                alert = {
                    "account_id": tx["account_id"],
                    "rule": random.choice(["HIGH_VELOCITY", "STRUCTURING_SUSPICION", "CIRCULAR_TRANSFER"]),
                    "amount": tx["amount"],
                    "risk_score": random.randint(70, 99)
                }
                topic = "aml-events" if "STRUCTURING" in alert["rule"] or "CIRCULAR" in alert["rule"] else "fraud-events"
                await manager.broadcast({"topic": topic, "data": alert})
            
            # Delay một khoảng nhỏ để rải đều giao dịch trong 1 giây
            await asyncio.sleep(1.0 / num_tx)

@app.on_event("startup")
async def startup_event():
    # Thử kết nối Kafka, nếu lỗi thì bật Mock
    asyncio.create_task(consume_kafka())
    # Bật mock mode luôn để có dữ liệu demo đẹp mắt
    asyncio.create_task(simulate_events())

@app.post("/api/config/tps")
async def update_tps(config: TPSConfig):
    global current_tps
    current_tps = config.tps
    return {"message": f"TPS updated to {current_tps}"}

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Lắng nghe nếu client gửi message (keep-alive)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "clients_connected": len(manager.active_connections)}
