import asyncio
import json
import os
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaConsumer
from pydantic import BaseModel
from auth import verify_password, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends, HTTPException, status, UploadFile, File
from datetime import timedelta
import csv
import io
from fastapi.responses import StreamingResponse
from typing import Optional, List

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

# --- XAI Helper: Generate mock explanation based on rule and risk_score ---
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

def generate_xai_explanation(rule_name, risk_score, amount):
    """Sinh ra lời giải thích dạng text cho một cảnh báo, giả lập SHAP values."""
    templates = XAI_REASONS.get(rule_name, XAI_REASONS["HIGH_VELOCITY"])
    num_reasons = 2 if risk_score < 85 else 3
    selected = random.sample(templates, min(num_reasons, len(templates)))
    
    reasons = []
    for tmpl in selected:
        reason = tmpl.format(
            pct=random.randint(150, 500),
            time=f"{random.randint(0,5)}:{random.randint(10,59)} AM",
            count=random.randint(3, 8),
            total=f"{amount * random.uniform(2, 5):.0f}",
            hours=random.randint(1, 12),
            conf=random.randint(75, 98),
            mins=random.randint(2, 30),
        )
        reasons.append(reason)
    return json.dumps(reasons, ensure_ascii=False)

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
                        rule = data.get("rule", "ML_MODEL_FRAUD")
                        amount = data.get("amount", 0)
                        risk_score = data.get("risk_score", 90)
                        xai = generate_xai_explanation(rule, risk_score, amount)
                        with pg_conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO alerts (account_id, rule_name, amount, risk_score, xai_explanation) VALUES (%s, %s, %s, %s, %s)",
                                (data.get("account_id"), rule, amount, risk_score, xai)
                            )
                    except Exception as e:
                        print(f"Lỗi lưu Postgres: {e}")
        finally:
            await consumer.stop()
    except Exception as e:
        print(f"Kafka connection failed: {e}. Dashboard will not receive live events.")

# --- Load active rules from DB for mock simulation ---
def get_active_rules():
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

async def simulate_events():
    print("MOCK MODE: Bắt đầu gửi dữ liệu giả lập (High Throughput)...")
    from neo4j import GraphDatabase
    import time
    
    rule_cache = {}
    rule_cache_time = 0
    
    while True:
        # Sinh ngẫu nhiên số lượng giao dịch mỗi giây để đồ thị nhảy múa
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
                "lat": random.uniform(8.5, 23.3),  # VN Latitude
                "lng": random.uniform(102.1, 109.4)  # VN Longitude
            }
            await manager.broadcast({"topic": "payment-events", "data": tx})
            
            # Thỉnh thoảng gửi cảnh báo (dựa trên dynamic rules)
            if random.random() < 0.015:
                active_rule_names = list(rule_cache.keys()) if rule_cache else ["HIGH_VELOCITY", "STRUCTURING_SUSPICION", "CIRCULAR_TRANSFER"]
                rule_name = random.choice(active_rule_names)
                rule_config = rule_cache.get(rule_name, {"threshold": 10000})
                
                alert = {
                    "account_id": tx["account_id"],
                    "rule": rule_name,
                    "amount": tx["amount"],
                    "risk_score": random.randint(70, 99)
                }
                topic = "aml-events" if "STRUCTURING" in alert["rule"] or "CIRCULAR" in alert["rule"] else "fraud-events"
                await manager.broadcast({"topic": topic, "data": alert})
                
                if pg_conn:
                    try:
                        xai = generate_xai_explanation(rule_name, alert["risk_score"], alert["amount"])
                        with pg_conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO alerts (account_id, rule_name, amount, risk_score, xai_explanation) VALUES (%s, %s, %s, %s, %s)",
                                (alert["account_id"], alert["rule"], alert["amount"], alert["risk_score"], xai)
                            )
                    except Exception as e:
                        pass
            
            # Delay một khoảng nhỏ để rải đều giao dịch trong 1 giây
            await asyncio.sleep(1.0 / num_tx)

@app.on_event("startup")
async def startup_event():
    # Run Phase 6 migrations
    if pg_conn:
        try:
            migration_path = os.path.join(os.path.dirname(__file__), "sql", "phase6_migration.sql")
            if os.path.exists(migration_path):
                with open(migration_path, "r") as f:
                    sql = f.read()
                with pg_conn.cursor() as cur:
                    cur.execute(sql)
                print("Phase 6 migration completed successfully.")
        except Exception as e:
            print(f"Phase 6 migration error: {e}")

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

# --- Redis Integration ---
try:
    import redis as redis_module
    redis_client = redis_module.Redis(
        host=os.environ.get("REDIS_HOST", "banking_redis"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    print("Redis connected successfully.")
except Exception as e:
    print(f"Redis connection error: {e}")
    redis_client = None

# --- MinIO (S3-compatible) Integration ---
bucket_name = "evidence"
s3_client = None

def get_s3_client():
    global s3_client
    if s3_client:
        return s3_client
    try:
        import boto3
        from botocore.client import Config as BotoConfig
        s3_client = boto3.client(
            "s3",
            endpoint_url="http://banking_minio:9000",
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin",
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except Exception:
            s3_client.create_bucket(Bucket=bucket_name)
        print("MinIO (S3) connected. Bucket 'evidence' ready.")
        return s3_client
    except Exception as e:
        print(f"MinIO lazy init error: {e}")
        return None

# =============================================
# AUTH APIs
# =============================================
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

# =============================================
# ALERTS APIs (includes XAI + Collaboration)
# =============================================
@app.get("/api/alerts")
def get_alerts(current_user: dict = Depends(get_current_user)):
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                if current_user["role"] == "ADMIN":
                    cur.execute("SELECT alert_id, account_id, rule_name, amount, risk_score, status, created_at, xai_explanation, notes, evidence_file_url, assignee_id FROM alerts ORDER BY created_at DESC LIMIT 1000")
                else:
                    cur.execute("SELECT alert_id, account_id, rule_name, amount, risk_score, status, created_at, xai_explanation, notes, evidence_file_url, assignee_id FROM alerts WHERE assignee_id = %s ORDER BY created_at DESC LIMIT 1000", (current_user["id"],))
                
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
                        "created_at": str(row[6]),
                        "xai_explanation": row[7],
                        "notes": row[8],
                        "evidence_file_url": row[9],
                        "assignee_id": row[10],
                    })
                return data
        except Exception as e:
            print(f"Postgres query error: {e}")

    # Mock fallback
    return [
        {"alert_id": 1, "account_id": "ACC_44", "rule_name": "CIRCULAR_TRANSFER", "amount": 12000.0, "risk_score": 98, "status": "PENDING", "created_at": "2023-10-27 10:00:00", "xai_explanation": None, "notes": None, "evidence_file_url": None, "assignee_id": None},
        {"alert_id": 2, "account_id": "ACC_11", "rule_name": "HIGH_VELOCITY", "amount": 4500.0, "risk_score": 85, "status": "PENDING", "created_at": "2023-10-27 10:05:00", "xai_explanation": None, "notes": None, "evidence_file_url": None, "assignee_id": None},
    ]

class AlertStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    assignee_id: Optional[int] = None

@app.post("/api/alerts/{alert_id}/status")
def update_alert_status(alert_id: int, update: AlertStatusUpdate, current_user: dict = Depends(get_current_user)):
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                # Build dynamic SET clause
                set_parts = ["status = %s"]
                params = [update.status]
                
                if update.notes is not None:
                    set_parts.append("notes = %s")
                    params.append(update.notes)
                
                if update.assignee_id is not None:
                    set_parts.append("assignee_id = %s")
                    params.append(update.assignee_id)
                
                params.append(alert_id)
                query = f"UPDATE alerts SET {', '.join(set_parts)} WHERE alert_id = %s"
                cur.execute(query, tuple(params))
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

# =============================================
# RULES APIs (Dynamic Rule Engine)
# =============================================
class RuleUpdate(BaseModel):
    threshold: Optional[float] = None
    window_seconds: Optional[int] = None
    max_count: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

@app.get("/api/rules")
def get_rules(current_user: dict = Depends(get_current_user)):
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT rule_id, name, description, threshold, window_seconds, max_count, is_active, created_at, updated_at FROM rules ORDER BY rule_id")
                rows = cur.fetchall()
                return [
                    {
                        "rule_id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "threshold": float(row[3]),
                        "window_seconds": row[4],
                        "max_count": row[5],
                        "is_active": row[6],
                        "created_at": str(row[7]),
                        "updated_at": str(row[8]),
                    } for row in rows
                ]
        except Exception as e:
            print(f"Error fetching rules: {e}")
    return []

@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: int, update: RuleUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN can modify rules")
    
    if not pg_conn:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    try:
        set_parts = []
        params = []
        
        if update.threshold is not None:
            set_parts.append("threshold = %s")
            params.append(update.threshold)
        if update.window_seconds is not None:
            set_parts.append("window_seconds = %s")
            params.append(update.window_seconds)
        if update.max_count is not None:
            set_parts.append("max_count = %s")
            params.append(update.max_count)
        if update.is_active is not None:
            set_parts.append("is_active = %s")
            params.append(update.is_active)
        if update.description is not None:
            set_parts.append("description = %s")
            params.append(update.description)
        
        if not set_parts:
            return {"message": "No fields to update"}
        
        set_parts.append("updated_at = NOW()")
        params.append(rule_id)
        
        query = f"UPDATE rules SET {', '.join(set_parts)} WHERE rule_id = %s"
        with pg_conn.cursor() as cur:
            cur.execute(query, tuple(params))
        
        # Publish update event to Redis for Spark/workers to pick up
        if redis_client:
            redis_client.publish("rule_updates", json.dumps({"rule_id": rule_id, "action": "updated"}))
            # Clear cache so next load picks up fresh data
            redis_client.delete("active_rules")
        
        return {"message": "Rule updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# KYC 360° APIs
# =============================================
@app.get("/api/accounts/{account_id}/kyc")
def get_kyc_profile(account_id: str, current_user: dict = Depends(get_current_user)):
    profile = {
        "account_id": account_id,
        "trust_score": None,
        "total_alerts": 0,
        "resolved_alerts": 0,
        "recent_transactions": [],
        "devices": [],
        "network_graph": {"nodes": [], "links": []},
    }
    
    # 1. Postgres: Alert history and trust score
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM alerts WHERE account_id = %s", (account_id,))
                profile["total_alerts"] = cur.fetchone()[0]
                
                cur.execute("SELECT count(*) FROM alerts WHERE account_id = %s AND status = 'RESOLVED'", (account_id,))
                profile["resolved_alerts"] = cur.fetchone()[0]
                
                # Trust score: inverse of alert frequency (simple heuristic)
                if profile["total_alerts"] == 0:
                    profile["trust_score"] = 95
                elif profile["total_alerts"] < 5:
                    profile["trust_score"] = 70
                elif profile["total_alerts"] < 15:
                    profile["trust_score"] = 45
                else:
                    profile["trust_score"] = 20
        except Exception as e:
            print(f"KYC Postgres error: {e}")
    
    # 2. Neo4j: Network graph for this account
    if graph_driver:
        try:
            query = """
            MATCH (a:Account {id: $account_id})-[r:TRANSFERRED_TO]-(b:Account)
            OPTIONAL MATCH (b)-[r2:TRANSFERRED_TO]-(c:Account)
            WHERE c.id <> $account_id
            RETURN DISTINCT a.id AS src, b.id AS dst, type(r) AS rel, r.amount AS amt, c.id AS hop2
            LIMIT 30
            """
            with graph_driver.session() as session:
                result = session.run(query, account_id=account_id)
                records = list(result)
                nodes_set = {account_id}
                links = []
                for rec in records:
                    nodes_set.add(rec["dst"])
                    links.append({"source": rec["src"], "target": rec["dst"], "value": rec.get("amt", 100)})
                    if rec["hop2"]:
                        nodes_set.add(rec["hop2"])
                        links.append({"source": rec["dst"], "target": rec["hop2"], "value": 50})
                
                profile["network_graph"] = {
                    "nodes": [{"id": n, "name": n, "group": 1 if n == account_id else 2} for n in nodes_set],
                    "links": links,
                }
        except Exception as e:
            print(f"KYC Neo4j error: {e}")
    
    # Mock fallback for network graph
    if not profile["network_graph"]["nodes"]:
        mock_peers = [f"ACC_{random.randint(1,100)}" for _ in range(4)]
        profile["network_graph"] = {
            "nodes": [{"id": account_id, "name": account_id, "group": 1}] + [{"id": p, "name": p, "group": 2} for p in mock_peers],
            "links": [{"source": account_id, "target": p, "value": random.randint(500, 8000)} for p in mock_peers],
        }
    
    # 3. Mock recent transactions and devices (would come from ClickHouse in production)
    import datetime
    profile["recent_transactions"] = [
        {"time": str(datetime.datetime.now() - datetime.timedelta(minutes=i*5)), "amount": round(random.uniform(50, 5000), 2), "type": random.choice(["TRANSFER", "PAYMENT", "DEPOSIT"])}
        for i in range(10)
    ]
    profile["devices"] = [
        {"name": "iPhone 15 Pro", "last_seen": "2 giờ trước", "ip": f"103.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"},
        {"name": "Chrome - Windows 11", "last_seen": "5 giờ trước", "ip": f"14.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"},
    ]
    
    if profile["trust_score"] is None:
        profile["trust_score"] = 75
    
    return profile

# =============================================
# MinIO Presigned URL API (Evidence Upload)
# =============================================
@app.get("/api/evidence/presigned-url")
def get_presigned_url(filename: str, alert_id: int, current_user: dict = Depends(get_current_user)):
    client = get_s3_client()
    if not client:
        raise HTTPException(status_code=500, detail="MinIO is not connected")
    
    object_key = f"alerts/{alert_id}/{filename}"
    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket_name, "Key": object_key, "ContentType": "application/octet-stream"},
            ExpiresIn=600,  # 10 minutes
        )
        
        # Also store the expected URL in the alert record
        download_url = f"http://localhost:9001/{bucket_name}/{object_key}"
        if pg_conn:
            try:
                with pg_conn.cursor() as cur:
                    cur.execute("UPDATE alerts SET evidence_file_url = %s WHERE alert_id = %s", (download_url, alert_id))
            except Exception as e:
                print(f"Error saving evidence URL: {e}")
        
        return {"upload_url": url, "download_url": download_url, "object_key": object_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# USERS API (for Assignee dropdown)
# =============================================
@app.get("/api/users")
def get_users(current_user: dict = Depends(get_current_user)):
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT id, username, role FROM users ORDER BY id")
                rows = cur.fetchall()
                return [{"id": row[0], "username": row[1], "role": row[2]} for row in rows]
        except Exception as e:
            print(f"Error fetching users: {e}")
    return []
