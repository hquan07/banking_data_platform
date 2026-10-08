"""Opt-in check for atomic, event-time Redis velocity accounting."""

import os
import uuid

import pytest

from fraud.rules.velocity_redis import VELOCITY_SCRIPT


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_E2E") != "1", reason="requires the running Docker Compose stack"
)


def test_velocity_window_deduplicates_and_excludes_late_events():
    import redis

    client = redis.Redis(host="127.0.0.1", port=6379, socket_timeout=5)
    suffix = uuid.uuid4().hex
    account_key = f"test:velocity:{suffix}"
    seen_keys = []
    base_ms = 1_790_000_000_000

    def record(event_number, event_ms):
        event_id = f"test-velocity-{suffix}-{event_number}"
        seen_key = f"test:velocity:seen:{event_id}"
        seen_keys.append(seen_key)
        return client.eval(VELOCITY_SCRIPT, 2, seen_key, account_key, event_id, event_ms)

    try:
        for event_number in range(1, 7):
            assert record(event_number, base_ms + event_number * 1000) == event_number
        assert record(6, base_ms + 6000) == -1
        assert record(7, base_ms - 300000) == -2
        assert record(8, base_ms + 2500) == 7  # out of order, but still in the window
        assert record(9, base_ms + 306000) == 1  # old entries have aged out
        assert client.zcard(account_key) == 1
    finally:
        client.delete(account_key, *seen_keys)
