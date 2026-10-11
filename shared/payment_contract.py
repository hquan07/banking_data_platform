"""Version 1 of the payment-events wire contract.

Identifiers are stable across retries. Amounts have two decimal places and
timestamps are UTC ISO-8601 strings ending in Z.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

from shared.contract_error import ContractError

SCHEMA_VERSION = 1
PAYMENT_TOPIC = "payment-events"
PAYMENT_STATUSES = frozenset({"CREATED", "PENDING", "SUCCESS", "FAILED"})
PAYMENT_METHODS = frozenset({"CARD", "BANK_TRANSFER", "QR"})
CHANNELS = frozenset({"POS", "ONLINE", "ATM"})
MAX_AMOUNT = Decimal("99999999999.99")


def normalize_payment_event(event: dict) -> dict:
    """Validate and normalize a v1 payment event; reject unsupported versions."""
    if not isinstance(event, dict) or type(event.get("schema_version")) is not int or event["schema_version"] != SCHEMA_VERSION:
        raise ContractError("payment", SCHEMA_VERSION, "unsupported_schema_version", event, PAYMENT_TOPIC)

    result = event.copy()
    for field, maximum in (("event_id", 120), ("trace_id", 50), ("payment_id", 50), ("customer_id", 50), ("account_id", 50)):
        value = result.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ContractError("payment", SCHEMA_VERSION, f"invalid_{field}", event, PAYMENT_TOPIC)
        result[field] = value.strip()

    for field, maximum in (("merchant_id", 50), ("device_id", 50), ("location", 100)):
        value = result.get(field)
        if value is not None and (not isinstance(value, str) or len(value) > maximum):
            raise ContractError("payment", SCHEMA_VERSION, f"invalid_{field}", event, PAYMENT_TOPIC)

    try:
        amount = Decimal(str(result.get("amount")))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ContractError("payment", SCHEMA_VERSION, "invalid_amount", event, PAYMENT_TOPIC) from exc
    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT or amount.as_tuple().exponent < -2:
        raise ContractError("payment", SCHEMA_VERSION, "invalid_amount", event, PAYMENT_TOPIC)
    result["amount"] = float(amount)

    currency = result.get("currency")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        raise ContractError("payment", SCHEMA_VERSION, "invalid_currency", event, PAYMENT_TOPIC)
    for field, allowed in (("status", PAYMENT_STATUSES), ("payment_method", PAYMENT_METHODS), ("channel", CHANNELS)):
        if result.get(field) not in allowed:
            raise ContractError("payment", SCHEMA_VERSION, f"invalid_{field}", event, PAYMENT_TOPIC)

    value = result.get("timestamp")
    if not isinstance(value, str):
        raise ContractError("payment", SCHEMA_VERSION, "invalid_timestamp", event, PAYMENT_TOPIC)
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("payment", SCHEMA_VERSION, "invalid_timestamp", event, PAYMENT_TOPIC) from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ContractError("payment", SCHEMA_VERSION, "timestamp_timezone_required", event, PAYMENT_TOPIC)
    result["timestamp"] = timestamp.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return result
