"""Read-only API for audited retention executions."""

from fastapi import APIRouter, Depends, HTTPException, Query

from core.db import pg_conn
from core.deps import get_current_user


router = APIRouter(prefix="/api/retention", tags=["Retention"])


def _admin(current_user: dict) -> None:
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="ADMIN role required")


@router.get("/executions")
def list_retention_executions(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    _admin(current_user)
    if pg_conn is None:
        raise HTTPException(status_code=503, detail="Retention control plane unavailable")
    with pg_conn.cursor() as cursor:
        cursor.execute(
            "SELECT execution_id, mode, status, source, cutoff_at, requested_by, "
            "approved_dry_run_id, candidate_fingerprint, candidate_run_ids, summary, "
            "error_message, started_at, finished_at FROM retention_executions "
            "ORDER BY started_at DESC, execution_id DESC LIMIT %s",
            (limit,),
        )
        columns = [item.name for item in cursor.description]
        executions = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {"data": executions, "limit": limit}


@router.get("/executions/{execution_id}")
def get_retention_execution(
    execution_id: str,
    current_user: dict = Depends(get_current_user),
):
    _admin(current_user)
    if pg_conn is None:
        raise HTTPException(status_code=503, detail="Retention control plane unavailable")
    with pg_conn.cursor() as cursor:
        cursor.execute(
            "SELECT execution_id, mode, status, source, cutoff_at, requested_by, "
            "approved_dry_run_id, candidate_fingerprint, candidate_run_ids, summary, "
            "error_message, started_at, finished_at FROM retention_executions "
            "WHERE execution_id::text = %s",
            (execution_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Retention execution not found")
        columns = [item.name for item in cursor.description]
        execution = dict(zip(columns, row))
        cursor.execute(
            "SELECT store, candidate_count, protected_count, deleted_count, details "
            "FROM retention_execution_items WHERE execution_id::text = %s ORDER BY store",
            (execution_id,),
        )
        execution["items"] = [
            dict(zip(("store", "candidate_count", "protected_count", "deleted_count", "details"), item))
            for item in cursor.fetchall()
        ]
    return execution
