"""Non-blocking PostgreSQL heartbeat for long-running processors."""

from __future__ import annotations

import atexit
import json
import os
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable


UPSERT_HEARTBEAT = """
    INSERT INTO processor_heartbeats
        (processor_name, instance_id, status, started_at, heartbeat_at,
         last_batch_at, last_success_at, last_error, processed_rows,
         checkpoint_age_seconds, metadata, updated_at)
    VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW())
    ON CONFLICT (processor_name, instance_id) DO UPDATE SET
        status = EXCLUDED.status,
        heartbeat_at = EXCLUDED.heartbeat_at,
        last_batch_at = EXCLUDED.last_batch_at,
        last_success_at = EXCLUDED.last_success_at,
        last_error = EXCLUDED.last_error,
        processed_rows = EXCLUDED.processed_rows,
        checkpoint_age_seconds = EXCLUDED.checkpoint_age_seconds,
        metadata = EXCLUDED.metadata,
        updated_at = NOW()
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_connection():
    import psycopg2

    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "banking_postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
    )


class ProcessorHeartbeat:
    """Publish liveness in a daemon thread without blocking event processing."""

    def __init__(
        self,
        processor_name: str,
        *,
        interval_seconds: float | None = None,
        connection_factory: Callable[[], Any] | None = None,
        instance_id: str | None = None,
    ) -> None:
        if not processor_name or len(processor_name) > 80:
            raise ValueError("processor_name must contain 1-80 characters")
        interval = (
            interval_seconds
            if interval_seconds is not None
            else float(os.environ.get("PROCESSOR_HEARTBEAT_INTERVAL_SECONDS", "15"))
        )
        if interval <= 0:
            raise ValueError("heartbeat interval must be positive")
        self.processor_name = processor_name
        self.instance_id = instance_id or os.environ.get("PROCESSOR_INSTANCE_ID") or (
            f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        )
        self.interval_seconds = interval
        self.connection_factory = connection_factory or _default_connection
        self.started_at = _utcnow()
        self._state: dict[str, Any] = {
            "status": "starting",
            "last_batch_at": None,
            "last_success_at": None,
            "last_error": None,
            "processed_rows": 0,
            "checkpoint_age_seconds": None,
            "metadata": {},
        }
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "ProcessorHeartbeat":
        if self._thread is not None:
            return self
        with self._lock:
            self._state["status"] = "running"
        self._thread = threading.Thread(
            target=self._run,
            name=f"heartbeat-{self.processor_name}",
            daemon=True,
        )
        self._thread.start()
        atexit.register(self.stop)
        return self

    def record_success(
        self,
        *,
        processed_rows: int = 0,
        batch_id: str | int | None = None,
        checkpoint_age_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if processed_rows < 0:
            raise ValueError("processed_rows cannot be negative")
        now = _utcnow()
        with self._lock:
            self._state.update({
                "status": "running",
                "last_batch_at": now,
                "last_success_at": now,
                "last_error": None,
                "processed_rows": self._state["processed_rows"] + processed_rows,
                "checkpoint_age_seconds": checkpoint_age_seconds,
                "metadata": {**self._state["metadata"], **(metadata or {})},
            })
            if batch_id is not None:
                self._state["metadata"]["last_batch_id"] = str(batch_id)
        self._wake.set()

    def record_failure(self, error: BaseException | str) -> None:
        with self._lock:
            self._state["status"] = "failed"
            self._state["last_error"] = str(error)[:2000]
        self._wake.set()

    def stop(self, status: str = "stopped") -> None:
        if status not in {"failed", "stopped"}:
            raise ValueError("terminal heartbeat status must be failed or stopped")
        if self._stop.is_set():
            return
        with self._lock:
            if self._state["status"] != "failed":
                self._state["status"] = status
        self._stop.set()
        self._wake.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=min(self.interval_seconds, 2))
        self._emit()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state, metadata=dict(self._state["metadata"]))

    def _run(self) -> None:
        while not self._stop.is_set():
            self._emit()
            self._wake.wait(self.interval_seconds)
            self._wake.clear()

    def _emit(self) -> bool:
        snapshot = self.snapshot()
        now = _utcnow()
        connection = None
        try:
            connection = self.connection_factory()
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(UPSERT_HEARTBEAT, (
                        self.processor_name,
                        self.instance_id,
                        snapshot["status"],
                        self.started_at,
                        now,
                        snapshot["last_batch_at"],
                        snapshot["last_success_at"],
                        snapshot["last_error"],
                        snapshot["processed_rows"],
                        snapshot["checkpoint_age_seconds"],
                        json.dumps(snapshot["metadata"], separators=(",", ":")),
                    ))
            return True
        except Exception as exc:
            print(json.dumps({
                "event": "processor_heartbeat_unavailable",
                "processor": self.processor_name,
                "error": type(exc).__name__,
            }), flush=True)
            return False
        finally:
            if connection is not None:
                connection.close()
