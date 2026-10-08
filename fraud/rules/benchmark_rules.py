"""Leakage-safe, source-specific benchmark rules.

Ground-truth labels are intentionally not accepted by any rule helper.
"""

from __future__ import annotations

from typing import Any


EVALUATOR_VERSION = "benchmark-rules-v2"
OUTFLOW_TYPES = frozenset({"CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"})


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _signal(rule: str, score: float, evidence: dict[str, Any]) -> dict[str, Any]:
    if score >= 85:
        level = "HIGH"
    elif score >= 65:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {
        "rule": rule,
        "risk_score": score,
        "risk_level": level,
        "decision": "REVIEW",
        "evidence": evidence,
    }


def evaluate_paysim(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate balance semantics from the PaySim payload only."""
    tx_type = payload.get("transaction_type")
    amount = _number(payload.get("amount"))
    balances = payload.get("balances") or {}
    before = _number(balances.get("origin_before"))
    after = _number(balances.get("origin_after"))
    if amount is None or before is None or after is None:
        return []

    signals = []
    expected_after = None
    if tx_type == "CASH_IN":
        expected_after = before + amount
    elif tx_type in OUTFLOW_TYPES and before >= amount:
        expected_after = before - amount
    if expected_after is not None and abs(expected_after - after) > 0.01:
        signals.append(_signal("BALANCE_MISMATCH", 75, {
            "transaction_type": tx_type,
            "origin_before": before,
            "amount": amount,
            "expected_origin_after": round(expected_after, 2),
            "observed_origin_after": after,
        }))
    if tx_type in OUTFLOW_TYPES and before >= amount and after == 0 and amount >= 10_000:
        signals.append(_signal("ZERO_DRAIN", 70, {
            "transaction_type": tx_type,
            "origin_before": before,
            "amount": amount,
        }))
    return signals


def evaluate_baf(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep BAF fail-closed until source-specific thresholds are calibrated."""
    # Canary profiling showed device_fraud_count is constant zero and a proposed
    # identity-reuse threshold flagged most rows. Persist all features for
    # offline calibration, but do not turn uncalibrated values into cases.
    return []


def evaluate_benchmark_payload(dataset_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic rule signals without reading evaluation labels."""
    if dataset_id == "ds3_paysim":
        return evaluate_paysim(payload)
    if dataset_id == "ds4_baf":
        return evaluate_baf(payload)
    # DS1 requires a trained, versioned model or calibrated profile
    # thresholds. They are persisted but deliberately not guessed here.
    return []
