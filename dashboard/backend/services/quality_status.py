"""Shared operational status vocabulary for runs and dataset freshness."""

from __future__ import annotations

from datetime import datetime, timezone


BAD_CLASSIFICATIONS = {"DUPLICATE", "MISSING", "MISMATCHED"}


def _age(now: datetime, value: datetime | None) -> float | None:
    return max(0.0, (now - value).total_seconds()) if value else None


def run_quality_payload(run: dict, reconciliation_rows: list[tuple], now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    checks: dict[str, set[str]] = {}
    observed = []
    sla_values = []
    for check_id, classification, observed_at, sla_seconds in reconciliation_rows:
        checks.setdefault(str(check_id), set()).add(classification)
        if observed_at:
            observed.append(observed_at)
        sla_values.append(sla_seconds)
    total = len(checks)
    complete = sum("PENDING" not in values for values in checks.values())
    classifications = set().union(*checks.values()) if checks else set()
    status = run["status"]
    reason = None
    if status == "FAILED":
        operational = "failed"
        reason = run.get("failure_reason") or "run_failed"
    elif status in {"RUNNING", "PAUSING", "CANCELLING"}:
        operational = "running"
    elif status in {"CREATED", "PAUSED"}:
        operational = "idle"
    elif classifications & BAD_CLASSIFICATIONS:
        operational = "degraded"
        reason = "reconciliation_discrepancy"
    elif "PENDING" in classifications:
        operational = "running"
        reason = "reconciliation_pending"
    elif status == "COMPLETED":
        operational = "completed"
        if not total:
            reason = "reconciliation_not_run"
    else:
        operational = "failed"
        reason = "run_cancelled"
    last_success = run.get("completed_at") if operational == "completed" else None
    return {
        "status": operational,
        "reason": reason,
        "observed_at": now.isoformat(),
        "last_success_at": last_success.isoformat() if last_success else None,
        "data_age_seconds": _age(now, run.get("updated_at")),
        "sla_threshold_seconds": max(sla_values, default=300),
        "reconciliation_completeness": complete / total if total else 0.0,
        "reconciliation_checks": total,
    }


def dataset_freshness_payload(
    dataset_id: str,
    *,
    event_count: int,
    last_event_at: datetime | None,
    latest_run_quality: dict | None,
    sla_threshold_seconds: int,
    now=None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    age = _age(now, last_event_at)
    if event_count == 0:
        status, reason = "idle", "no_materialized_events"
    elif latest_run_quality and latest_run_quality["status"] in {"failed", "degraded"}:
        status, reason = latest_run_quality["status"], latest_run_quality["reason"]
    elif age is not None and age > sla_threshold_seconds:
        status, reason = "stale", "freshness_sla_exceeded"
    elif latest_run_quality and latest_run_quality["status"] == "running":
        status, reason = "running", latest_run_quality["reason"]
    else:
        status, reason = "ready", None
    return {
        "dataset_id": dataset_id,
        "status": status,
        "reason": reason,
        "observed_at": now.isoformat(),
        "last_success_at": last_event_at.isoformat() if last_event_at else None,
        "data_age_seconds": age,
        "sla_threshold_seconds": sla_threshold_seconds,
        "reconciliation_completeness": (
            latest_run_quality["reconciliation_completeness"]
            if latest_run_quality else None
        ),
        "event_count": event_count,
    }
