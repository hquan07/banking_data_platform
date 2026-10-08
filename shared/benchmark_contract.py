"""Canonical wire contract for independent public fraud benchmarks."""

from __future__ import annotations

import math
from typing import Any


SCHEMA_VERSION = 1
DATASET_IDS = frozenset({
    "ds1_creditcard",
    "ds2_ieee_cis",
    "ds3_paysim",
    "ds4_baf",
})
EVENT_TYPES = frozenset({
    "card_transaction",
    "ecommerce_transaction",
    "mobile_money_transaction",
    "account_application",
})
TIME_UNITS = frozenset({"seconds", "hours", "month_index"})


def normalize_benchmark_event(event: dict[str, Any]) -> dict[str, Any]:
    """Validate a benchmark event without inventing identities or wall-clock time."""
    if not isinstance(event, dict) or event.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported_schema_version")
    result = dict(event)
    if result.get("dataset_id") not in DATASET_IDS:
        raise ValueError("invalid_dataset_id")
    if result.get("event_type") not in EVENT_TYPES:
        raise ValueError("invalid_event_type")
    for field in ("event_id", "trace_id", "source_row_id"):
        value = result.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise ValueError(f"invalid_{field}")
        result[field] = value.strip()

    event_time = result.get("event_time")
    if not isinstance(event_time, dict) or event_time.get("kind") != "relative":
        raise ValueError("invalid_event_time")
    if event_time.get("unit") not in TIME_UNITS:
        raise ValueError("invalid_event_time_unit")
    value = event_time.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid_event_time_value")
    if event_time.get("origin") is not None:
        raise ValueError("benchmark_time_origin_must_be_unknown")

    payload = result.get("payload")
    if not isinstance(payload, dict) or not payload:
        raise ValueError("invalid_payload")
    ground_truth = result.get("ground_truth")
    if not isinstance(ground_truth, dict) or type(ground_truth.get("is_fraud")) is not bool:
        raise ValueError("invalid_ground_truth")
    provenance = result.get("provenance")
    if not isinstance(provenance, dict) or not isinstance(provenance.get("source_file"), str):
        raise ValueError("invalid_provenance")
    if provenance.get("source_kind") not in {
        "anonymized_real",
        "anonymized_competition",
        "synthetic_simulation",
        "privacy_preserving_synthetic",
    }:
        raise ValueError("invalid_source_kind")
    return result
