"""Pure formatting helpers for dataset status responses."""

DATASETS = {
    "ds1_creditcard": {
        "name": "Credit Card Fraud Detection",
        "source_kind": "anonymized_real",
        "domain": "card_transaction",
    },
    "ds3_paysim": {
        "name": "PaySim",
        "source_kind": "synthetic_simulation",
        "domain": "mobile_money_transaction",
    },
    "ds4_baf": {
        "name": "Bank Account Fraud Base",
        "source_kind": "privacy_preserving_synthetic",
        "domain": "account_application",
    },
}


def status_payload(rows: list[tuple]) -> list[dict]:
    observed = {
        row[0]: {
            "event_count": row[1],
            "fraud_count": row[2],
            "first_ingested_at": row[3].isoformat() if row[3] else None,
            "last_ingested_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    }
    result = []
    for dataset_id, metadata in DATASETS.items():
        counts = observed.get(dataset_id, {
            "event_count": 0,
            "fraud_count": 0,
            "first_ingested_at": None,
            "last_ingested_at": None,
        })
        result.append({
            "dataset_id": dataset_id,
            **metadata,
            **counts,
            "status": "loaded" if counts["event_count"] else "not_loaded",
        })
    return result


def balance_anomaly_payload(row: tuple | None) -> dict | None:
    """Format PaySim balance-rule metrics from the latest evaluation per event."""
    if row is None or not row[0]:
        return None
    return {
        "total_events": row[0],
        "evaluated_events": row[1],
        "ground_truth_fraud": row[2],
        "predicted_fraud": row[3],
        "balance_mismatch": row[4],
        "zero_drain": row[5],
        "source_system_flagged": row[6],
        "source_flag_true_positive": row[7],
        "source_flag_false_positive": row[8],
    }


def account_risk_payload(
    summary: tuple | None,
    source_rows: list[tuple],
    device_rows: list[tuple],
) -> dict | None:
    """Format aggregate BAF features without deriving uncalibrated risk labels."""
    if summary is None or not summary[0]:
        return None

    def segment(row: tuple, name_key: str) -> dict:
        total = row[1]
        fraud_count = row[2]
        return {
            name_key: row[0] or "unknown",
            "count": total,
            "fraud_count": fraud_count,
            "fraud_rate": fraud_count / total if total else 0,
        }

    return {
        "total_applications": summary[0],
        "fraud_count": summary[1],
        "fraud_rate": summary[1] / summary[0],
        "average_income": float(summary[2]),
        "average_credit_risk_score": float(summary[3]),
        "average_session_minutes": float(summary[4]),
        "average_name_email_similarity": float(summary[5]),
        "foreign_request_count": summary[6],
        "by_source": [segment(row, "source") for row in source_rows],
        "by_device_os": [segment(row, "device_os") for row in device_rows],
    }


def model_candidate_payload(rows: list[tuple]) -> list[dict]:
    """Expose audited model metadata without loading or serving its binary."""
    return [
        {
            "version": row[0],
            "dataset_id": row[1],
            "algorithm": row[2],
            "feature_schema": row[3],
            "train_rows": row[4],
            "holdout_rows": row[5],
            "dataset_sha256": row[6],
            "model_sha256": row[7],
            "metrics": row[8],
            "evaluation_scope": row[9],
            "decision": row[10],
            "production_eligible": row[11],
            "explanation_status": row[12],
            "recorded_at": row[13].isoformat() if row[13] else None,
        }
        for row in rows
    ]


def behavior_distribution_payload(
    velocity_rows: list[tuple],
    session_rows: list[tuple],
    missing_session_count: int,
) -> dict:
    observed_velocity = {
        (row[0], row[1]): {"count": row[2], "fraud_count": row[3]}
        for row in velocity_rows
    }
    heatmap = []
    for velocity_24h_quantile in range(5, 0, -1):
        for velocity_6h_quantile in range(1, 6):
            counts = observed_velocity.get(
                (velocity_6h_quantile, velocity_24h_quantile),
                {"count": 0, "fraud_count": 0},
            )
            heatmap.append({
                "velocity_6h_quantile": velocity_6h_quantile,
                "velocity_24h_quantile": velocity_24h_quantile,
                **counts,
            })

    return {
        "velocity_heatmap": heatmap,
        "session_bins": [
            {
                "quantile": row[0],
                "minimum_minutes": float(row[1]),
                "maximum_minutes": float(row[2]),
                "count": row[3],
                "fraud_count": row[4],
            }
            for row in session_rows
        ],
        "session_missing_sentinel_count": missing_session_count,
    }
