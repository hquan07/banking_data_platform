"""Pure response formatting for isolated benchmark graph analytics."""


def fraud_sequence_payload(records) -> list[dict]:
    return [
        {
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
            "participant_linked": row["transfer_destination"] == row["cashout_origin"],
            "ground_truth_fraud": bool(row["ground_truth_fraud"]),
        }
        for row in records
    ]
