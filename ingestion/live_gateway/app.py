"""Authenticated HTTP ingress for canonical operational banking events."""

import hmac
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from ingestion.live_gateway.publisher import KafkaEventPublisher, PublishUnavailable
from shared.payment_contract import PAYMENT_TOPIC, normalize_payment_event
from shared.transfer_contract import normalize_transfer_event

TRANSFER_TOPIC = "transfer-events"
DEFAULT_INTEGRATION_KEY = "integration-live-key-change-me"
INGEST_EVENTS = Counter(
    "live_ingest_events_total", "Live events handled by the gateway", ("event_type", "status")
)
VALIDATION_FAILURES = Counter(
    "live_ingest_validation_failures_total", "Live events rejected by contract", ("event_type",)
)
KAFKA_FAILURES = Counter(
    "live_ingest_kafka_publish_failures_total", "Live events not acknowledged by Kafka", ("event_type",)
)
PUBLISH_LATENCY = Histogram(
    "live_ingest_publish_latency_seconds", "Gateway to Kafka acknowledgement latency", ("event_type",)
)
LAST_EVENT_TIMESTAMP = Gauge(
    "live_ingest_last_event_timestamp_seconds", "Last Kafka-acknowledged live event", ("event_type",)
)


class SourceState:
    def __init__(self) -> None:
        self.last_event_at: dict[str, str] = {}

    def accepted(self, event_type: str) -> None:
        self.last_event_at[event_type] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def snapshot(self, ready: bool) -> dict[str, Any]:
        latest = max(self.last_event_at.values(), default=None)
        active_window = int(os.environ.get("LIVE_SOURCE_ACTIVE_WINDOW_SECONDS", "60"))
        streaming = False
        if latest:
            last_time = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            streaming = (datetime.now(timezone.utc) - last_time).total_seconds() <= active_window
        return {
            "status": "streaming" if ready and streaming else "idle" if ready else "unavailable",
            "configured": True,
            "kafka": ready,
            "last_event_at": latest,
            "event_types_seen": sorted(self.last_event_at),
        }


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
    source_state = SourceState()

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

    def publish(topic: str, key: str, event: dict[str, Any], event_type: str) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            result = publisher.publish(topic, key, event)
        except PublishUnavailable as exc:
            INGEST_EVENTS.labels(event_type, "kafka_error").inc()
            KAFKA_FAILURES.labels(event_type).inc()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        PUBLISH_LATENCY.labels(event_type).observe(time.perf_counter() - started)
        INGEST_EVENTS.labels(event_type, "accepted").inc()
        LAST_EVENT_TIMESTAMP.labels(event_type).set_to_current_time()
        source_state.accepted(event_type)
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

    @gateway.get("/health/source")
    def source_health() -> dict[str, Any]:
        return source_state.snapshot(publisher.ready())

    @gateway.get("/metrics")
    def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @gateway.post("/v1/events/payments", status_code=status.HTTP_202_ACCEPTED)
    def ingest_payment(
        payload: dict[str, Any],
        _: None = Depends(authorize_source),
        x_source_system: str = Header(default="external"),
    ) -> dict[str, Any]:
        try:
            event = normalize_payment_event(payload)
        except ValueError as exc:
            INGEST_EVENTS.labels("payment", "validation_error").inc()
            VALIDATION_FAILURES.labels("payment").inc()
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        event["source_system"] = x_source_system[:100]
        return publish(PAYMENT_TOPIC, event["payment_id"], event, "payment")

    @gateway.post("/v1/events/transfers", status_code=status.HTTP_202_ACCEPTED)
    def ingest_transfer(
        payload: dict[str, Any],
        _: None = Depends(authorize_source),
        x_source_system: str = Header(default="external"),
    ) -> dict[str, Any]:
        try:
            event = normalize_transfer_event(payload)
        except ValueError as exc:
            INGEST_EVENTS.labels("transfer", "validation_error").inc()
            VALIDATION_FAILURES.labels("transfer").inc()
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        event["source_system"] = x_source_system[:100]
        return publish(TRANSFER_TOPIC, event["from_account_id"], event, "transfer")

    return gateway


app = create_app()
