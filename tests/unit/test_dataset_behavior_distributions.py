from dashboard.backend.services.dataset_status import behavior_distribution_payload


def test_behavior_distribution_fills_empty_velocity_cells():
    payload = behavior_distribution_payload(
        [(1, 5, 10, 2), (5, 1, 20, 1)],
        [(1, 0.1, 1.5, 12, 1)],
        7,
    )

    assert len(payload["velocity_heatmap"]) == 25
    assert payload["velocity_heatmap"][0] == {
        "velocity_6h_quantile": 1,
        "velocity_24h_quantile": 5,
        "count": 10,
        "fraud_count": 2,
    }
    assert payload["velocity_heatmap"][1]["count"] == 0
    assert payload["session_bins"][0]["minimum_minutes"] == 0.1
    assert payload["session_missing_sentinel_count"] == 7
