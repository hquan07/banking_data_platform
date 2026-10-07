import unittest

from scripts.reconcile_payment_events import compare_records


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
