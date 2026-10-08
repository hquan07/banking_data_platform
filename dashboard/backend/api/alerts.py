"""
Alerts CRUD, export, and evidence upload router.
"""
import csv
import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.db import pg_conn, get_s3_client, EVIDENCE_BUCKET
from core.deps import get_current_user
from core.runtime import demo_mode
from services.alert_lifecycle import transition_allowed

router = APIRouter(prefix="/api", tags=["Alerts"])


from pydantic import Field
class AlertStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(PENDING|INVESTIGATING|RESOLVED|IGNORED)$")
    version: int = Field(..., ge=1)
    notes: Optional[str] = Field(None, max_length=1000)
    assignee_id: Optional[int] = Field(None, gt=0)


@router.get("/alerts")
def get_alerts(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    account_id: Optional[str] = None, payment_id: Optional[str] = None,
    rule: Optional[str] = None, status: Optional[str] = None,
    risk_level: Optional[str] = None,
    created_from: Optional[datetime] = None, created_to: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
):
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="created_from must precede created_to")
    offset = (page - 1) * limit
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                clauses, params = [], []
                if current_user["role"] != "ADMIN":
                    clauses.append("assignee_id = %s")
                    params.append(current_user["id"])
                for column, value in (("account_id", account_id), ("payment_id", payment_id),
                                      ("rule_name", rule), ("status", status), ("risk_level", risk_level)):
                    if value:
                        clauses.append(f"{column} = %s")
                        params.append(value)
                if created_from:
                    clauses.append("created_at >= %s")
                    params.append(created_from)
                if created_to:
                    clauses.append("created_at <= %s")
                    params.append(created_to)
                where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
                cur.execute("SELECT COUNT(*) FROM alerts" + where_sql, params)
                total = cur.fetchone()[0]
                cur.execute(
                    "SELECT alert_id, account_id, rule_name, amount, risk_score, status, created_at, "
                    "xai_explanation, notes, evidence_file_url, assignee_id, version, payment_id, risk_level "
                    "FROM alerts" + where_sql + " ORDER BY created_at DESC, alert_id DESC LIMIT %s OFFSET %s",
                    (*params, limit, offset),
                )
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
                        "version": row[11],
                        "payment_id": row[12],
                        "risk_level": row[13],
                    })
                return {"total": total, "page": page, "limit": limit, "data": data}
        except Exception as e:
            print(f"Postgres query error: {e}")
            if not demo_mode():
                raise HTTPException(status_code=503, detail="Alerts database unavailable") from e

    if not demo_mode():
        raise HTTPException(status_code=503, detail="Alerts database unavailable")
    # Demo-only sample data
    data = [
        {"alert_id": 1, "account_id": "ACC_44", "rule_name": "CIRCULAR_TRANSFER", "amount": 12000.0, "risk_score": 98, "status": "PENDING", "created_at": "2023-10-27 10:00:00", "xai_explanation": None, "notes": None, "evidence_file_url": None, "assignee_id": None},
        {"alert_id": 2, "account_id": "ACC_11", "rule_name": "HIGH_VELOCITY", "amount": 4500.0, "risk_score": 85, "status": "PENDING", "created_at": "2023-10-27 10:05:00", "xai_explanation": None, "notes": None, "evidence_file_url": None, "assignee_id": None},
    ]
    return {"total": len(data), "page": page, "limit": limit, "data": data}


@router.post("/alerts/{alert_id}/status")
def update_alert_status(alert_id: int, update: AlertStatusUpdate, current_user: dict = Depends(get_current_user)):
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute(
                    "SELECT status, assignee_id, version, notes FROM alerts WHERE alert_id = %s",
                    (alert_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    raise HTTPException(status_code=404, detail="Alert not found")
                old_status, existing_assignee, version, old_notes = existing
                if update.version != version:
                    raise HTTPException(status_code=409, detail="Alert changed; refresh before updating")
                if not transition_allowed(old_status, update.status):
                    raise HTTPException(status_code=422, detail=f"Cannot transition from {old_status} to {update.status}")
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

                set_parts.extend(("updated_at = NOW()", "version = version + 1"))
                if update.status == "RESOLVED":
                    set_parts.append("resolved_at = NOW()")

                details = {
                    "old_assignee_id": existing_assignee,
                    "new_assignee_id": update.assignee_id if update.assignee_id is not None else existing_assignee,
                    "old_notes": old_notes,
                    "new_notes": update.notes if update.notes is not None else old_notes,
                }
                cur.execute(
                    f"""WITH changed AS (
                        UPDATE alerts SET {', '.join(set_parts)}
                        WHERE alert_id = %s AND version = %s
                        RETURNING alert_id, version
                    ), audit AS (
                        INSERT INTO alert_audit_log
                            (alert_id, actor_user_id, action, old_status, new_status, details)
                        SELECT alert_id, %s, 'CASE_UPDATE', %s, %s, %s::jsonb FROM changed
                        RETURNING audit_id
                    )
                    SELECT changed.version FROM changed JOIN audit ON TRUE""",
                    (*params, alert_id, update.version, current_user["id"], old_status,
                     update.status, json.dumps(details)),
                )
                changed = cur.fetchone()
                if not changed:
                    raise HTTPException(status_code=409, detail="Alert changed; refresh before updating")
            return {"message": "Success", "version": changed[0]}
        except HTTPException:
            raise
        except Exception as e:
            print(f"Postgres update error: {e}")
            raise HTTPException(status_code=503, detail="Alerts database unavailable") from e
    raise HTTPException(status_code=503, detail="Alerts database unavailable")


@router.get("/alerts/{alert_id}/history")
def get_alert_history(alert_id: int, current_user: dict = Depends(get_current_user)):
    if not pg_conn:
        raise HTTPException(status_code=503, detail="Alerts database unavailable")
    with pg_conn.cursor() as cur:
        cur.execute("SELECT assignee_id FROM alerts WHERE alert_id = %s", (alert_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        if current_user["role"] != "ADMIN" and row[0] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Alert is outside your scope")
        cur.execute(
            "SELECT audit_id, actor_user_id, action, old_status, new_status, details, created_at "
            "FROM alert_audit_log WHERE alert_id = %s ORDER BY created_at, audit_id",
            (alert_id,),
        )
        rows = cur.fetchall()
    return [
        {"audit_id": r[0], "actor_user_id": r[1], "action": r[2], "old_status": r[3],
         "new_status": r[4], "details": r[5], "created_at": r[6].isoformat()}
        for r in rows
    ]


@router.get("/alerts/export")
def export_alerts(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN can export reports")

    if not pg_conn:
        raise HTTPException(status_code=503, detail="Database not connected")

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
    if not pg_conn:
        raise HTTPException(status_code=503, detail="Alerts database unavailable")
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
        import boto3
        from botocore.config import Config

        public_client = boto3.client(
            "s3",
            endpoint_url=os.environ.get("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000"),
            aws_access_key_id=os.environ["MINIO_ROOT_USER"],
            aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
            region_name="us-east-1",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        url = public_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": EVIDENCE_BUCKET, "Key": object_key, "ContentType": "application/octet-stream"},
            ExpiresIn=600,
        )

        return {"upload_url": url, "object_key": object_key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail="Evidence service unavailable") from e


class EvidenceComplete(BaseModel):
    object_key: str = Field(..., min_length=1, max_length=500)


@router.post("/alerts/{alert_id}/evidence/complete")
def complete_evidence(alert_id: int, payload: EvidenceComplete, current_user: dict = Depends(get_current_user)):
    prefix = f"alerts/{alert_id}/"
    filename = payload.object_key.removeprefix(prefix)
    if not payload.object_key.startswith(prefix) or not filename or Path(filename).name != filename:
        raise HTTPException(status_code=422, detail="Invalid evidence object key")
    if not pg_conn:
        raise HTTPException(status_code=503, detail="Alerts database unavailable")
    with pg_conn.cursor() as cur:
        cur.execute("SELECT assignee_id FROM alerts WHERE alert_id = %s", (alert_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    if current_user["role"] != "ADMIN" and row[0] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Alert is outside your scope")
    client = get_s3_client()
    if not client:
        raise HTTPException(status_code=503, detail="Evidence store unavailable")
    try:
        metadata = client.head_object(Bucket=EVIDENCE_BUCKET, Key=payload.object_key)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Evidence object not uploaded") from exc
    download_url = f"{os.environ.get('MINIO_PUBLIC_ENDPOINT', 'http://localhost:9000')}/{EVIDENCE_BUCKET}/{payload.object_key}"
    try:
        with pg_conn.cursor() as cur:
            cur.execute(
                """WITH inserted AS (
                    INSERT INTO evidence_files
                        (alert_id, object_key, original_filename, content_type, size_bytes, uploaded_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (object_key) DO NOTHING RETURNING alert_id
                ), changed AS (
                    UPDATE alerts SET evidence_file_url = %s, version = version + 1, updated_at = NOW()
                    WHERE alert_id IN (SELECT alert_id FROM inserted)
                    RETURNING alert_id, status, version
                ), audit AS (
                    INSERT INTO alert_audit_log
                        (alert_id, actor_user_id, action, old_status, new_status, details)
                    SELECT alert_id, %s, 'EVIDENCE_UPLOADED', status, status, %s::jsonb
                    FROM changed RETURNING audit_id
                ) SELECT changed.version FROM changed JOIN audit ON TRUE""",
                (alert_id, payload.object_key, filename, metadata.get("ContentType", "application/octet-stream"),
                 metadata["ContentLength"], current_user["id"], download_url, current_user["id"],
                 json.dumps({"object_key": payload.object_key, "size_bytes": metadata["ContentLength"]})),
            )
            changed = cur.fetchone()
            if changed:
                version = changed[0]
            else:
                cur.execute("SELECT version FROM alerts WHERE alert_id = %s", (alert_id,))
                version = cur.fetchone()[0]
        return {"object_key": payload.object_key, "download_url": download_url, "version": version}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Evidence metadata unavailable") from exc
