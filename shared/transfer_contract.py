"""Version 1 transfer-event contract for account-to-account AML graph edges."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from shared.contract_error import ContractError


SCHEMA_VERSION = 1
TRANSFER_TOPIC = "transfer-events"


def _reject(data: object, reason: str) -> None:
    raise ContractError("transfer", SCHEMA_VERSION, reason, data, TRANSFER_TOPIC)


def normalize_transfer_event(data: dict) -> dict:
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data.get("schema_version") != SCHEMA_VERSION:
        _reject(data, "unsupported_schema_version")
    event = dict(data)
    for field in ("event_id", "trace_id", "from_account_id", "to_account_id"):
        value = event.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            _reject(data, f"invalid_{field}")
    if event["from_account_id"] == event["to_account_id"]:
        _reject(data, "self_transfer")
    try:
        amount = Decimal(str(event["amount"]))
    except (KeyError, InvalidOperation, ValueError):
        _reject(data, "invalid_amount")
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        _reject(data, "invalid_amount")
    currency = event.get("currency")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha() or currency != currency.upper():
        _reject(data, "invalid_currency")
    try:
        event_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError, AttributeError):
        _reject(data, "invalid_timestamp")
    if event_time.tzinfo is None:
        _reject(data, "invalid_timestamp")
    event["amount"] = str(amount.quantize(Decimal("0.01")))
    event["timestamp"] = event_time.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return event
