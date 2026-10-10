from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from ingestion.live_gateway.app import create_app
from ingestion.live_simulator import generate_payment, generate_transfer
from shared.payment_contract import normalize_payment_event
from shared.transfer_contract import normalize_transfer_event


class FakePublisher:
    def __init__(self):
        self.events = []
        self.started = False
        self.closed = False

    def start(self):
        self.started = True

    def close(self):
        self.closed = True

    def ready(self):
        return True

    def publish(self, topic, key, event):
        self.events.append((topic, key, event))
        return SimpleNamespace(topic=topic, partition=1, offset=12)


def route_endpoint(app, path):
    return next(route.endpoint for route in app.routes if getattr(route, "path", None) == path)


def test_gateway_normalizes_and_routes_canonical_events(monkeypatch):
    monkeypatch.setenv("LIVE_INGESTION_API_KEY", "unit-test-live-key")
    publisher = FakePublisher()
    app = create_app(publisher)

    payment = generate_payment(1, __import__("random").Random(1))
    payment_result = route_endpoint(app, "/v1/events/payments")(payment, None, "unit-source")
    transfer = generate_transfer(1, __import__("random").Random(2))
    transfer_result = route_endpoint(app, "/v1/events/transfers")(transfer, None, "unit-source")

    assert payment_result["status"] == transfer_result["status"] == "accepted"
    assert publisher.events[0][0:2] == ("payment-events", payment["payment_id"])
    assert publisher.events[1][0:2] == ("transfer-events", transfer["from_account_id"])
    assert publisher.events[0][2]["source_system"] == "unit-source"
    assert publisher.events[1][2]["source_system"] == "unit-source"
    normalize_payment_event(publisher.events[0][2])
    normalize_transfer_event(publisher.events[1][2])


def test_gateway_rejects_invalid_contract_before_publish(monkeypatch):
    monkeypatch.setenv("LIVE_INGESTION_API_KEY", "unit-test-live-key")
    publisher = FakePublisher()
    app = create_app(publisher)

    with pytest.raises(HTTPException) as payment_error:
        route_endpoint(app, "/v1/events/payments")({}, None, "unit-source")
    with pytest.raises(HTTPException) as transfer_error:
        route_endpoint(app, "/v1/events/transfers")({}, None, "unit-source")

    assert payment_error.value.status_code == 422
    assert transfer_error.value.status_code == 422
    assert publisher.events == []


def test_production_requires_a_real_source_key(monkeypatch):
    monkeypatch.setenv("APP_MODE", "production")
    monkeypatch.setenv("LIVE_INGESTION_API_KEY", "replace-with-a-live-key")
    with pytest.raises(RuntimeError, match="LIVE_INGESTION_API_KEY"):
        create_app(FakePublisher())
