"""Authenticated HTTP ingress for canonical operational banking events."""

import hmac
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status

from ingestion.live_gateway.publisher import KafkaEventPublisher, PublishUnavailable
from shared.payment_contract import PAYMENT_TOPIC, normalize_payment_event
from shared.transfer_contract import normalize_transfer_event

TRANSFER_TOPIC = "transfer-events"
DEFAULT_INTEGRATION_KEY = "integration-live-key-change-me"


def _configured_api_key() -> str:
    app_mode = os.environ.get("APP_MODE", "integration").lower()
    api_key = os.environ.get("LIVE_INGESTION_API_KEY", "")
    if app_mode == "integration" and not api_key:
        return DEFAULT_INTEGRATION_KEY
    if not api_key or api_key.startswith("replace-with-") or (app_mode == "production" and api_key == DEFAULT_INTEGRATION_KEY):
        raise RuntimeError("LIVE_INGESTION_API_KEY must be configured with a non-placeholder value")
    return api_key


def create_app(event_publisher: Any | None = None) -> FastAPI:
    publisher = event_publisher or KafkaEventPublisher(
        os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "banking_kafka:9092")
    )
    api_key = _configured_api_key()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            publisher.start()
        except PublishUnavailable:
            # Keep liveness available while readiness reports Kafka degradation.
            pass
        yield
        publisher.close()

    gateway = FastAPI(title="Banking Live Ingestion Gateway", version="1.0.0", lifespan=lifespan)
    gateway.state.publisher = publisher

    def authorize_source(x_live_source_key: str | None = Header(default=None)) -> None:
        if not x_live_source_key or not hmac.compare_digest(x_live_source_key, api_key):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid live source key")

    def publish(topic: str, key: str, event: dict[str, Any]) -> dict[str, Any]:
        try:
            result = publisher.publish(topic, key, event)
        except PublishUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        return {
            "status": "accepted",
            "event_id": event["event_id"],
            "trace_id": event["trace_id"],
            "topic": result.topic,
            "partition": result.partition,
            "offset": result.offset,
        }

    @gateway.get("/health/live")
    def liveness() -> dict[str, str]:
        return {"status": "alive"}

    @gateway.get("/health/ready")
    def readiness() -> dict[str, Any]:
        if not publisher.ready():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready", "kafka": False},
            )
        return {"status": "ready", "kafka": True}

    @gateway.post("/v1/events/payments", status_code=status.HTTP_202_ACCEPTED)
    def ingest_payment(
        payload: dict[str, Any],
        _: None = Depends(authorize_source),
        x_source_system: str = Header(default="external"),
    ) -> dict[str, Any]:
        try:
            event = normalize_payment_event(payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        event["source_system"] = x_source_system[:100]
        return publish(PAYMENT_TOPIC, event["payment_id"], event)

    @gateway.post("/v1/events/transfers", status_code=status.HTTP_202_ACCEPTED)
    def ingest_transfer(
        payload: dict[str, Any],
        _: None = Depends(authorize_source),
        x_source_system: str = Header(default="external"),
    ) -> dict[str, Any]:
        try:
            event = normalize_transfer_event(payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        event["source_system"] = x_source_system[:100]
        return publish(TRANSFER_TOPIC, event["from_account_id"], event)

    return gateway


app = create_app()
