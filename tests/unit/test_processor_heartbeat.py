from datetime import datetime, timedelta, timezone

from dashboard.backend.services.processor_health import processor_health_payload
from shared.processor_heartbeat import ProcessorHeartbeat, UPSERT_HEARTBEAT


class FakeCursor:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, statement, params):
        self.calls.append((statement, params))


class FakeConnection:
    def __init__(self):
        self.cursor_value = FakeCursor()
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_value

    def close(self):
        self.closed = True


def heartbeat_row(name, status, heartbeat_at, *, error=None):
    return (
        name, f"{name}-instance", status, heartbeat_at - timedelta(minutes=1),
        heartbeat_at, heartbeat_at, heartbeat_at, error, 12, 3.5,
        {"last_batch_id": "7"},
    )


def test_heartbeat_upsert_carries_latest_success_state():
    connection = FakeConnection()
    heartbeat = ProcessorHeartbeat(
        "unit_processor",
        interval_seconds=60,
        connection_factory=lambda: connection,
        instance_id="unit-instance",
    )
    heartbeat.record_success(processed_rows=3, batch_id=9, metadata={"topic": "events"})

    assert heartbeat._emit() is True
    assert connection.closed is True
    statement, params = connection.cursor_value.calls[0]
    assert statement == UPSERT_HEARTBEAT
    assert params[0:3] == ("unit_processor", "unit-instance", "running")
    assert params[8] == 3
    assert '"last_batch_id":"9"' in params[10]
    assert '"topic":"events"' in params[10]


def test_processor_health_marks_stale_failed_and_missing_instances():
    now = datetime(2026, 10, 11, 9, 0, tzinfo=timezone.utc)
    rows = [
        heartbeat_row("running", "running", now - timedelta(seconds=10)),
        heartbeat_row("stale", "running", now - timedelta(seconds=46)),
        heartbeat_row("failed", "failed", now - timedelta(seconds=90), error="boom"),
    ]

    payload = processor_health_payload(
        rows,
        now=now,
        stale_after_seconds=45,
        required_processors=("running", "stale", "failed", "missing"),
    )
    by_name = {item["processor_name"]: item for item in payload["processors"]}

    assert payload["status"] == "degraded"
    assert by_name["running"]["status"] == "running"
    assert by_name["stale"]["status"] == "stale"
    assert by_name["failed"]["status"] == "failed"
    assert by_name["failed"]["last_error"] == "boom"
    assert by_name["missing"]["status"] == "missing"
