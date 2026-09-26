"""
Banking Command Center API — Entry Point.
This file only initializes the FastAPI app, registers routers, and starts background tasks.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from core.db import pg_conn, graph_driver, ch_client, redis_client, get_s3_client
from core.security import get_password_hash
from services.kafka_client import manager, consume_kafka, simulate_events

# API Routers
from api.auth import router as auth_router
from api.alerts import router as alerts_router
from api.graph import router as graph_router
from api.analytics import router as analytics_router
from api.users import router as users_router
from api.config import router as config_router

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

    # --- Startup ---
    # Run idempotent application migrations. This also repairs databases
    # created before the dashboard schema was mounted by Compose.
    if pg_conn:
        try:
            sql_dir = os.path.join(os.path.dirname(__file__), "sql")
            for migration_name in ("app_schema.sql", "phase6_migration.sql"):
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
    elif os.environ.get("APP_MODE", "integration") != "demo":
        raise RuntimeError("PostgreSQL is required outside demo mode")

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

    # Start the real consumer in every mode. The simulator is opt-in.
    background_tasks.append(asyncio.create_task(consume_kafka()))
    if os.environ.get("ENABLE_MOCK_DATA", "false").lower() == "true":
        background_tasks.append(asyncio.create_task(simulate_events()))

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

# =============================================
# Register Routers
# =============================================
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(graph_router)
app.include_router(analytics_router)
app.include_router(users_router)
app.include_router(config_router)


# =============================================
# WebSocket & Health
# =============================================
@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "clients_connected": len(manager.active_connections)}


@app.get("/api/health/live")
def liveness_check():
    return {"status": "alive"}


@app.get("/api/health/ready")
def readiness_check():
    dependencies = {
        "postgres": pg_conn is not None,
        "neo4j": graph_driver is not None,
        "clickhouse": ch_client is not None,
        "redis": redis_client is not None,
    }
    if not all(dependencies.values()):
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"status": "not_ready", **dependencies})
    return {"status": "ready", **dependencies}
