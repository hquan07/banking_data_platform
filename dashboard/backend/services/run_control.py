"""Durable pipeline-run queries and state transitions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

try:
    from services.quality_status import run_quality_payload
except ModuleNotFoundError:  # Package import used by unit tests.
    from .quality_status import run_quality_payload


RUN_STATES = frozenset({
    "CREATED", "RUNNING", "PAUSING", "PAUSED",
    "CANCELLING", "CANCELLED", "COMPLETED", "FAILED",
})
TERMINAL_STATES = frozenset({"CANCELLED", "COMPLETED", "FAILED"})
TRANSITIONS = {
    "CREATED": frozenset({"RUNNING", "FAILED"}),
    "RUNNING": frozenset({"PAUSING", "CANCELLING", "COMPLETED", "FAILED"}),
    "PAUSING": frozenset({"PAUSED", "CANCELLING", "FAILED"}),
    "PAUSED": frozenset({"RUNNING", "CANCELLING", "FAILED"}),
    "CANCELLING": frozenset({"CANCELLED", "FAILED"}),
    "CANCELLED": frozenset(),
    "COMPLETED": frozenset(),
    "FAILED": frozenset(),
}
RUN_COLUMNS = (
    "run_id", "status", "version", "owner_user_id", "source_kind",
    "dataset_id", "dataset_version", "dataset_hash", "contract_version",
    "evaluator_version", "requested_rate", "requested_start_offset",
    "requested_end_offset", "created_at", "updated_at", "started_at",
    "paused_at", "cancelled_at", "completed_at", "failed_at", "failure_reason",
)
RUN_SELECT = ", ".join(RUN_COLUMNS)


class RunNotFoundError(LookupError):
    pass


class RunVersionConflictError(RuntimeError):
    pass


class RunTransitionError(ValueError):
    pass


def transition_allowed(old_status: str, new_status: str) -> bool:
    return new_status in TRANSITIONS.get(old_status, frozenset())


def _record(row: Any) -> dict[str, Any]:
    return dict(zip(RUN_COLUMNS, row))


def create_run(connection: Any, values: dict[str, Any], owner_user_id: int) -> dict[str, Any]:
    """Create a run and its immutable CREATED audit event atomically."""
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            WITH created AS (
                INSERT INTO pipeline_runs
                    (owner_user_id, source_kind, dataset_id, dataset_version,
                     dataset_hash, contract_version, evaluator_version,
                     requested_rate, requested_start_offset, requested_end_offset)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {RUN_SELECT}
            ), audit AS (
                INSERT INTO pipeline_run_events
                    (run_id, event_type, old_status, new_status, actor_user_id, details)
                SELECT run_id, 'CREATED', NULL, status, %s, %s::jsonb FROM created
                RETURNING run_id
            )
            SELECT {', '.join('created.' + item for item in RUN_COLUMNS)}
            FROM created JOIN audit USING (run_id)
            """,
            (
                owner_user_id, values["source_kind"], values["dataset_id"],
                values["dataset_version"], values["dataset_hash"],
                values["contract_version"], values["evaluator_version"],
                values["requested_rate"], values.get("requested_start_offset"),
                values.get("requested_end_offset"), owner_user_id,
                json.dumps({"source_kind": values["source_kind"]}),
            ),
        )
        row = cursor.fetchone()
    return _record(row)


def list_runs(
    connection: Any,
    *,
    limit: int,
    offset: int,
    status: str | None = None,
    dataset_id: str | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    clauses, params = [], []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if dataset_id:
        clauses.append("dataset_id = %s")
        params.append(dataset_id)
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM pipeline_runs" + where_sql, params)
        total = cursor.fetchone()[0]
        cursor.execute(
            f"SELECT {RUN_SELECT} FROM pipeline_runs{where_sql} "
            "ORDER BY created_at DESC, run_id DESC LIMIT %s OFFSET %s",
            (*params, limit, offset),
        )
        rows = cursor.fetchall()
        run_records = [_record(row) for row in rows]
        run_ids = [record["run_id"] for record in run_records]
        quality_rows = []
        if run_ids:
            cursor.execute(
                "SELECT checks.run_id, checks.check_id, results.classification, "
                "checks.observed_at, checks.freshness_sla_seconds "
                "FROM pipeline_reconciliation_checks checks "
                "JOIN pipeline_reconciliation_results results USING (check_id) "
                "WHERE checks.run_id = ANY(%s::uuid[])",
                (run_ids,),
            )
            quality_rows = cursor.fetchall()
    now = datetime.now(timezone.utc)
    for record in run_records:
        rows_for_run = [row[1:] for row in quality_rows if row[0] == record["run_id"]]
        record["quality"] = run_quality_payload(record, rows_for_run, now=now)
    return total, run_records


def get_run(connection: Any, run_id: str) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {RUN_SELECT} FROM pipeline_runs WHERE run_id = %s",
            (run_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RunNotFoundError(run_id)
        run = _record(row)
        cursor.execute(
            "SELECT topic, partition, start_offset, end_offset, current_offset, updated_at "
            "FROM pipeline_run_offsets WHERE run_id = %s ORDER BY topic, partition",
            (run_id,),
        )
        run["offsets"] = [
            dict(zip(("topic", "partition", "start_offset", "end_offset", "current_offset", "updated_at"), item))
            for item in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT counter_name, counter_value, updated_at FROM pipeline_run_counters "
            "WHERE run_id = %s ORDER BY counter_name",
            (run_id,),
        )
        run["counters"] = [
            dict(zip(("counter_name", "counter_value", "updated_at"), item))
            for item in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT event_id, event_type, old_status, new_status, actor_user_id, details, created_at "
            "FROM pipeline_run_events WHERE run_id = %s ORDER BY event_id",
            (run_id,),
        )
        run["events"] = [
            dict(zip(("event_id", "event_type", "old_status", "new_status", "actor_user_id", "details", "created_at"), item))
            for item in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT checks.check_id, results.classification, checks.observed_at, "
            "checks.freshness_sla_seconds, checks.store, checks.metric, checks.window_key, "
            "results.expected_count, results.actual_count, results.discrepancy_count, "
            "results.sample_ids FROM pipeline_reconciliation_checks checks "
            "JOIN pipeline_reconciliation_results results USING (check_id) "
            "WHERE checks.run_id = %s ORDER BY checks.store, checks.metric, results.classification",
            (run_id,),
        )
        reconciliation = cursor.fetchall()
        run["reconciliation"] = [
            dict(zip((
                "check_id", "classification", "observed_at", "sla_threshold_seconds",
                "store", "metric", "window_key", "expected_count", "actual_count",
                "discrepancy_count", "sample_ids",
            ), item))
            for item in reconciliation
        ]
        run["quality"] = run_quality_payload(run, [item[:4] for item in reconciliation])
    return run


def transition_run(
    connection: Any,
    run_id: str,
    *,
    expected_version: int,
    new_status: str,
    actor_user_id: int,
    reason: str | None = None,
) -> dict[str, Any]:
    """Apply one state transition with compare-and-swap versioning and audit."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT status, version FROM pipeline_runs WHERE run_id = %s",
            (run_id,),
        )
        existing = cursor.fetchone()
        if existing is None:
            raise RunNotFoundError(run_id)
        old_status, current_version = existing
        if current_version != expected_version:
            raise RunVersionConflictError(run_id)
        if not transition_allowed(old_status, new_status):
            raise RunTransitionError(f"Cannot transition from {old_status} to {new_status}")

        timestamp_column = {
            "RUNNING": "started_at = COALESCE(started_at, NOW())",
            "PAUSED": "paused_at = NOW()",
            "CANCELLED": "cancelled_at = NOW()",
            "COMPLETED": "completed_at = NOW()",
            "FAILED": "failed_at = NOW()",
        }.get(new_status)
        assignments = ["status = %s", "version = version + 1", "updated_at = NOW()"]
        if timestamp_column:
            assignments.append(timestamp_column)
        if new_status == "FAILED":
            assignments.append("failure_reason = %s")
        params: list[Any] = [new_status]
        if new_status == "FAILED":
            params.append(reason)
        details = {"reason": reason} if reason else {}
        cursor.execute(
            f"""
            WITH changed AS (
                UPDATE pipeline_runs SET {', '.join(assignments)}
                WHERE run_id = %s AND version = %s
                RETURNING {RUN_SELECT}
            ), audit AS (
                INSERT INTO pipeline_run_events
                    (run_id, event_type, old_status, new_status, actor_user_id, details)
                SELECT run_id, 'STATE_TRANSITION', %s, status, %s, %s::jsonb FROM changed
                RETURNING run_id
            )
            SELECT {', '.join('changed.' + item for item in RUN_COLUMNS)}
            FROM changed JOIN audit USING (run_id)
            """,
            (*params, run_id, expected_version, old_status, actor_user_id, json.dumps(details)),
        )
        changed = cursor.fetchone()
        if changed is None:
            raise RunVersionConflictError(run_id)
    return _record(changed)
