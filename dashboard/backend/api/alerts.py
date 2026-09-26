"""
Alerts CRUD, export, and evidence upload router.
"""
import csv
import io
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.db import pg_conn, get_s3_client, EVIDENCE_BUCKET
from core.deps import get_current_user

router = APIRouter(prefix="/api", tags=["Alerts"])


from pydantic import BaseModel, Field
class AlertStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(PENDING|INVESTIGATING|RESOLVED|IGNORED)$")
    notes: Optional[str] = Field(None, max_length=1000)
    assignee_id: Optional[int] = Field(None, gt=0)


@router.get("/alerts")
def get_alerts(page: int = 1, limit: int = 50, current_user: dict = Depends(get_current_user)):
    offset = (page - 1) * limit
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                if current_user["role"] == "ADMIN":
                    cur.execute("SELECT COUNT(*) FROM alerts")
                    total = cur.fetchone()[0]
                    cur.execute("SELECT alert_id, account_id, rule_name, amount, risk_score, status, created_at, xai_explanation, notes, evidence_file_url, assignee_id FROM alerts ORDER BY created_at DESC LIMIT %s OFFSET %s", (limit, offset))
                else:
                    cur.execute("SELECT COUNT(*) FROM alerts WHERE assignee_id = %s", (current_user["id"],))
                    total = cur.fetchone()[0]
                    cur.execute("SELECT alert_id, account_id, rule_name, amount, risk_score, status, created_at, xai_explanation, notes, evidence_file_url, assignee_id FROM alerts WHERE assignee_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s", (current_user["id"], limit, offset))

                rows = cur.fetchall()
                data = []
                for row in rows:
                    data.append({
                        "alert_id": row[0],
                        "account_id": row[1],
                        "rule_name": row[2],
                        "amount": row[3],
                        "risk_score": row[4],
                        "status": row[5],
                        "created_at": str(row[6]),
                        "xai_explanation": row[7],
                        "notes": row[8],
                        "evidence_file_url": row[9],
                        "assignee_id": row[10],
                    })
                return {"total": total, "page": page, "limit": limit, "data": data}
        except Exception as e:
            print(f"Postgres query error: {e}")

    # Mock fallback
    return [
        {"alert_id": 1, "account_id": "ACC_44", "rule_name": "CIRCULAR_TRANSFER", "amount": 12000.0, "risk_score": 98, "status": "PENDING", "created_at": "2023-10-27 10:00:00", "xai_explanation": None, "notes": None, "evidence_file_url": None, "assignee_id": None},
        {"alert_id": 2, "account_id": "ACC_11", "rule_name": "HIGH_VELOCITY", "amount": 4500.0, "risk_score": 85, "status": "PENDING", "created_at": "2023-10-27 10:05:00", "xai_explanation": None, "notes": None, "evidence_file_url": None, "assignee_id": None},
    ]


@router.post("/alerts/{alert_id}/status")
def update_alert_status(alert_id: int, update: AlertStatusUpdate, current_user: dict = Depends(get_current_user)):
    allowed_statuses = {"PENDING", "INVESTIGATING", "RESOLVED", "IGNORED"}
    if update.status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Invalid alert status")
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute(
                    "SELECT status, assignee_id FROM alerts WHERE alert_id = %s",
                    (alert_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    raise HTTPException(status_code=404, detail="Alert not found")
                # Strict Workflow State Machine
                old_status = existing[0]
                existing_assignee = existing[1]
                
                valid_transitions = {
                    "PENDING": {"INVESTIGATING", "IGNORED"},
                    "INVESTIGATING": {"RESOLVED", "IGNORED"},
                    "RESOLVED": set(),
                    "IGNORED": set()
                }
                
                if update.status != old_status and update.status not in valid_transitions.get(old_status, set()):
                    raise HTTPException(status_code=422, detail=f"Strict Workflow: Cannot transition from {old_status} to {update.status}")
                
                if current_user["role"] != "ADMIN" and existing_assignee != current_user["id"]:
                    raise HTTPException(status_code=403, detail="Alert is outside your scope")
                if update.assignee_id is not None and current_user["role"] != "ADMIN":
                    raise HTTPException(status_code=403, detail="Only ADMIN can assign alerts")
                set_parts = ["status = %s"]
                params = [update.status]

                if update.notes is not None:
                    set_parts.append("notes = %s")
                    params.append(update.notes)

                if update.assignee_id is not None:
                    set_parts.append("assignee_id = %s")
                    params.append(update.assignee_id)

                set_parts.append("updated_at = NOW()")
                if update.status == "RESOLVED":
                    set_parts.append("resolved_at = NOW()")

                params.append(alert_id)
                query = f"UPDATE alerts SET {', '.join(set_parts)} WHERE alert_id = %s"
                cur.execute(query, tuple(params))
                
                # Determine audit action
                import json
                audit_action = "STATUS_UPDATE"
                if update.assignee_id is not None and update.assignee_id != existing_assignee:
                    audit_action = "ASSIGNMENT_UPDATE"
                if update.status != old_status and update.assignee_id is not None and update.assignee_id != existing_assignee:
                    audit_action = "STATUS_AND_ASSIGNMENT_UPDATE"
                    
                cur.execute(
                    """
                    INSERT INTO alert_audit_log
                        (alert_id, actor_user_id, action, old_status, new_status, details)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        alert_id,
                        current_user["id"],
                        audit_action,
                        old_status,
                        update.status,
                        json.dumps({
                            "notes": update.notes,
                            "assignee_id": update.assignee_id
                        }),
                    ),
                )
            return {"message": "Success"}
        except Exception as e:
            print(f"Postgres update error: {e}")
            return {"error": str(e)}
    return {"message": "Mock updated"}


@router.get("/alerts/export")
def export_alerts(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN can export reports")

    if not pg_conn:
        raise HTTPException(status_code=500, detail="Database not connected")

    try:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT alert_id, account_id, rule_name, amount, risk_score, status, created_at FROM alerts ORDER BY created_at DESC")
            rows = cur.fetchall()

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Alert ID", "Account ID", "Rule Name", "Amount", "Risk Score", "Status", "Created At"])
            for row in rows:
                writer.writerow(row)

            output.seek(0)
            return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=alerts_export.csv"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence/presigned-url")
def get_presigned_url(filename: str, alert_id: int, current_user: dict = Depends(get_current_user)):
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename or len(safe_name) > 255:
        raise HTTPException(status_code=422, detail="Invalid filename")
    if pg_conn:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT assignee_id FROM alerts WHERE alert_id = %s", (alert_id,))
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        if current_user["role"] != "ADMIN" and row[0] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Alert is outside your scope")
    client = get_s3_client()
    if not client:
        raise HTTPException(status_code=500, detail="MinIO is not connected")

    object_key = f"alerts/{alert_id}/{safe_name}"
    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": EVIDENCE_BUCKET, "Key": object_key, "ContentType": "application/octet-stream"},
            ExpiresIn=600,
        )

        download_url = f"{os.environ.get('MINIO_PUBLIC_ENDPOINT', 'http://localhost:9000')}/{EVIDENCE_BUCKET}/{object_key}"
        if pg_conn:
            try:
                with pg_conn.cursor() as cur:
                    cur.execute("UPDATE alerts SET evidence_file_url = %s WHERE alert_id = %s", (download_url, alert_id))
            except Exception as e:
                print(f"Error saving evidence URL: {e}")

        return {"upload_url": url, "download_url": download_url, "object_key": object_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
