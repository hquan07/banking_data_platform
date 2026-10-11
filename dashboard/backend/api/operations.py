"""Authenticated operational status endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from core.db import pg_conn
from core.deps import get_current_user
from services.processor_health import load_processor_health


router = APIRouter(
    prefix="/api/operations",
    tags=["Operations"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/processors")
def get_processor_health():
    if pg_conn is None:
        raise HTTPException(status_code=503, detail="Processor health database unavailable")
    try:
        return load_processor_health(pg_conn)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Processor health unavailable") from exc
