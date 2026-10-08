from dashboard.backend.services.graph_analytics import fraud_sequence_payload


def test_fraud_sequence_payload_does_not_invent_participant_link():
    payload = fraud_sequence_payload([{
        "transfer_origin": "C1",
        "transfer_destination": "C2",
        "cashout_origin": "C3",
        "cashout_destination": "C4",
        "transfer_event_id": "ds3_paysim:1",
        "cashout_event_id": "ds3_paysim:2",
        "transfer_source_row": 1,
        "cashout_source_row": 2,
        "transfer_amount": 100.0,
        "cashout_amount": 95.0,
        "transfer_step": 4,
        "cashout_step": 5,
        "ground_truth_fraud": True,
    }])

    assert payload[0]["transfer_destination"] == "C2"
    assert payload[0]["cashout_origin"] == "C3"
    assert payload[0]["participant_linked"] is False
    assert payload[0]["transfer_amount"] == 100.0
    assert payload[0]["ground_truth_fraud"] is True


def test_fraud_sequence_payload_handles_empty_result():
    assert fraud_sequence_payload([]) == []
