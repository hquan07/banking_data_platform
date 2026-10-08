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
