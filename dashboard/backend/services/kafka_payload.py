"""Decode dashboard Kafka messages without poisoning the payment consumer."""

import json


def decode_message(topic: str, payload: bytes) -> dict | None:
    """Skip invalid payments; alert parse failures remain retryable errors."""
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        if topic == "payment-events":
            return None
        raise
    if not isinstance(data, dict):
        if topic == "payment-events":
            return None
        raise ValueError("Alert payload must be a JSON object")
    if topic == "payment-events" and "schema_version" in data and data["schema_version"] != 1:
        return None
    return data
