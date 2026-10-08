"""Dataset provenance, quality and benchmark analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core.db import pg_conn
from core.deps import get_current_user
from services.dataset_status import account_risk_payload, balance_anomaly_payload, status_payload


router = APIRouter(prefix="/api/datasets", tags=["Datasets"])

def _database_required():
    if pg_conn is None:
        raise HTTPException(status_code=503, detail="Dataset database unavailable")


@router.get("/status")
def get_dataset_status(current_user: dict = Depends(get_current_user)):
    _database_required()
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT dataset_id, count(*),
                       count(*) FILTER (WHERE ground_truth_is_fraud),
                       min(ingested_at), max(ingested_at)
                FROM benchmark_events
                GROUP BY dataset_id
                """
            )
            rows = cursor.fetchall()
        return status_payload(rows)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dataset status unavailable") from exc


@router.get("/performance")
def get_dataset_performance(current_user: dict = Depends(get_current_user)):
    _database_required()
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT e.dataset_id, v.evaluator_version, count(*) AS total,
                       count(*) FILTER (WHERE v.predicted_fraud AND e.ground_truth_is_fraud) AS tp,
                       count(*) FILTER (WHERE v.predicted_fraud AND NOT e.ground_truth_is_fraud) AS fp,
                       count(*) FILTER (WHERE NOT v.predicted_fraud AND NOT e.ground_truth_is_fraud) AS tn,
                       count(*) FILTER (WHERE NOT v.predicted_fraud AND e.ground_truth_is_fraud) AS fn
                FROM benchmark_events e
                JOIN benchmark_evaluations v ON v.event_id = e.event_id
                GROUP BY e.dataset_id, v.evaluator_version
                ORDER BY e.dataset_id, v.evaluator_version
                """
            )
            rows = cursor.fetchall()
        return [
            {
                "dataset_id": row[0], "evaluator_version": row[1], "total": row[2],
                "true_positive": row[3], "false_positive": row[4],
                "true_negative": row[5], "false_negative": row[6],
            }
            for row in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dataset performance unavailable") from exc


@router.get("/rule-hits")
def get_rule_hits(current_user: dict = Depends(get_current_user)):
    _database_required()
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT dataset_id, rule_name, count(*)
                FROM alerts
                WHERE dataset_id IS NOT NULL
                GROUP BY dataset_id, rule_name
                ORDER BY dataset_id, count(*) DESC, rule_name
                """
            )
            rows = cursor.fetchall()
        return [{"dataset_id": row[0], "rule": row[1], "count": row[2]} for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dataset rule analytics unavailable") from exc


@router.get("/transaction-types")
def get_transaction_types(current_user: dict = Depends(get_current_user)):
    _database_required()
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT payload->>'transaction_type' AS transaction_type,
                       count(*), sum((payload->>'amount')::double precision),
                       count(*) FILTER (WHERE ground_truth_is_fraud)
                FROM benchmark_events
                WHERE dataset_id = 'ds3_paysim'
                GROUP BY transaction_type
                ORDER BY count(*) DESC
                """
            )
            rows = cursor.fetchall()
        return [
            {"transaction_type": row[0], "count": row[1],
             "total_amount": float(row[2]), "fraud_count": row[3]}
            for row in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Transaction type analytics unavailable") from exc


@router.get("/balance-anomalies")
def get_balance_anomalies(current_user: dict = Depends(get_current_user)):
    _database_required()
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                WITH latest_evaluation AS (
                    SELECT DISTINCT ON (event_id)
                           event_id, predicted_fraud, triggered_rules
                    FROM benchmark_evaluations
                    WHERE dataset_id = 'ds3_paysim'
                    ORDER BY event_id, evaluated_at DESC, evaluation_id DESC
                )
                SELECT
                    count(*) AS total_events,
                    count(v.event_id) AS evaluated_events,
                    count(*) FILTER (WHERE e.ground_truth_is_fraud),
                    count(*) FILTER (WHERE v.predicted_fraud),
                    count(*) FILTER (WHERE v.triggered_rules ? 'BALANCE_MISMATCH'),
                    count(*) FILTER (WHERE v.triggered_rules ? 'ZERO_DRAIN'),
                    count(*) FILTER (
                        WHERE (e.payload->>'source_system_flag')::boolean
                    ),
                    count(*) FILTER (
                        WHERE (e.payload->>'source_system_flag')::boolean
                          AND e.ground_truth_is_fraud
                    ),
                    count(*) FILTER (
                        WHERE (e.payload->>'source_system_flag')::boolean
                          AND NOT e.ground_truth_is_fraud
                    )
                FROM benchmark_events e
                LEFT JOIN latest_evaluation v ON v.event_id = e.event_id
                WHERE e.dataset_id = 'ds3_paysim'
                """
            )
            row = cursor.fetchone()
        return balance_anomaly_payload(row)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Balance anomaly analytics unavailable") from exc


@router.get("/velocity-summary")
def get_velocity_summary(current_user: dict = Depends(get_current_user)):
    _database_required()
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    avg((payload #>> '{features,velocity_6h}')::double precision),
                    percentile_cont(0.5) WITHIN GROUP
                        (ORDER BY (payload #>> '{features,velocity_6h}')::double precision),
                    percentile_cont(0.95) WITHIN GROUP
                        (ORDER BY (payload #>> '{features,velocity_6h}')::double precision),
                    avg((payload #>> '{features,velocity_24h}')::double precision),
                    avg((payload #>> '{features,velocity_4w}')::double precision)
                FROM benchmark_events
                WHERE dataset_id = 'ds4_baf'
                """
            )
            row = cursor.fetchone()
        if row is None or row[0] is None:
            return None
        return {
            "velocity_6h_avg": float(row[0]), "velocity_6h_p50": float(row[1]),
            "velocity_6h_p95": float(row[2]), "velocity_24h_avg": float(row[3]),
            "velocity_4w_avg": float(row[4]),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Velocity analytics unavailable") from exc


@router.get("/account-risk")
def get_account_risk(current_user: dict = Depends(get_current_user)):
    _database_required()
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    count(*),
                    count(*) FILTER (WHERE ground_truth_is_fraud),
                    avg((payload #>> '{features,income}')::double precision),
                    avg((payload #>> '{features,credit_risk_score}')::double precision),
                    avg((payload #>> '{features,session_length_in_minutes}')::double precision),
                    avg((payload #>> '{features,name_email_similarity}')::double precision),
                    count(*) FILTER (
                        WHERE (payload #>> '{features,foreign_request}')::integer = 1
                    )
                FROM benchmark_events
                WHERE dataset_id = 'ds4_baf'
                """
            )
            summary = cursor.fetchone()
            cursor.execute(
                """
                SELECT payload #>> '{features,source}', count(*),
                       count(*) FILTER (WHERE ground_truth_is_fraud)
                FROM benchmark_events
                WHERE dataset_id = 'ds4_baf'
                GROUP BY payload #>> '{features,source}'
                ORDER BY count(*) DESC
                """
            )
            source_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT payload #>> '{features,device_os}', count(*),
                       count(*) FILTER (WHERE ground_truth_is_fraud)
                FROM benchmark_events
                WHERE dataset_id = 'ds4_baf'
                GROUP BY payload #>> '{features,device_os}'
                ORDER BY count(*) DESC
                """
            )
            device_rows = cursor.fetchall()
        return account_risk_payload(summary, source_rows, device_rows)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Account risk analytics unavailable") from exc
