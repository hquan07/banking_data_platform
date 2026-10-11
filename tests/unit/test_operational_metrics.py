from datetime import datetime, timezone

import pytest


def test_timestamp_seconds_accepts_timezone_aware_iso_values():
    from dashboard.backend.services.processor_health import timestamp_seconds

    value = timestamp_seconds("2026-10-11T09:30:00+00:00")
    assert value == datetime(2026, 10, 11, 9, 30, tzinfo=timezone.utc).timestamp()
    assert timestamp_seconds(None) is None


def test_timestamp_seconds_rejects_naive_values():
    from dashboard.backend.services.processor_health import timestamp_seconds

    with pytest.raises(ValueError, match="timezone"):
        timestamp_seconds("2026-10-11T09:30:00")
