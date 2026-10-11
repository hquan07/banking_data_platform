"""Pure reconciliation logic with bounded diagnostic evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


CLASSIFICATIONS = (
    "EXACT", "PENDING", "DUPLICATE", "MISSING", "MISMATCHED", "QUARANTINED",
)


@dataclass(frozen=True)
class ReconciliationOutcome:
    expected_count: int
    actual_count: int
    observed_at: datetime
    due_at: datetime
    findings: dict[str, tuple[str, ...]]
    finding_counts: dict[str, int]

    @property
    def complete(self) -> bool:
        return "PENDING" not in self.findings


def _group(records: Iterable[tuple[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for identity, fingerprint in records:
        grouped[str(identity)].append(str(fingerprint))
    return grouped


def reconcile_records(
    expected: Iterable[tuple[str, str]],
    actual: Iterable[tuple[str, str]],
    *,
    quarantined_ids: Iterable[str] = (),
    observed_at: datetime,
    due_at: datetime,
    sample_limit: int = 25,
) -> ReconciliationOutcome:
    """Classify identity/fingerprint differences without retaining full records."""
    if sample_limit < 1 or sample_limit > 25:
        raise ValueError("sample_limit must be between 1 and 25")
    if observed_at.tzinfo is None or due_at.tzinfo is None:
        raise ValueError("observed_at and due_at must be timezone-aware")

    expected_rows = list(expected)
    actual_rows = list(actual)
    expected_by_id = _group(expected_rows)
    actual_by_id = _group(actual_rows)
    quarantined = {str(value) for value in quarantined_ids} & set(expected_by_id)

    duplicate = {
        identity for rows in (expected_rows, actual_rows)
        for identity, count in Counter(identity for identity, _ in rows).items()
        if count > 1
    }
    common = set(expected_by_id) & set(actual_by_id)
    mismatched = {
        identity for identity in common
        if set(expected_by_id[identity]) != set(actual_by_id[identity])
    }
    mismatched.update(set(actual_by_id) - set(expected_by_id))
    absent = set(expected_by_id) - set(actual_by_id) - quarantined
    missing_classification = "PENDING" if observed_at < due_at else "MISSING"

    raw_findings = {
        "DUPLICATE": duplicate,
        "MISMATCHED": mismatched,
        missing_classification: absent,
        "QUARANTINED": quarantined,
    }
    findings = {
        classification: tuple(sorted(identities)[:sample_limit])
        for classification, identities in raw_findings.items()
        if identities
    }
    finding_counts = {
        classification: len(identities)
        for classification, identities in raw_findings.items()
        if identities
    }
    if not findings:
        findings = {"EXACT": ()}
        finding_counts = {"EXACT": 0}
    return ReconciliationOutcome(
        expected_count=len(expected_rows),
        actual_count=len(actual_rows),
        observed_at=observed_at,
        due_at=due_at,
        findings=findings,
        finding_counts=finding_counts,
    )


def reconcile_count(
    expected_count: int,
    actual_count: int,
    *,
    observed_at: datetime,
    due_at: datetime,
    sample_ids: Iterable[str] = (),
    sample_limit: int = 25,
) -> ReconciliationOutcome:
    """Classify an aggregate count when record identities are unavailable."""
    if expected_count < 0 or actual_count < 0:
        raise ValueError("counts must be non-negative")
    if sample_limit < 1 or sample_limit > 25:
        raise ValueError("sample_limit must be between 1 and 25")
    if observed_at.tzinfo is None or due_at.tzinfo is None:
        raise ValueError("observed_at and due_at must be timezone-aware")
    difference = actual_count - expected_count
    if difference == 0:
        classification = "EXACT"
        discrepancy_count = 0
    elif difference > 0:
        classification = "DUPLICATE"
        discrepancy_count = difference
    else:
        classification = "PENDING" if observed_at < due_at else "MISSING"
        discrepancy_count = -difference
    samples = tuple(sorted({str(value) for value in sample_ids})[:sample_limit])
    return ReconciliationOutcome(
        expected_count=expected_count,
        actual_count=actual_count,
        observed_at=observed_at,
        due_at=due_at,
        findings={classification: () if classification == "EXACT" else samples},
        finding_counts={classification: discrepancy_count},
    )
