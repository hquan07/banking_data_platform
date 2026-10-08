from dashboard.backend.services.graph_analytics import fraud_chain_payload


def test_fraud_chain_payload_keeps_ground_truth_as_evaluation_context():
    payload = fraud_chain_payload([{
        "victim": "C1",
        "mule": "C2",
        "exit": "M3",
        "transfer_event_id": "ds3_paysim:1",
        "cashout_event_id": "ds3_paysim:2",
        "transfer_amount": 100.0,
        "cashout_amount": 95.0,
        "transfer_step": 4,
        "cashout_step": 5,
        "ground_truth_fraud": True,
    }])

    assert payload[0]["mule"] == "C2"
    assert payload[0]["transfer_amount"] == 100.0
    assert payload[0]["ground_truth_fraud"] is True


def test_fraud_chain_payload_handles_empty_result():
    assert fraud_chain_payload([]) == []
