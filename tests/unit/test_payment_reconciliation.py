import unittest
from datetime import datetime, timedelta, timezone

from scripts.reconcile_payment_events import compare_records, partition_quarantined_events
from shared.reconciliation.engine import reconcile_count, reconcile_records
from shared.reconciliation.payment import snapshot_window_key


class ReconciliationTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)

    def test_reports_missing_and_mismatched_payments(self):
        events = [
            {"payment_id": "p1", "event_id": "e1"},
            {"payment_id": "p2", "event_id": "e2"},
        ]
        result = compare_records(events, [("p1", "e1")], [("p1", "other"), ("p2", "e2")])
        self.assertEqual(result["missing_postgres"], ["p2"])
        self.assertEqual(result["missing_clickhouse"], [])
        self.assertEqual(result["clickhouse_event_mismatch"], ["p1"])

    def test_requires_exact_dlq_source_evidence_before_excluding_event(self):
        events = [
            {"payment_id": "p1", "event_id": "e1", "_source": {
                "topic": "payment-events", "partition": 1, "offset": 20,
            }},
            {"payment_id": "p2", "event_id": "e2", "_source": {
                "topic": "payment-events", "partition": 1, "offset": 21,
            }},
        ]
        materialized, quarantined = partition_quarantined_events(
            events, {("payment-events", 1, 20)},
        )
        self.assertEqual([event["payment_id"] for event in materialized], ["p2"])
        self.assertEqual([event["payment_id"] for event in quarantined], ["p1"])

    def test_exact_match_has_no_discrepancy(self):
        outcome = reconcile_records(
            [("p1", "e1")], [("p1", "e1")],
            observed_at=self.now, due_at=self.now,
        )
        self.assertEqual(outcome.findings, {"EXACT": ()})
        self.assertTrue(outcome.complete)

    def test_eventual_arrival_is_pending_before_sla_then_missing(self):
        pending = reconcile_records(
            [("p1", "e1")], [], observed_at=self.now,
            due_at=self.now + timedelta(seconds=1),
        )
        missing = reconcile_records(
            [("p1", "e1")], [], observed_at=self.now,
            due_at=self.now - timedelta(seconds=1),
        )
        self.assertEqual(pending.findings, {"PENDING": ("p1",)})
        self.assertFalse(pending.complete)
        self.assertEqual(missing.findings, {"MISSING": ("p1",)})

    def test_duplicate_mismatch_and_unexpected_records_are_classified(self):
        outcome = reconcile_records(
            [("p1", "e1"), ("p2", "e2")],
            [("p1", "wrong"), ("p1", "wrong"), ("extra", "e3")],
            observed_at=self.now, due_at=self.now,
        )
        self.assertEqual(outcome.findings["DUPLICATE"], ("p1",))
        self.assertEqual(outcome.findings["MISMATCHED"], ("extra", "p1"))
        self.assertEqual(outcome.findings["MISSING"], ("p2",))

    def test_dlq_evidence_classifies_quarantine_instead_of_missing(self):
        outcome = reconcile_records(
            [("p1", "e1")], [], quarantined_ids=["p1"],
            observed_at=self.now, due_at=self.now,
        )
        self.assertEqual(outcome.findings, {"QUARANTINED": ("p1",)})
        self.assertTrue(outcome.complete)

    def test_evidence_samples_are_bounded_but_counts_remain_exact(self):
        expected = [(f"p{index}", f"e{index}") for index in range(30)]
        outcome = reconcile_records(
            expected, [], observed_at=self.now, due_at=self.now, sample_limit=5,
        )
        self.assertEqual(len(outcome.findings["MISSING"]), 5)
        self.assertEqual(outcome.finding_counts["MISSING"], 30)

    def test_snapshot_window_is_stable_across_partitions(self):
        events = [
            {"_source": {"topic": "payment-events", "partition": 1, "offset": 9}},
            {"_source": {"topic": "payment-events", "partition": 0, "offset": 5}},
            {"_source": {"topic": "payment-events", "partition": 1, "offset": 7}},
        ]
        self.assertEqual(snapshot_window_key(events), "payment-events:p0:5-6,p1:7-10")

    def test_count_reconciliation_respects_freshness_and_overage(self):
        pending = reconcile_count(
            5, 3, observed_at=self.now, due_at=self.now + timedelta(seconds=1),
        )
        duplicate = reconcile_count(
            3, 5, observed_at=self.now, due_at=self.now,
        )
        self.assertEqual(pending.finding_counts, {"PENDING": 2})
        self.assertEqual(duplicate.finding_counts, {"DUPLICATE": 2})
