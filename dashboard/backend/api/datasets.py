"""Dataset provenance, quality and benchmark analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core.db import pg_conn
from core.deps import get_current_user
from services.dataset_status import (
    account_risk_payload,
    balance_anomaly_payload,
    behavior_distribution_payload,
    model_candidate_payload,
    status_payload,
)


router = APIRouter(prefix="/api/datasets", tags=["Datasets"])

SUPPORTED_DATASET_IDS = {"ds1_creditcard", "ds3_paysim", "ds4_baf"}

def _database_required():
    if pg_conn is None:
        raise HTTPException(status_code=503, detail="Dataset database unavailable")


def _validate_dataset_id(dataset_id: str) -> str:
    if dataset_id not in SUPPORTED_DATASET_IDS:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    return dataset_id


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


@router.get("/model-candidates")
def get_model_candidates(current_user: dict = Depends(get_current_user)):
    _database_required()
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT version, dataset_id, algorithm, feature_schema,
                       train_rows, holdout_rows, dataset_sha256, model_sha256,
                       metrics, evaluation_scope, decision,
                       production_eligible, explanation_status, recorded_at
                FROM benchmark_model_candidates
                ORDER BY recorded_at DESC, version
                """
            )
            rows = cursor.fetchall()
        return model_candidate_payload(rows)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Model candidate registry unavailable") from exc


@router.get("/behavior-distributions")
def get_behavior_distributions(current_user: dict = Depends(get_current_user)):
    _database_required()
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                WITH ranked AS (
                    SELECT
                        ntile(5) OVER (
                            ORDER BY (payload #>> '{features,velocity_6h}')::double precision
                        ) AS velocity_6h_quantile,
                        ntile(5) OVER (
                            ORDER BY (payload #>> '{features,velocity_24h}')::double precision
                        ) AS velocity_24h_quantile,
                        ground_truth_is_fraud
                    FROM benchmark_events
                    WHERE dataset_id = 'ds4_baf'
                )
                SELECT velocity_6h_quantile, velocity_24h_quantile, count(*),
                       count(*) FILTER (WHERE ground_truth_is_fraud)
                FROM ranked
                GROUP BY velocity_6h_quantile, velocity_24h_quantile
                ORDER BY velocity_24h_quantile DESC, velocity_6h_quantile
                """
            )
            velocity_rows = cursor.fetchall()
            cursor.execute(
                """
                WITH ranked AS (
                    SELECT
                        ntile(10) OVER (
                            ORDER BY (payload #>> '{features,session_length_in_minutes}')::double precision
                        ) AS session_quantile,
                        (payload #>> '{features,session_length_in_minutes}')::double precision
                            AS session_minutes,
                        ground_truth_is_fraud
                    FROM benchmark_events
                    WHERE dataset_id = 'ds4_baf'
                      AND (payload #>> '{features,session_length_in_minutes}')::double precision >= 0
                )
                SELECT session_quantile, min(session_minutes), max(session_minutes),
                       count(*), count(*) FILTER (WHERE ground_truth_is_fraud)
                FROM ranked
                GROUP BY session_quantile
                ORDER BY session_quantile
                """
            )
            session_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT count(*)
                FROM benchmark_events
                WHERE dataset_id = 'ds4_baf'
                  AND (payload #>> '{features,session_length_in_minutes}')::double precision < 0
                """
            )
            missing_session_count = cursor.fetchone()[0]
        return behavior_distribution_payload(
            velocity_rows, session_rows, missing_session_count
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Behavior distributions unavailable") from exc


@router.get("/{dataset_id}/overview")
def get_dataset_overview(dataset_id: str, current_user: dict = Depends(get_current_user)):
    """Return one consistent KPI contract for every benchmark dataset."""
    _database_required()
    dataset_id = _validate_dataset_id(dataset_id)
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (event_id) event_id, predicted_fraud
                    FROM benchmark_evaluations
                    WHERE dataset_id = %s
                    ORDER BY event_id, evaluated_at DESC, evaluation_id DESC
                ), event_metrics AS (
                    SELECT
                        count(*) AS event_count,
                        count(*) FILTER (WHERE e.ground_truth_is_fraud) AS fraud_count,
                        COALESCE(sum((e.payload->>'amount')::double precision), 0) AS total_amount,
                        avg((e.payload->>'amount')::double precision) AS average_amount,
                        min(e.relative_time_value) AS minimum_time,
                        max(e.relative_time_value) AS maximum_time,
                        min(e.relative_time_unit) AS time_unit,
                        min(e.ingested_at) AS first_ingested_at,
                        max(e.ingested_at) AS last_ingested_at,
                        count(l.event_id) AS evaluated_count,
                        count(*) FILTER (WHERE l.predicted_fraud) AS predicted_fraud,
                        count(*) FILTER (WHERE l.predicted_fraud AND e.ground_truth_is_fraud) AS tp,
                        count(*) FILTER (WHERE l.predicted_fraud AND NOT e.ground_truth_is_fraud) AS fp,
                        count(*) FILTER (WHERE NOT l.predicted_fraud AND NOT e.ground_truth_is_fraud) AS tn,
                        count(*) FILTER (WHERE NOT l.predicted_fraud AND e.ground_truth_is_fraud) AS fn
                    FROM benchmark_events e
                    LEFT JOIN latest l ON l.event_id = e.event_id
                    WHERE e.dataset_id = %s
                ), alert_metrics AS (
                    SELECT count(*) AS alert_count,
                           count(*) FILTER (WHERE status IN ('PENDING', 'INVESTIGATING')) AS open_alerts
                    FROM alerts WHERE dataset_id = %s
                )
                SELECT event_metrics.*, alert_metrics.alert_count, alert_metrics.open_alerts
                FROM event_metrics CROSS JOIN alert_metrics
                """,
                (dataset_id, dataset_id, dataset_id),
            )
            row = cursor.fetchone()
        total, fraud = row[0], row[1]
        tp, fp, tn, fn = row[11], row[12], row[13], row[14]
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        false_positive_rate = fp / (fp + tn) if fp + tn else None
        return {
            "dataset_id": dataset_id,
            "event_count": total,
            "fraud_count": fraud,
            "fraud_rate": fraud / total if total else 0,
            "total_amount": float(row[2] or 0),
            "average_amount": float(row[3]) if row[3] is not None else None,
            "minimum_time": row[4],
            "maximum_time": row[5],
            "time_unit": row[6],
            "first_ingested_at": row[7].isoformat() if row[7] else None,
            "last_ingested_at": row[8].isoformat() if row[8] else None,
            "evaluated_count": row[9],
            "predicted_fraud": row[10],
            "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
            "precision": precision,
            "recall": recall,
            "false_positive_rate": false_positive_rate,
            "alert_count": row[15],
            "open_alerts": row[16],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dataset overview unavailable") from exc


@router.get("/{dataset_id}/timeseries")
def get_dataset_timeseries(dataset_id: str, current_user: dict = Depends(get_current_user)):
    """Aggregate event/fraud volume using the source's relative time semantics."""
    _database_required()
    dataset_id = _validate_dataset_id(dataset_id)
    bucket_expression = (
        "floor(relative_time_value / 60) * 60"
        if dataset_id == "ds1_creditcard"
        else "relative_time_value"
    )
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {bucket_expression} AS bucket,
                       min(relative_time_unit) AS unit,
                       count(*) AS event_count,
                       count(*) FILTER (WHERE ground_truth_is_fraud) AS fraud_count,
                       COALESCE(sum((payload->>'amount')::double precision), 0) AS total_amount
                FROM benchmark_events
                WHERE dataset_id = %s
                GROUP BY bucket
                ORDER BY bucket
                """,
                (dataset_id,),
            )
            rows = cursor.fetchall()
        return [
            {"bucket": row[0], "time_unit": row[1], "event_count": row[2],
             "fraud_count": row[3], "total_amount": float(row[4] or 0)}
            for row in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dataset time series unavailable") from exc


@router.get("/{dataset_id}/segments")
def get_dataset_segments(dataset_id: str, current_user: dict = Depends(get_current_user)):
    """Return dataset-native categorical distributions without inventing common entities."""
    _database_required()
    dataset_id = _validate_dataset_id(dataset_id)
    if dataset_id == "ds1_creditcard":
        segment_queries = {
            "amount_band": """
                CASE WHEN (payload->>'amount')::double precision < 10 THEN '< 10'
                     WHEN (payload->>'amount')::double precision < 50 THEN '10–49'
                     WHEN (payload->>'amount')::double precision < 100 THEN '50–99'
                     WHEN (payload->>'amount')::double precision < 500 THEN '100–499'
                     ELSE '500+' END
            """,
        }
    elif dataset_id == "ds3_paysim":
        segment_queries = {"transaction_type": "payload->>'transaction_type'"}
    else:
        segment_queries = {
            "source": "payload #>> '{features,source}'",
            "device_os": "payload #>> '{features,device_os}'",
            "payment_type": "payload #>> '{features,payment_type}'",
            "age_band": """
                CASE WHEN (payload #>> '{features,customer_age}')::integer < 30 THEN '< 30'
                     WHEN (payload #>> '{features,customer_age}')::integer < 50 THEN '30–49'
                     WHEN (payload #>> '{features,customer_age}')::integer < 70 THEN '50–69'
                     ELSE '70+' END
            """,
        }
    try:
        response = {}
        with pg_conn.cursor() as cursor:
            for segment, expression in segment_queries.items():
                cursor.execute(
                    f"""
                    SELECT {expression} AS label, count(*) AS event_count,
                           count(*) FILTER (WHERE ground_truth_is_fraud) AS fraud_count
                    FROM benchmark_events
                    WHERE dataset_id = %s
                    GROUP BY label
                    ORDER BY event_count DESC, label
                    """,
                    (dataset_id,),
                )
                response[segment] = [
                    {"label": row[0] or "unknown", "event_count": row[1],
                     "fraud_count": row[2], "fraud_rate": row[2] / row[1] if row[1] else 0}
                    for row in cursor.fetchall()
                ]
        return {"dataset_id": dataset_id, "segments": response}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dataset segments unavailable") from exc
