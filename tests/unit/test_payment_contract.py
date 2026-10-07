import unittest

from shared.payment_contract import normalize_payment_event


class PaymentContractTest(unittest.TestCase):
    def setUp(self):
        self.event = {
            "schema_version": 1,
            "event_id": "event-1",
            "trace_id": "trace-1",
            "payment_id": "payment-1",
            "customer_id": "customer-1",
            "account_id": "account-1",
            "amount": 12.34,
            "currency": "USD",
            "payment_method": "CARD",
            "channel": "ONLINE",
            "timestamp": "2026-10-07T12:00:00+07:00",
            "status": "CREATED",
        }

    def test_normalizes_timezone_to_utc(self):
        normalized = normalize_payment_event(self.event)
        self.assertEqual(normalized["timestamp"], "2026-10-07T05:00:00.000Z")
        self.assertEqual(normalized["event_id"], self.event["event_id"])

    def test_rejects_incompatible_version_and_invalid_money(self):
        for changes in ({"schema_version": 2}, {"amount": -1}, {"amount": 1.001}, {"amount": float("nan")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                normalize_payment_event({**self.event, **changes})

    def test_rejects_timestamp_without_timezone(self):
        with self.assertRaises(ValueError):
            normalize_payment_event({**self.event, "timestamp": "2026-10-07T12:00:00"})
