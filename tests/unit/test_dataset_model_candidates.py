from datetime import datetime, timezone

from dashboard.backend.services.dataset_status import model_candidate_payload


def test_model_candidate_payload_keeps_rejection_and_metrics_explicit():
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    payload = model_candidate_payload([(
        "ds1-isolation-v1",
        "ds1_creditcard",
        "IsolationForest",
        ["V1", "V2"],
        100,
        20,
        "a" * 64,
        "b" * 64,
        {"precision": 0.03, "recall": 0.02},
        "relative_time_holdout",
        "CANDIDATE_NOT_DEPLOYED",
        False,
        "No SHAP values",
        now,
    )])

    assert payload[0]["decision"] == "CANDIDATE_NOT_DEPLOYED"
    assert payload[0]["production_eligible"] is False
    assert payload[0]["metrics"]["precision"] == 0.03
    assert payload[0]["recorded_at"] == "2026-10-08T00:00:00+00:00"
