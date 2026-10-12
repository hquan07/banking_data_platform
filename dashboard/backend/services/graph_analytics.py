"""Pure response formatting for isolated benchmark graph analytics."""


def fraud_sequence_payload(records) -> list[dict]:
    return [
        {
            "run_id": row.get("run_id"),
            "evidence_basis": "source_row_adjacency",
            "match_basis": "adjacent_source_rows_same_step_and_amount",
            "transfer_origin": row["transfer_origin"],
            "transfer_destination": row["transfer_destination"],
            "cashout_origin": row["cashout_origin"],
            "cashout_destination": row["cashout_destination"],
            "transfer_event_id": row["transfer_event_id"],
            "cashout_event_id": row["cashout_event_id"],
            "transfer_source_row": row["transfer_source_row"],
            "cashout_source_row": row["cashout_source_row"],
            "transfer_amount": float(row["transfer_amount"]),
            "cashout_amount": float(row["cashout_amount"]),
            "transfer_step": float(row["transfer_step"]),
            "cashout_step": float(row["cashout_step"]),
            "relative_time_unit": row.get("relative_time_unit", "hours"),
            "source_file": row.get("source_file"),
            "source_kind": row.get("source_kind", "synthetic_simulation"),
            "transfer_risk_score": float(row.get("transfer_risk_score", 0)),
            "cashout_risk_score": float(row.get("cashout_risk_score", 0)),
            "participant_linked": row["transfer_destination"] == row["cashout_origin"],
            "ground_truth_fraud": bool(row["ground_truth_fraud"]),
        }
        for row in records
    ]
