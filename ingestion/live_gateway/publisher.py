"""Reliable Kafka publishing for canonical live-event contracts."""

import json
import threading
from dataclasses import dataclass
from typing import Any

from kafka import KafkaProducer


class PublishUnavailable(RuntimeError):
    """Raised when an event cannot be acknowledged by Kafka."""


@dataclass(frozen=True)
class PublishResult:
    topic: str
    partition: int
    offset: int


class KafkaEventPublisher:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer: KafkaProducer | None = None
        self._lock = threading.Lock()
        self.last_error: str | None = None

    def start(self) -> None:
        if self._producer is not None:
            return
        with self._lock:
            if self._producer is not None:
                return
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    acks="all",
                    retries=10,
                    max_in_flight_requests_per_connection=1,
                    max_block_ms=5_000,
                    request_timeout_ms=15_000,
                    value_serializer=lambda value: json.dumps(value, separators=(",", ":")).encode("utf-8"),
                )
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)
                raise PublishUnavailable("Kafka is unavailable") from exc

    def ready(self) -> bool:
        try:
            self.start()
            return bool(self._producer and self._producer.bootstrap_connected())
        except PublishUnavailable:
            return False

    def publish(self, topic: str, key: str, event: dict[str, Any]) -> PublishResult:
        try:
            self.start()
            assert self._producer is not None
            metadata = self._producer.send(topic, key=key.encode("utf-8"), value=event).get(timeout=15)
            self.last_error = None
            return PublishResult(topic=metadata.topic, partition=metadata.partition, offset=metadata.offset)
        except Exception as exc:
            self.last_error = str(exc)
            raise PublishUnavailable("Kafka did not acknowledge the event") from exc

    def close(self) -> None:
        if self._producer is None:
            return
        try:
            self._producer.flush(timeout=10)
            self._producer.close(timeout=10)
        finally:
            self._producer = None
