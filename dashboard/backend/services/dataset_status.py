"""Pure formatting helpers for dataset status responses."""

DATASETS = {
    "ds1_creditcard": {
        "name": "Credit Card Fraud Detection",
        "source_kind": "anonymized_real",
        "domain": "card_transaction",
    },
    "ds2_ieee_cis": {
        "name": "IEEE-CIS Fraud Detection",
        "source_kind": "anonymized_competition",
        "domain": "ecommerce_transaction",
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
