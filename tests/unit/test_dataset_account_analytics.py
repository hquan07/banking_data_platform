from dashboard.backend.services.dataset_status import account_risk_payload


def test_account_risk_payload_preserves_source_segments():
    payload = account_risk_payload(
        (1000, 11, 0.62, 145.5, 7.25, 0.71, 23),
        [("INTERNET", 800, 10), ("TELEAPP", 200, 1)],
        [("windows", 700, 8), ("linux", 300, 3)],
    )

    assert payload["fraud_rate"] == 0.011
    assert payload["average_credit_risk_score"] == 145.5
    assert payload["by_source"][0] == {
        "source": "INTERNET", "count": 800, "fraud_count": 10, "fraud_rate": 0.0125,
    }
    assert payload["by_device_os"][1]["device_os"] == "linux"


def test_account_risk_payload_is_empty_without_baf_events():
    assert account_risk_payload(None, [], []) is None
    assert account_risk_payload((0, 0, None, None, None, None, 0), [], []) is None
