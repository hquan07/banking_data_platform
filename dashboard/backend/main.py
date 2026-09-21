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

from core.db import pg_conn
from core.security import get_password_hash
from services.kafka_client import manager, consume_kafka, simulate_events

# API Routers
from api.auth import router as auth_router
from api.alerts import router as alerts_router
from api.graph import router as graph_router
from api.analytics import router as analytics_router
from api.users import router as users_router
from api.config import router as config_router


# =============================================
# Lifespan (replaces deprecated on_event)
# =============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks, yield, then cleanup."""
    # --- Startup ---
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
                    cur.execute("UPDATE alerts SET assignee_id = (SELECT id FROM users WHERE username = 'analyst_1')")
        except Exception as e:
            print("Init users error:", e)

    # Start background tasks
    asyncio.create_task(consume_kafka())
    asyncio.create_task(simulate_events())

    yield  # App is running

    # --- Shutdown (cleanup if needed) ---


# =============================================
# App Initialization
# =============================================
app = FastAPI(title="Banking Command Center API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
