from datetime import datetime, timezone

import pytest

from shared.transfer_contract import normalize_transfer_event


def transfer(**changes):
    return {
        "schema_version": 1, "event_id": "transfer-1", "trace_id": "trace-1",
        "from_account_id": "ACC_A", "to_account_id": "ACC_B",
        "amount": "1200.00", "currency": "USD",
        "timestamp": datetime.now(timezone.utc).isoformat(), **changes,
    }


def test_transfer_normalizes_utc_and_money():
    result = normalize_transfer_event(transfer(amount="12.5", timestamp="2026-10-08T10:00:00+07:00"))
    assert result["amount"] == "12.50"
    assert result["timestamp"] == "2026-10-08T03:00:00.000Z"


@pytest.mark.parametrize("change", [
    {"schema_version": 2}, {"to_account_id": "ACC_A"}, {"amount": -1},
    {"amount": "1.001"}, {"timestamp": "2026-10-08T10:00:00"},
    {"currency": "usd"},
])
def test_invalid_transfer_rejected(change):
    with pytest.raises(ValueError):
        normalize_transfer_event(transfer(**change))
