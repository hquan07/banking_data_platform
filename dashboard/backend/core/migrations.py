"""Ordered, idempotent application migration runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any


MIGRATIONS = (
    "app_schema.sql",
    "phase6_migration.sql",
    "payment_contract.sql",
    "p1_alert_lifecycle.sql",
    "p1_dq_results.sql",
    "p1_trace_context.sql",
    "dataset_benchmark.sql",
    "dataset_model_candidates.sql",
    "p2_runtime_observability.sql",
    "p2_run_control.sql",
    "p2_run_aware_replay.sql",
    "p2_reconciliation.sql",
    "p2_investigation_cases.sql",
    "p2_temporal_graph_evidence.sql",
    "p2_retention_controls.sql",
    "p2_security_controls.sql",
)


def apply_migrations(connection: Any, sql_dir: Path | None = None) -> list[str]:
    directory = sql_dir or Path(__file__).resolve().parents[1] / "sql"
    applied = []
    for migration_name in MIGRATIONS:
        migration_path = directory / migration_name
        if not migration_path.exists():
            continue
        with connection.cursor() as cursor:
            cursor.execute(migration_path.read_text(encoding="utf-8"))
        applied.append(migration_name)
    return applied

