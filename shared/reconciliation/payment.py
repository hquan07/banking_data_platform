"""Payment-specific adapters built on the shared reconciliation model."""

from __future__ import annotations

from datetime import datetime

from .engine import ReconciliationOutcome, reconcile_records


def compare_records(events, postgres_rows, clickhouse_rows):
    """Keep the original operator summary contract for compatibility."""
    expected = {event["payment_id"]: event["event_id"] for event in events}
    postgres = dict(postgres_rows)
    clickhouse = dict(clickhouse_rows)
    return {
        "missing_postgres": sorted(set(expected) - set(postgres)),
        "missing_clickhouse": sorted(set(expected) - set(clickhouse)),
        "postgres_event_mismatch": sorted(
            payment_id for payment_id in expected.keys() & postgres.keys()
            if expected[payment_id] != postgres[payment_id]
        ),
        "clickhouse_event_mismatch": sorted(
            payment_id for payment_id in expected.keys() & clickhouse.keys()
            if expected[payment_id] != clickhouse[payment_id]
        ),
    }


def partition_quarantined_events(events, dlq_sources):
    """Separate events only when an exact Kafka source offset has DLQ evidence."""
    materialized, quarantined = [], []
    for event in events:
        source = event.get("_source")
        identity = None if source is None else (
            source.get("topic"), source.get("partition"), source.get("offset"),
        )
        (quarantined if identity in dlq_sources else materialized).append(event)
    return materialized, quarantined


def payment_store_outcome(
    events,
    store_rows,
    *,
    quarantined_events=(),
    observed_at: datetime,
    due_at: datetime,
    sample_limit: int = 25,
) -> ReconciliationOutcome:
    expected = [(event["payment_id"], event["event_id"]) for event in events]
    quarantined_ids = [event["payment_id"] for event in quarantined_events]
    return reconcile_records(
        expected, store_rows, quarantined_ids=quarantined_ids,
        observed_at=observed_at, due_at=due_at, sample_limit=sample_limit,
    )


def snapshot_window_key(events) -> str:
    boundaries: dict[int, list[int]] = {}
    for event in events:
        source = event.get("_source") or {}
        if source.get("topic") != "payment-events":
            continue
        boundaries.setdefault(int(source["partition"]), []).append(int(source["offset"]))
    if not boundaries:
        return "payment-events:empty"
    encoded = ",".join(
        f"p{partition}:{min(offsets)}-{max(offsets) + 1}"
        for partition, offsets in sorted(boundaries.items())
    )
    return f"payment-events:{encoded}"
