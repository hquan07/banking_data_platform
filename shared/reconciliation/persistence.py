"""PostgreSQL persistence for bounded reconciliation outcomes."""

from __future__ import annotations

import json
from typing import Any

from .engine import ReconciliationOutcome


def persist_outcome(
    connection: Any,
    *,
    run_id: str,
    store: str,
    metric: str,
    window_key: str,
    freshness_sla_seconds: int,
    outcome: ReconciliationOutcome,
) -> str:
    if freshness_sla_seconds < 0:
        raise ValueError("freshness_sla_seconds must be non-negative")
    if not metric or len(metric) > 80:
        raise ValueError("metric must contain at most 80 characters")
    if not window_key or len(window_key) > 500:
        raise ValueError("window_key must contain at most 500 characters")

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pipeline_reconciliation_checks
                    (run_id, store, metric, window_key, expected_count,
                     freshness_sla_seconds, due_at, observed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, store, metric, window_key) DO UPDATE SET
                    expected_count = EXCLUDED.expected_count,
                    freshness_sla_seconds = EXCLUDED.freshness_sla_seconds,
                    due_at = EXCLUDED.due_at,
                    observed_at = EXCLUDED.observed_at,
                    updated_at = NOW()
                RETURNING check_id::text
                """,
                (
                    run_id, store, metric, window_key, outcome.expected_count,
                    freshness_sla_seconds, outcome.due_at, outcome.observed_at,
                ),
            )
            check_id = cursor.fetchone()[0]
            cursor.execute(
                "DELETE FROM pipeline_reconciliation_results WHERE check_id = %s",
                (check_id,),
            )
            for classification, sample_ids in outcome.findings.items():
                discrepancy_count = outcome.finding_counts[classification]
                cursor.execute(
                    """
                    INSERT INTO pipeline_reconciliation_results
                        (check_id, run_id, store, metric, window_key, classification,
                         expected_count, actual_count, discrepancy_count,
                         sample_ids, observed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        check_id, run_id, store, metric, window_key, classification,
                        outcome.expected_count, outcome.actual_count, discrepancy_count,
                        json.dumps(list(sample_ids)), outcome.observed_at,
                    ),
                )
    return check_id
