"""Version 1 contract for fraud and AML alert envelopes."""

from __future__ import annotations

import math
from typing import Any

from shared.contract_error import ContractError


SCHEMA_VERSION = 1
ALERT_TOPICS = frozenset({"fraud-events", "aml-events"})
RISK_LEVELS = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
DECISIONS = frozenset({"ALLOW", "MONITOR", "REVIEW", "BLOCK"})


def normalize_alert_event(event: dict[str, Any], source_topic: str = "fraud-events") -> dict[str, Any]:
    """Validate the common fields shared by rule-specific alert payloads."""
    if source_topic not in ALERT_TOPICS:
        raise ValueError("Unsupported alert source topic")
    if not isinstance(event, dict) or type(event.get("schema_version")) is not int or event.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("alert", SCHEMA_VERSION, "unsupported_schema_version", event, source_topic)
    result = dict(event)
    for field in ("event_id", "rule"):
        value = result.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise ContractError("alert", SCHEMA_VERSION, f"invalid_{field}", event, source_topic)
        result[field] = value.strip()
    trace_id = result.get("trace_id")
    if trace_id is not None and (not isinstance(trace_id, str) or not trace_id.strip() or len(trace_id) > 120):
        raise ContractError("alert", SCHEMA_VERSION, "invalid_trace_id", event, source_topic)
    score = result.get("risk_score")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score) or not 0 <= score <= 100:
        raise ContractError("alert", SCHEMA_VERSION, "invalid_risk_score", event, source_topic)
    if result.get("risk_level") is not None and result["risk_level"] not in RISK_LEVELS:
        raise ContractError("alert", SCHEMA_VERSION, "invalid_risk_level", event, source_topic)
    if result.get("decision") is not None and result["decision"] not in DECISIONS:
        raise ContractError("alert", SCHEMA_VERSION, "invalid_decision", event, source_topic)
    return result
