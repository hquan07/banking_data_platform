"""Authenticated case-detail, assignment, comment and disposition API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.db import pg_conn
from core.deps import get_current_user
from services.case_records import (
    CaseNotFoundError,
    CaseScopeError,
    CaseTransitionError,
    CaseVersionConflictError,
    add_comment,
    assign_case,
    close_case,
    get_case,
    update_case_metadata,
)


router = APIRouter(prefix="/api/alerts", tags=["Investigation cases"])


class CaseMetadataUpdate(BaseModel):
    version: int = Field(..., ge=1)
    priority: Optional[str] = Field(None, pattern="^P[1-4]$")
    due_at: Optional[datetime] = None


class CaseAssignmentUpdate(BaseModel):
    version: int = Field(..., ge=1)
    assignee_id: Optional[int] = Field(..., gt=0)


class CaseCommentCreate(BaseModel):
    version: int = Field(..., ge=1)
    body: str = Field(..., min_length=1, max_length=2000)


class CaseDispositionUpdate(BaseModel):
    version: int = Field(..., ge=1)
    disposition: str = Field(
        ..., pattern="^(CONFIRMED_FRAUD|FALSE_POSITIVE|DUPLICATE|NO_ACTION|REFERRED)$"
    )
    resolution_code: str = Field(
        ...,
        pattern=(
            "^(FRAUD_CONFIRMED|FALSE_POSITIVE|DUPLICATE_CASE|"
            "INSUFFICIENT_EVIDENCE|REFERRED_TO_COMPLIANCE)$"
        ),
    )


def _connection():
    if pg_conn is None:
        raise HTTPException(status_code=503, detail="Case database unavailable")
    return pg_conn


def _raise_case_error(error: Exception):
    if isinstance(error, CaseNotFoundError):
        raise HTTPException(status_code=404, detail="Case not found") from error
    if isinstance(error, CaseScopeError):
        raise HTTPException(status_code=403, detail=str(error) or "Case is outside your scope") from error
    if isinstance(error, CaseVersionConflictError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    if isinstance(error, CaseTransitionError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    raise error


@router.get("/{alert_id}")
def case_detail(alert_id: int, current_user: dict = Depends(get_current_user)):
    try:
        return get_case(_connection(), alert_id, current_user)
    except (CaseNotFoundError, CaseScopeError) as error:
        _raise_case_error(error)


@router.patch("/{alert_id}")
def update_case(
    alert_id: int,
    payload: CaseMetadataUpdate,
    current_user: dict = Depends(get_current_user),
):
    changes = {
        field: getattr(payload, field)
        for field in ("priority", "due_at")
        if field in payload.model_fields_set
    }
    if payload.due_at is not None and payload.due_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="due_at must include a timezone")
    try:
        return update_case_metadata(
            _connection(), alert_id, expected_version=payload.version,
            actor=current_user, changes=changes,
        )
    except (CaseNotFoundError, CaseScopeError, CaseVersionConflictError, CaseTransitionError) as error:
        _raise_case_error(error)


@router.post("/{alert_id}/assignment")
def update_assignment(
    alert_id: int,
    payload: CaseAssignmentUpdate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return assign_case(
            _connection(), alert_id, expected_version=payload.version,
            assignee_id=payload.assignee_id, actor=current_user,
        )
    except (CaseNotFoundError, CaseScopeError, CaseVersionConflictError, CaseTransitionError) as error:
        _raise_case_error(error)


@router.post("/{alert_id}/comments", status_code=201)
def create_comment(
    alert_id: int,
    payload: CaseCommentCreate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return add_comment(
            _connection(), alert_id, expected_version=payload.version,
            body=payload.body, actor=current_user,
        )
    except (CaseNotFoundError, CaseScopeError, CaseVersionConflictError, CaseTransitionError) as error:
        _raise_case_error(error)


@router.post("/{alert_id}/disposition")
def apply_disposition(
    alert_id: int,
    payload: CaseDispositionUpdate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return close_case(
            _connection(), alert_id, expected_version=payload.version,
            disposition=payload.disposition, resolution_code=payload.resolution_code,
            actor=current_user,
        )
    except (CaseNotFoundError, CaseScopeError, CaseVersionConflictError, CaseTransitionError) as error:
        _raise_case_error(error)
