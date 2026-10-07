"""Version 1 of the payment-events wire contract.

Identifiers are stable across retries. Amounts have two decimal places and
timestamps are UTC ISO-8601 strings ending in Z.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

SCHEMA_VERSION = 1
PAYMENT_TOPIC = "payment-events"
PAYMENT_STATUSES = frozenset({"CREATED", "PENDING", "SUCCESS", "FAILED"})
PAYMENT_METHODS = frozenset({"CARD", "BANK_TRANSFER", "QR"})
CHANNELS = frozenset({"POS", "ONLINE", "ATM"})
MAX_AMOUNT = Decimal("9999999999999999.99")


def normalize_payment_event(event: dict) -> dict:
    """Validate and normalize a v1 payment event; reject unsupported versions."""
    if not isinstance(event, dict) or event.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported payment schema_version")

    result = event.copy()
    for field in ("event_id", "trace_id", "payment_id", "customer_id", "account_id"):
        value = result.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise ValueError(f"Invalid {field}")
        result[field] = value.strip()

    try:
        amount = Decimal(str(result.get("amount")))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid amount") from exc
    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT or amount.as_tuple().exponent < -2:
        raise ValueError("Amount must be positive with at most two decimal places")
    result["amount"] = float(amount)

    currency = result.get("currency")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Invalid ISO currency code")
    for field, allowed in (("status", PAYMENT_STATUSES), ("payment_method", PAYMENT_METHODS), ("channel", CHANNELS)):
        if result.get(field) not in allowed:
            raise ValueError(f"Invalid {field}")

    value = result.get("timestamp")
    if not isinstance(value, str):
        raise ValueError("Invalid timestamp")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid timestamp") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    result["timestamp"] = timestamp.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return result
