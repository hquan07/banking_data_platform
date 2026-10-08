"""Pure response formatting for isolated benchmark graph analytics."""


def fraud_chain_payload(records) -> list[dict]:
    return [
        {
            "victim": row["victim"],
            "mule": row["mule"],
            "exit": row["exit"],
            "transfer_event_id": row["transfer_event_id"],
            "cashout_event_id": row["cashout_event_id"],
            "transfer_amount": float(row["transfer_amount"]),
            "cashout_amount": float(row["cashout_amount"]),
            "transfer_step": float(row["transfer_step"]),
            "cashout_step": float(row["cashout_step"]),
            "ground_truth_fraud": bool(row["ground_truth_fraud"]),
        }
        for row in records
    ]
