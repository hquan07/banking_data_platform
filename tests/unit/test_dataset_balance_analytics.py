from dashboard.backend.services.dataset_status import balance_anomaly_payload


def test_balance_anomaly_payload_formats_latest_evaluation_counts():
    payload = balance_anomaly_payload((1000, 1000, 2, 5, 4, 3, 1, 1, 0))

    assert payload == {
        "total_events": 1000,
        "evaluated_events": 1000,
        "ground_truth_fraud": 2,
        "predicted_fraud": 5,
        "balance_mismatch": 4,
        "zero_drain": 3,
        "source_system_flagged": 1,
        "source_flag_true_positive": 1,
        "source_flag_false_positive": 0,
    }


def test_balance_anomaly_payload_is_empty_without_paysim_events():
    assert balance_anomaly_payload(None) is None
    assert balance_anomaly_payload((0, 0, 0, 0, 0, 0, 0, 0, 0)) is None
