"""Build the operator-facing status of durable processor heartbeats."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


REQUIRED_PROCESSORS = (
    "payment_processor",
    "fraud_engine",
    "benchmark_processor",
    "live_graph_processor",
    "benchmark_graph_processor",
)


def processor_health_payload(
    rows: list[tuple[Any, ...]],
    *,
    now: datetime | None = None,
    stale_after_seconds: float | None = None,
    required_processors: tuple[str, ...] = REQUIRED_PROCESSORS,
) -> dict[str, Any]:
    observed_at = now or datetime.now(timezone.utc)
    stale_after = (
        stale_after_seconds
        if stale_after_seconds is not None
        else float(os.environ.get("PROCESSOR_HEARTBEAT_STALE_SECONDS", "45"))
    )
    if stale_after <= 0:
        raise ValueError("stale heartbeat threshold must be positive")
    latest = {row[0]: row for row in rows}
    processors = []
    for name in required_processors:
        row = latest.get(name)
        if row is None:
            processors.append({
                "processor_name": name,
                "status": "missing",
                "heartbeat_age_seconds": None,
                "last_batch_at": None,
                "last_success_at": None,
                "last_error": None,
                "processed_rows": 0,
                "checkpoint_age_seconds": None,
                "metadata": {},
            })
            continue
        heartbeat_at = row[4]
        if heartbeat_at.tzinfo is None:
            heartbeat_at = heartbeat_at.replace(tzinfo=timezone.utc)
        age = max(0.0, (observed_at - heartbeat_at).total_seconds())
        raw_status = row[2]
        status = "stale" if age > stale_after and raw_status != "failed" else raw_status
        processors.append({
            "processor_name": name,
            "instance_id": row[1],
            "status": status,
            "heartbeat_at": heartbeat_at.isoformat(),
            "heartbeat_age_seconds": round(age, 3),
            "last_batch_at": row[5].isoformat() if row[5] else None,
            "last_success_at": row[6].isoformat() if row[6] else None,
            "last_error": row[7],
            "processed_rows": row[8],
            "checkpoint_age_seconds": row[9],
            "metadata": row[10] or {},
        })
    healthy = all(item["status"] == "running" for item in processors)
    return {
        "status": "ready" if healthy else "degraded",
        "observed_at": observed_at.isoformat(),
        "stale_after_seconds": stale_after,
        "processors": processors,
    }


def load_processor_health(connection: Any) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT ON (processor_name)
                   processor_name, instance_id, status, started_at, heartbeat_at,
                   last_batch_at, last_success_at, last_error, processed_rows,
                   checkpoint_age_seconds, metadata
            FROM processor_heartbeats
            ORDER BY processor_name, heartbeat_at DESC
            """
        )
        rows = cursor.fetchall()
    return processor_health_payload(rows)
