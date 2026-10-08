"""
Banking Command Center API — Entry Point.
This file only initializes the FastAPI app, registers routers, and starts background tasks.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Gauge

from core.db import pg_conn, graph_driver, ch_client, redis_client, get_s3_client
from core.security import get_password_hash
from core.deps import resolve_user_token
from core.runtime import APP_MODE, validate_runtime_config
from services.kafka_client import manager, consume_kafka, kafka_ready

# API Routers
from api.auth import router as auth_router
from api.alerts import router as alerts_router
from api.graph import router as graph_router
from api.analytics import router as analytics_router
from api.users import router as users_router
from api.config import router as config_router
from api.datasets import router as datasets_router

import logging
from pythonjsonlogger import jsonlogger

# Configure JSON Logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s'
)
logHandler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[logHandler])
logger = logging.getLogger(__name__)


# =============================================
# Lifespan (replaces deprecated on_event)
# =============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks, yield, then cleanup."""
    background_tasks = []
    validate_runtime_config()

    if pg_conn is None:
        raise RuntimeError("PostgreSQL is required for authentication and alerts")
    with pg_conn.cursor() as cur:
        cur.execute("SELECT 1")
    if redis_client is None or not redis_client.ping():
        raise RuntimeError("Redis is required")
    if graph_driver is None:
        raise RuntimeError("Neo4j is required")
    graph_driver.verify_connectivity()
    if ch_client is None or ch_client.execute("EXISTS TABLE payment_events") != [(1,)]:
        raise RuntimeError("ClickHouse is required")
    if get_s3_client() is None:
        raise RuntimeError("MinIO is required")

    # --- Startup ---
    # Run idempotent application migrations. This also repairs databases
    # created before the dashboard schema was mounted by Compose.
    if pg_conn:
        try:
            sql_dir = os.path.join(os.path.dirname(__file__), "sql")
            for migration_name in ("app_schema.sql", "phase6_migration.sql", "payment_contract.sql", "p1_alert_lifecycle.sql", "p1_dq_results.sql", "p1_trace_context.sql", "dataset_benchmark.sql"):
                migration_path = os.path.join(sql_dir, migration_name)
                if not os.path.exists(migration_path):
                    continue
                with open(migration_path, "r", encoding="utf-8") as f:
                    sql = f.read()
                with pg_conn.cursor() as cur:
                    cur.execute(sql)
                print(f"Migration {migration_name} completed successfully.")
        except Exception as e:
            raise RuntimeError(f"Database migration failed: {e}") from e

    # Initialize default users if not present
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM users")
                if cur.fetchone()[0] == 0:
                    admin_password = os.environ.get("DASHBOARD_ADMIN_PASSWORD")
                    analyst_password = os.environ.get("DASHBOARD_ANALYST_PASSWORD")
                    if not admin_password or not analyst_password:
                        raise RuntimeError("Dashboard passwords must be configured")
                    admin_hash = get_password_hash(admin_password)
                    analyst_hash = get_password_hash(analyst_password)
                    cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", ('admin', admin_hash, 'ADMIN'))
                    cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", ('analyst_1', analyst_hash, 'ANALYST'))
                    cur.execute("UPDATE alerts SET assignee_id = (SELECT id FROM users WHERE username = 'analyst_1')")
        except Exception as e:
            raise RuntimeError(f"Default user initialization failed: {e}") from e

    background_tasks.append(asyncio.create_task(consume_kafka()))
    try:
        await asyncio.wait_for(kafka_ready.wait(), timeout=30)
    except asyncio.TimeoutError as exc:
        for task in background_tasks:
            task.cancel()
        await asyncio.gather(*background_tasks, return_exceptions=True)
        raise RuntimeError("Kafka consumer did not become ready") from exc

    yield

    # --- Shutdown (cleanup if needed) ---
    for task in background_tasks:
        task.cancel()
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)


# =============================================
# App Initialization
# =============================================
app = FastAPI(title="Banking Command Center API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "CORS_ALLOWED_ORIGINS", "http://localhost:5173"
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

DQ_LAST_SUCCESS = Gauge("dq_last_run_success", "Whether the latest customer Silver DQ run passed")
DQ_RUN_PRESENT = Gauge("dq_last_run_present", "Whether a customer Silver DQ result exists")
DQ_LAST_INVALID = Gauge("dq_last_run_invalid_records", "Invalid records in the latest customer Silver DQ run")
DQ_LAST_DUPLICATE_RATE = Gauge("dq_last_run_duplicate_rate", "Duplicate account rate in latest customer Silver DQ run")
ALERT_CASES = Gauge("alert_cases", "Alert cases by rule, status and severity", ("rule", "status", "risk_level"))
SPARK_BATCH_ROWS = Gauge("spark_last_batch_rows", "Rows in latest Spark batch", ("job",))
SPARK_BATCH_DURATION = Gauge("spark_last_batch_duration_seconds", "Latest Spark batch duration", ("job",))
SPARK_BATCH_COMPLETED = Gauge("spark_last_batch_completed_timestamp_seconds", "Latest Spark batch completion time", ("job",))


@app.middleware("http")
async def refresh_dq_metrics(request: Request, call_next):
    if request.url.path == "/metrics" and pg_conn is not None:
        try:
            with pg_conn.cursor() as cur:
                cur.execute(
                    "SELECT success, invalid_count, duplicate_rate FROM dq_run_results "
                    "ORDER BY checked_at DESC LIMIT 1"
                )
                row = cur.fetchone()
            if row:
                DQ_RUN_PRESENT.set(1)
                DQ_LAST_SUCCESS.set(int(row[0]))
                DQ_LAST_INVALID.set(row[1])
                DQ_LAST_DUPLICATE_RATE.set(row[2])
            else:
                DQ_RUN_PRESENT.set(0)
            with pg_conn.cursor() as cur:
                cur.execute(
                    "SELECT rule_name, status, risk_level, count(*) FROM alerts "
                    "GROUP BY rule_name, status, risk_level"
                )
                case_rows = cur.fetchall()
            ALERT_CASES.clear()
            for rule, status, risk_level, count in case_rows:
                ALERT_CASES.labels(rule, status, risk_level).set(count)
        except Exception:
            logger.exception("Could not refresh DQ metrics")
        if redis_client is not None:
            try:
                for job in ("payment_processor", "fraud_velocity"):
                    values = redis_client.hgetall(f"spark:batch:{job}")
                    if values:
                        SPARK_BATCH_DURATION.labels(job).set(float(values["duration_seconds"]))
                        SPARK_BATCH_COMPLETED.labels(job).set(float(values["completed_at"]))
                        if "rows" in values:
                            SPARK_BATCH_ROWS.labels(job).set(float(values["rows"]))
            except Exception:
                logger.exception("Could not refresh Spark batch metrics")
    return await call_next(request)

# =============================================
# Register Routers
# =============================================
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(graph_router)
app.include_router(analytics_router)
app.include_router(users_router)
app.include_router(config_router)
app.include_router(datasets_router)


# =============================================
# WebSocket & Health
# =============================================
@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    protocols = [item.strip() for item in websocket.headers.get("sec-websocket-protocol", "").split(",")]
    if len(protocols) != 2 or protocols[0] != "bearer":
        await websocket.close(code=1008)
        return
    try:
        resolve_user_token(protocols[1])
    except Exception:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, subprotocol="bearer")
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/health")
def health_check():
    return {"status": "healthy" if kafka_ready.is_set() else "degraded", "mode": APP_MODE, "clients_connected": len(manager.active_connections)}


@app.get("/api/health/live")
def liveness_check():
    return {"status": "alive"}


@app.get("/api/health/ready")
def readiness_check():
    from fastapi import HTTPException

    def check(client, probe):
        if client is None:
            return False
        try:
            return probe() is not False
        except Exception:
            return False

    def postgres_probe():
        if pg_conn is None:
            raise RuntimeError("PostgreSQL not connected")
        with pg_conn.cursor() as cur:
            cur.execute("SELECT 1")

    dependencies = {"postgres": check(pg_conn, postgres_probe)}
    s3_client = get_s3_client()
    dependencies.update({
        "kafka": kafka_ready.is_set(),
        "redis": check(redis_client, redis_client.ping if redis_client else None),
        "neo4j": check(graph_driver, graph_driver.verify_connectivity if graph_driver else None),
        "clickhouse": check(ch_client, lambda: ch_client.execute("EXISTS TABLE payment_events") == [(1,)]),
        "minio": check(s3_client, lambda: s3_client.head_bucket(Bucket="evidence")),
    })
    if not all(dependencies.values()):
        raise HTTPException(status_code=503, detail={"status": "not_ready", **dependencies})
    return {"status": "ready", "mode": APP_MODE, **dependencies}
