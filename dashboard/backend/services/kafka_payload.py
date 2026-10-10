"""Decode dashboard Kafka messages without poisoning the payment consumer."""

import json


def decode_message(topic: str, payload: bytes) -> dict | None:
    """Skip invalid stream telemetry; alert parse failures remain retryable errors."""
    tolerant_topics = {"payment-events", "benchmark-events"}
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        if topic in tolerant_topics:
            return None
        raise
    if not isinstance(data, dict):
        if topic in tolerant_topics:
            return None
        raise ValueError("Alert payload must be a JSON object")
    if topic == "payment-events" and "schema_version" in data and data["schema_version"] != 1:
        return None
    if topic == "benchmark-events" and (not data.get("event_id") or not data.get("dataset_id")):
        return None
    return data
