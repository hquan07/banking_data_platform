from datetime import datetime, timedelta, timezone

import pytest

from governance.retention import RetentionPlan, classify_run_rows, parse_cutoff, validate_source


NOW = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
CUTOFF = NOW - timedelta(days=30)


def row(run_id, *, status="COMPLETED", ended_at=None, legal_hold=False,
        open_case_count=0, retention_purged_at=None):
    return {
        "run_id": run_id, "status": status,
        "ended_at": ended_at if ended_at is not None else CUTOFF - timedelta(seconds=1),
        "legal_hold": legal_hold, "open_case_count": open_case_count,
        "retention_purged_at": retention_purged_at,
    }


def test_cutoff_must_be_explicit_aware_and_in_the_past():
    assert parse_cutoff("2026-09-01T00:00:00Z", now=NOW).tzinfo == timezone.utc
    with pytest.raises(ValueError, match="timezone"):
        parse_cutoff("2026-09-01T00:00:00", now=NOW)
    with pytest.raises(ValueError, match="past"):
        parse_cutoff(NOW.isoformat(), now=NOW)
    with pytest.raises(ValueError, match="ISO-8601"):
        parse_cutoff("last month", now=NOW)
    with pytest.raises(ValueError, match="lowercase"):
        validate_source("DS3-PaySim")


def test_retention_boundary_and_protection_reasons_are_fail_closed():
    candidates, protected = classify_run_rows([
        row("eligible"),
        row("boundary", ended_at=CUTOFF),
        row("newer", ended_at=CUTOFF + timedelta(seconds=1)),
        row("held", legal_hold=True),
        row("case", open_case_count=1),
        row("paused", status="PAUSED"),
        row("purged", retention_purged_at=NOW),
    ], CUTOFF)
    assert candidates == ["eligible"]
    assert protected == {
        "active_or_paused": ["paused"],
        "already_purged": ["purged"],
        "legal_hold": ["held"],
        "not_before_cutoff": ["boundary", "newer"],
        "open_case": ["case"],
    }


def test_plan_fingerprint_is_deterministic_and_detects_candidate_drift():
    stores = {
        "postgres": {"candidate_count": 2, "protected_count": 1, "details": {"events": 2}},
    }
    first = RetentionPlan("ds3_paysim", CUTOFF, ("run-a",), {"legal_hold": ["run-b"]}, stores)
    same = RetentionPlan("ds3_paysim", CUTOFF, ("run-a",), {"legal_hold": ["run-b"]}, stores)
    changed = RetentionPlan(
        "ds3_paysim", CUTOFF, ("run-a",), {"legal_hold": ["run-b"]},
        {"postgres": {"candidate_count": 3, "protected_count": 1, "details": {"events": 3}}},
    )
    assert first.fingerprint == same.fingerprint
    assert first.fingerprint != changed.fingerprint
    assert first.summary()["dry_run_required_for_apply"] is True
