import unittest

from scripts.reconcile_payment_events import compare_records, partition_quarantined_events


class ReconciliationTest(unittest.TestCase):
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
