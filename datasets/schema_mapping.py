"""Source-specific mappings into benchmark-events v1."""

from __future__ import annotations

import math
from typing import Any, Mapping

from shared.benchmark_contract import normalize_benchmark_event


DS1_FEATURES = tuple(f"V{i}" for i in range(1, 29))
DS4_FEATURES = (
    "income", "name_email_similarity", "prev_address_months_count",
    "current_address_months_count", "customer_age", "days_since_request",
    "intended_balcon_amount", "payment_type", "zip_count_4w", "velocity_6h",
    "velocity_24h", "velocity_4w", "bank_branch_count_8w",
    "date_of_birth_distinct_emails_4w", "employment_status",
    "credit_risk_score", "email_is_free", "housing_status", "phone_home_valid",
    "phone_mobile_valid", "bank_months_count", "has_other_cards",
    "proposed_credit_limit", "foreign_request", "source",
    "session_length_in_minutes", "device_os", "keep_alive_session",
    "device_distinct_emails_8w", "device_fraud_count",
)


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _plain(value: Any) -> Any:
    if _missing(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _required_number(row: Mapping[str, Any], field: str, *, minimum: float = 0) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"invalid_{field}") from None
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"invalid_{field}")
    return value


def _label(value: Any) -> bool:
    if value in (0, 0.0, "0", False):
        return False
    if value in (1, 1.0, "1", True):
        return True
    raise ValueError("invalid_fraud_label")


def _event(
    *, dataset_id: str, source_row_id: Any, event_type: str,
    time_value: float, time_unit: str, payload: dict[str, Any],
    is_fraud: bool, source_file: str, source_kind: str,
) -> dict[str, Any]:
    row_id = str(source_row_id).strip()
    if not row_id:
        raise ValueError("invalid_source_row_id")
    event_id = f"{dataset_id}:{row_id}"
    return normalize_benchmark_event({
        "schema_version": 1,
        "dataset_id": dataset_id,
        "event_id": event_id,
        "trace_id": event_id,
        "source_row_id": row_id,
        "event_type": event_type,
        "event_time": {"kind": "relative", "value": time_value, "unit": time_unit, "origin": None},
        "payload": payload,
        "ground_truth": {"is_fraud": is_fraud},
        "provenance": {"source_file": source_file, "source_kind": source_kind},
    })


def _feature_group(row: Mapping[str, Any], names: tuple[str, ...]) -> dict[str, Any]:
    return {name: _plain(row.get(name)) for name in names if not _missing(row.get(name))}


def map_ds1(row: Mapping[str, Any], row_number: int) -> dict[str, Any]:
    features = _feature_group(row, DS1_FEATURES)
    if len(features) != len(DS1_FEATURES):
        raise ValueError("missing_ds1_pca_feature")
    return _event(
        dataset_id="ds1_creditcard",
        source_row_id=row_number,
        event_type="card_transaction",
        time_value=_required_number(row, "Time"),
        time_unit="seconds",
        payload={"amount": _required_number(row, "Amount"), "pca_features": features},
        is_fraud=_label(row.get("Class")),
        source_file="creditcard/creditcard.csv",
        source_kind="anonymized_real",
    )


def map_ds3(row: Mapping[str, Any], row_number: int) -> dict[str, Any]:
    tx_type = str(row.get("type", "")).strip().upper()
    if tx_type not in {"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}:
        raise ValueError("invalid_paysim_type")
    participant_ids = {
        "origin": str(row.get("nameOrig", "")).strip(),
        "destination": str(row.get("nameDest", "")).strip(),
    }
    if not all(participant_ids.values()):
        raise ValueError("invalid_paysim_participant")
    balances = {
        "origin_before": _required_number(row, "oldbalanceOrg"),
        "origin_after": _required_number(row, "newbalanceOrig"),
        "destination_before": _required_number(row, "oldbalanceDest"),
        "destination_after": _required_number(row, "newbalanceDest"),
    }
    return _event(
        dataset_id="ds3_paysim",
        source_row_id=row_number,
        event_type="mobile_money_transaction",
        time_value=_required_number(row, "step"),
        time_unit="hours",
        payload={
            "transaction_type": tx_type,
            "amount": _required_number(row, "amount"),
            "participant_ids": participant_ids,
            "balances": balances,
            "source_system_flag": _label(row.get("isFlaggedFraud")),
        },
        is_fraud=_label(row.get("isFraud")),
        source_file="paysim/PS_20174392719_1491204439457_log.csv",
        source_kind="synthetic_simulation",
    )


def map_ds4(row: Mapping[str, Any], row_number: int) -> dict[str, Any]:
    features = {name: _plain(row.get(name)) for name in DS4_FEATURES}
    missing = [name for name, value in features.items() if value is None]
    if missing:
        raise ValueError(f"missing_ds4_features:{','.join(missing)}")
    return _event(
        dataset_id="ds4_baf",
        source_row_id=row_number,
        event_type="account_application",
        time_value=_required_number(row, "month"),
        time_unit="month_index",
        payload={"features": features},
        is_fraud=_label(row.get("fraud_bool")),
        source_file="bank-account-fraud/Base.csv",
        source_kind="privacy_preserving_synthetic",
    )
