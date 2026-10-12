"""Authenticated API for durable pipeline-run control."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel, Field, model_validator

from core.db import pg_conn
from core.deps import get_current_user
from services.run_control import (
    RUN_STATES,
    RunNotFoundError,
    RunLegalHoldError,
    RunTransitionError,
    RunVersionConflictError,
    create_run,
    get_run,
    list_runs,
    set_legal_hold,
    transition_run,
)


router = APIRouter(prefix="/api/runs", tags=["Pipeline runs"])


class RunCreate(BaseModel):
    source_kind: Literal["BENCHMARK_REPLAY", "LIVE_INGESTION", "MANUAL_REPLAY"]
    dataset_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    dataset_version: str = Field(..., min_length=1, max_length=120)
    dataset_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    contract_version: int = Field(..., ge=1)
    evaluator_version: str = Field(..., min_length=1, max_length=120)
    requested_rate: float = Field(..., ge=0, le=100000)
    requested_start_offset: int | None = Field(None, ge=0)
    requested_end_offset: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_offset_range(self):
        if (
            self.requested_start_offset is not None
            and self.requested_end_offset is not None
            and self.requested_end_offset < self.requested_start_offset
        ):
            raise ValueError("requested_end_offset must be at least requested_start_offset")
        return self


class RunTransition(BaseModel):
    status: Literal[
        "RUNNING", "PAUSING", "PAUSED", "CANCELLING",
        "CANCELLED", "COMPLETED", "FAILED",
    ]
    version: int = Field(..., ge=1)
    reason: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def require_failure_reason(self):
        if self.status == "FAILED" and not (self.reason and self.reason.strip()):
            raise ValueError("reason is required when status is FAILED")
        return self


class RunLegalHold(BaseModel):
    enabled: bool
    version: int = Field(..., ge=1)
    reason: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def require_hold_reason(self):
        if self.enabled and not (self.reason and self.reason.strip()):
            raise ValueError("reason is required when enabling legal hold")
        return self


def _connection():
    if pg_conn is None:
        raise HTTPException(status_code=503, detail="Run-control database unavailable")
    return pg_conn


def require_admin(current_user: dict) -> None:
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="ADMIN role required")


@router.get("")
def get_runs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    dataset_id: str | None = Query(None, max_length=64),
    current_user: dict = Depends(get_current_user),
):
    if status is not None and status not in RUN_STATES:
        raise HTTPException(status_code=422, detail="Unsupported run status")
    total, rows = list_runs(
        _connection(), limit=limit, offset=(page - 1) * limit,
        status=status, dataset_id=dataset_id,
    )
    return {"total": total, "page": page, "limit": limit, "data": rows}


@router.get("/{run_id}")
def get_run_detail(run_id: UUID, current_user: dict = Depends(get_current_user)):
    try:
        return get_run(_connection(), str(run_id))
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pipeline run not found") from exc


@router.post("", status_code=http_status.HTTP_201_CREATED)
def post_run(payload: RunCreate, current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    return create_run(_connection(), payload.model_dump(), current_user["id"])


@router.post("/{run_id}/transition")
def post_run_transition(
    run_id: UUID,
    payload: RunTransition,
    current_user: dict = Depends(get_current_user),
):
    require_admin(current_user)
    try:
        return transition_run(
            _connection(), str(run_id), expected_version=payload.version,
            new_status=payload.status, actor_user_id=current_user["id"],
            reason=payload.reason.strip() if payload.reason else None,
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pipeline run not found") from exc
    except RunVersionConflictError as exc:
        raise HTTPException(
            status_code=409, detail="Pipeline run changed; refresh before updating",
        ) from exc
    except RunTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{run_id}/legal-hold")
def post_run_legal_hold(
    run_id: UUID,
    payload: RunLegalHold,
    current_user: dict = Depends(get_current_user),
):
    require_admin(current_user)
    try:
        return set_legal_hold(
            _connection(), str(run_id), expected_version=payload.version,
            enabled=payload.enabled, reason=payload.reason,
            actor_user_id=current_user["id"],
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pipeline run not found") from exc
    except RunVersionConflictError as exc:
        raise HTTPException(
            status_code=409, detail="Pipeline run changed; refresh before updating",
        ) from exc
    except RunLegalHoldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
