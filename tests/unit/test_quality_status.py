from datetime import datetime, timedelta, timezone

from dashboard.backend.services.quality_status import (
    dataset_freshness_payload,
    run_quality_payload,
)


NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)


def _run(status="COMPLETED"):
    return {
        "status": status,
        "updated_at": NOW - timedelta(seconds=10),
        "completed_at": NOW - timedelta(seconds=10) if status == "COMPLETED" else None,
        "failure_reason": "boom" if status == "FAILED" else None,
    }


def test_run_quality_reports_complete_reconciliation():
    quality = run_quality_payload(
        _run(), [("check-1", "EXACT", NOW, 60), ("check-2", "QUARANTINED", NOW, 60)],
        now=NOW,
    )
    assert quality["status"] == "completed"
    assert quality["reconciliation_completeness"] == 1
    assert quality["last_success_at"] is not None


def test_run_quality_status_precedence_failed_then_degraded_then_pending():
    assert run_quality_payload(_run("FAILED"), [], now=NOW)["status"] == "failed"
    degraded = run_quality_payload(
        _run(), [("check-1", "MISSING", NOW, 60)], now=NOW,
    )
    assert degraded["status"] == "degraded"
    pending = run_quality_payload(
        _run(), [("check-1", "PENDING", NOW, 60)], now=NOW,
    )
    assert pending["status"] == "running"


def test_empty_dataset_is_idle_never_ready():
    payload = dataset_freshness_payload(
        "ds1_creditcard", event_count=0, last_event_at=None,
        latest_run_quality=None, sla_threshold_seconds=60, now=NOW,
    )
    assert payload["status"] == "idle"
    assert payload["reason"] == "no_materialized_events"


def test_dataset_freshness_boundary_and_degraded_precedence():
    boundary = dataset_freshness_payload(
        "ds1_creditcard", event_count=1, last_event_at=NOW - timedelta(seconds=60),
        latest_run_quality=None, sla_threshold_seconds=60, now=NOW,
    )
    assert boundary["status"] == "ready"
    stale = dataset_freshness_payload(
        "ds1_creditcard", event_count=1, last_event_at=NOW - timedelta(seconds=61),
        latest_run_quality=None, sla_threshold_seconds=60, now=NOW,
    )
    assert stale["status"] == "stale"
    degraded = dataset_freshness_payload(
        "ds1_creditcard", event_count=1, last_event_at=NOW,
        latest_run_quality={"status": "degraded", "reason": "missing", "reconciliation_completeness": 1},
        sla_threshold_seconds=60, now=NOW,
    )
    assert degraded["status"] == "degraded"
