"""
Configuration router: Rules CRUD and TPS control.
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from core.db import pg_conn, redis_client
from core.deps import get_current_user

router = APIRouter(prefix="/api", tags=["Config"])


class RuleUpdate(BaseModel):
    threshold: Optional[float] = Field(None, ge=0)
    window_seconds: Optional[int] = Field(None, gt=0)
    max_count: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)


@router.get("/rules")
def get_rules(current_user: dict = Depends(get_current_user)):
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT rule_id, name, description, threshold, window_seconds, max_count, is_active, created_at, updated_at FROM rules ORDER BY rule_id")
                rows = cur.fetchall()
                return [
                    {
                        "rule_id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "threshold": float(row[3]),
                        "window_seconds": row[4],
                        "max_count": row[5],
                        "is_active": row[6],
                        "created_at": str(row[7]),
                        "updated_at": str(row[8]),
                    } for row in rows
                ]
        except Exception as e:
            print(f"Error fetching rules: {e}")
            raise HTTPException(status_code=503, detail="Rules database unavailable") from e
    raise HTTPException(status_code=503, detail="Rules database unavailable")


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, update: RuleUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN can modify rules")

    if not pg_conn:
        raise HTTPException(status_code=503, detail="Database not connected")
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    try:
        set_parts = []
        params = []

        if update.threshold is not None:
            set_parts.append("threshold = %s")
            params.append(update.threshold)
        if update.window_seconds is not None:
            set_parts.append("window_seconds = %s")
            params.append(update.window_seconds)
        if update.max_count is not None:
            set_parts.append("max_count = %s")
            params.append(update.max_count)
        if update.is_active is not None:
            set_parts.append("is_active = %s")
            params.append(update.is_active)
        if update.description is not None:
            set_parts.append("description = %s")
            params.append(update.description)

        if not set_parts:
            return {"message": "No fields to update"}

        set_parts.append("updated_at = NOW()")
        params.append(rule_id)

        query = f"UPDATE rules SET {', '.join(set_parts)} WHERE rule_id = %s"
        with pg_conn.cursor() as cur:
            cur.execute(query, tuple(params))

        # Publish update event to Redis for Spark/workers to pick up
        if redis_client:
            redis_client.publish("rule_updates", json.dumps({"rule_id": rule_id, "action": "updated"}))
            redis_client.delete("active_rules")

        return {"message": "Rule updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
