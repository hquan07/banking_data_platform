from datetime import datetime, timezone

from dashboard.backend.services.dataset_status import DATASETS, status_payload


def test_status_payload_keeps_unloaded_sources_visible():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    payload = status_payload([("ds3_paysim", 100, 2, now, now)])

    assert len(payload) == len(DATASETS)
    paysim = next(item for item in payload if item["dataset_id"] == "ds3_paysim")
    assert paysim["status"] == "loaded"
    assert paysim["event_count"] == 100
    assert paysim["source_kind"] == "synthetic_simulation"
    ds1 = next(item for item in payload if item["dataset_id"] == "ds1_creditcard")
    assert ds1["status"] == "not_loaded"
    assert ds1["event_count"] == 0
