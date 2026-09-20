import asyncio
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaConsumer
from pydantic import BaseModel
from auth import verify_password, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends, HTTPException, status
from datetime import timedelta
import csv
import io
from fastapi.responses import StreamingResponse
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
                
                # Lưu vào Postgres nếu là cảnh báo
                if msg.topic in ['fraud-events', 'aml-events'] and pg_conn:
                    try:
                        with pg_conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO alerts (account_id, rule_name, amount, risk_score) VALUES (%s, %s, %s, %s)",
                                (data.get("account_id"), data.get("rule", "ML_MODEL_FRAUD"), data.get("amount", 0), data.get("risk_score", 90))
                            )
                    except Exception as e:
                        print(f"Lỗi lưu Postgres: {e}")
        finally:
            await consumer.stop()
    except Exception as e:
        print(f"Kafka connection failed: {e}. Dashboard will not receive live events.")

async def simulate_events():
    print("MOCK MODE: Bắt đầu gửi dữ liệu giả lập (High Throughput)...")
    from neo4j import GraphDatabase
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
                
                if pg_conn:
                    try:
                        with pg_conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO alerts (account_id, rule_name, amount, risk_score) VALUES (%s, %s, %s, %s)",
                                (alert["account_id"], alert["rule"], alert["amount"], alert["risk_score"])
                            )
                    except Exception as e:
                        pass
            
            # Delay một khoảng nhỏ để rải đều giao dịch trong 1 giây
            await asyncio.sleep(1.0 / num_tx)

@app.on_event("startup")
async def startup_event():
    # Initialize default users if not present
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM users")
                if cur.fetchone()[0] == 0:
                    admin_hash = get_password_hash("admin")
                    analyst_hash = get_password_hash("analyst")
                    cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", ('admin', admin_hash, 'ADMIN'))
                    cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", ('analyst_1', analyst_hash, 'ANALYST'))
                    # Assign existing alerts to analyst_1 to prevent them from being hidden
                    cur.execute("UPDATE alerts SET assignee_id = (SELECT id FROM users WHERE username = 'analyst_1')")
        except Exception as e:
            print("Init users error:", e)

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

# --- Neo4j Integration ---
try:
    from neo4j import GraphDatabase
    NEO4J_URI = "neo4j://banking_neo4j:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "banking_password"
    graph_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
except ImportError:
    print("neo4j module not installed")
    graph_driver = None
except Exception as e:
    print(f"Neo4j connection error: {e}")
    graph_driver = None

@app.get("/api/graph/circular")
def get_circular_graph():
    if graph_driver:
        query = """
        MATCH (a:Account)-[r1:TRANSFERRED_TO]->(b:Account)-[r2:TRANSFERRED_TO]->(c:Account)-[r3:TRANSFERRED_TO]->(a)
        RETURN a.id AS acc_a, b.id AS acc_b, c.id AS acc_c, r1.amount AS amt1, r2.amount AS amt2, r3.amount AS amt3
        LIMIT 50
        """
        try:
            with graph_driver.session() as session:
                result = session.run(query)
                records = list(result)
                
                if len(records) > 0:
                    nodes = set()
                    links = []
                    for rec in records:
                        nodes.add(rec["acc_a"])
                        nodes.add(rec["acc_b"])
                        nodes.add(rec["acc_c"])
                        links.append({"source": rec["acc_a"], "target": rec["acc_b"], "value": rec["amt1"]})
                        links.append({"source": rec["acc_b"], "target": rec["acc_c"], "value": rec["amt2"]})
                        links.append({"source": rec["acc_c"], "target": rec["acc_a"], "value": rec["amt3"]})
                    
                    return {
                        "nodes": [{"id": n, "name": n, "group": 1} for n in nodes],
                        "links": links
                    }
        except Exception as e:
            print(f"Neo4j query error: {e}")
            
    # Mock fallback
    return {
        "nodes": [
            {"id": "ACC_92", "name": "ACC_92", "group": 1},
            {"id": "ACC_11", "name": "ACC_11", "group": 1},
            {"id": "ACC_44", "name": "ACC_44", "group": 2},
            {"id": "ACC_05", "name": "ACC_05", "group": 2},
            {"id": "ACC_73", "name": "ACC_73", "group": 3},
            {"id": "Crypto_Ex", "name": "Crypto Ex", "group": 4}
        ],
        "links": [
            {"source": "ACC_92", "target": "ACC_11", "value": 5000},
            {"source": "ACC_11", "target": "ACC_44", "value": 4500},
            {"source": "ACC_44", "target": "ACC_92", "value": 4000},
            {"source": "ACC_05", "target": "ACC_73", "value": 8000},
            {"source": "ACC_73", "target": "ACC_05", "value": 7500},
            {"source": "ACC_44", "target": "Crypto_Ex", "value": 12000}
        ]
    }

# --- ClickHouse Integration ---
try:
    from clickhouse_driver import Client
    ch_client = Client(host='banking_clickhouse', port=9000, user='banking_user', password='banking_password', database='banking_warehouse')
except Exception as e:
    print(f"ClickHouse connection error: {e}")
    ch_client = None

@app.get("/api/analytics/history")
def get_history_analytics():
    if ch_client:
        try:
            query = """
                SELECT 
                    toDate(event_time) AS date,
                    count() AS total_tx,
                    sum(amount) AS total_amount,
                    sum(if(status='FRAUD', 1, 0)) AS total_fraud
                FROM fct_transactions
                GROUP BY date
                ORDER BY date DESC
                LIMIT 30
            """
            result = ch_client.execute(query)
            data = []
            for row in reversed(result): # Sắp xếp tăng dần theo ngày
                data.append({
                    "date": str(row[0]),
                    "total_tx": row[1],
                    "total_amount": row[2],
                    "total_fraud": row[3]
                })
            if data:
                return data
        except Exception as e:
            print(f"ClickHouse query error: {e}")
            
    # Mock fallback
    import datetime
    data = []
    for i in range(14, -1, -1):
        date = datetime.date.today() - datetime.timedelta(days=i)
        data.append({
            "date": str(date),
            "total_tx": 1000 + (i * 10) % 500,
            "total_amount": 500000 + (i * 5000) % 200000,
            "total_fraud": 5 + i % 10
        })
    return data

# --- Postgres Integration (Case Management) ---
try:
    import psycopg2
    pg_conn = psycopg2.connect(
        host="banking_postgres",
        port=5432,
        dbname="banking_data_platform",
        user="banking_user",
        password="banking_password"
    )
    pg_conn.autocommit = True
except Exception as e:
    print(f"Postgres connection error: {e}")
    pg_conn = None

@app.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not pg_conn:
        raise HTTPException(status_code=500, detail="Database not connected")
    with pg_conn.cursor() as cur:
        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (form_data.username,))
        user = cur.fetchone()
        
    if not user or not verify_password(form_data.password, user[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user[1], "role": user[3], "id": user[0]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user[3], "username": user[1]}

@app.get("/api/alerts")
def get_alerts(current_user: dict = Depends(get_current_user)):
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                if current_user["role"] == "ADMIN":
                    cur.execute("SELECT alert_id, account_id, rule_name, amount, risk_score, status, created_at FROM alerts ORDER BY created_at DESC LIMIT 1000")
                else:
                    cur.execute("SELECT alert_id, account_id, rule_name, amount, risk_score, status, created_at FROM alerts WHERE assignee_id = %s ORDER BY created_at DESC LIMIT 1000", (current_user["id"],))
                
                rows = cur.fetchall()
                data = []
                for row in rows:
                    data.append({
                        "alert_id": row[0],
                        "account_id": row[1],
                        "rule_name": row[2],
                        "amount": row[3],
                        "risk_score": row[4],
                        "status": row[5],
                        "created_at": str(row[6])
                    })
                return data
        except Exception as e:
            print(f"Postgres query error: {e}")

    # Mock fallback
    return [
        {"alert_id": 1, "account_id": "ACC_44", "rule_name": "CIRCULAR_TRANSFER", "amount": 12000.0, "risk_score": 98, "status": "PENDING", "created_at": "2023-10-27 10:00:00"},
        {"alert_id": 2, "account_id": "ACC_11", "rule_name": "HIGH_VELOCITY", "amount": 4500.0, "risk_score": 85, "status": "PENDING", "created_at": "2023-10-27 10:05:00"},
    ]

class AlertStatusUpdate(BaseModel):
    status: str

@app.post("/api/alerts/{alert_id}/status")
def update_alert_status(alert_id: int, update: AlertStatusUpdate, current_user: dict = Depends(get_current_user)):
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("UPDATE alerts SET status = %s WHERE alert_id = %s", (update.status, alert_id))
            return {"message": "Success"}
        except Exception as e:
            print(f"Postgres update error: {e}")
            return {"error": str(e)}
    return {"message": "Mock updated"}

@app.get("/api/alerts/export")
def export_alerts(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN can export reports")
        
    if not pg_conn:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT alert_id, account_id, rule_name, amount, risk_score, status, created_at FROM alerts ORDER BY created_at DESC")
            rows = cur.fetchall()
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Alert ID", "Account ID", "Rule Name", "Amount", "Risk Score", "Status", "Created At"])
            for row in rows:
                writer.writerow(row)
                
            output.seek(0)
            return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=alerts_export.csv"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
