"""Single source of truth for runtime dependency readiness probes."""

from __future__ import annotations

import json
import os
from urllib.request import urlopen

from core.db import ch_client, get_s3_client, graph_driver, pg_conn, redis_client
from core.runtime import APP_MODE
from services.kafka_client import benchmark_kafka_ready, kafka_ready


REQUIRED_SPARK_APPS = ("PaymentStreamingProcessor", "FraudDetectionEngine")


def _check(client, probe) -> bool:
    if client is None or probe is None:
        return False
    try:
        return probe() is not False
    except Exception:
        return False


def fetch_spark_runtime() -> dict:
    with urlopen(os.environ["SPARK_MASTER_STATUS_URL"], timeout=3) as response:
        spark_payload = json.loads(response.read())
    active_apps = sorted(
        item.get("name") for item in spark_payload.get("activeapps", []) if item.get("name")
    )
    return {
        "status": spark_payload.get("status", "unknown"),
        "alive_workers": int(spark_payload.get("aliveworkers", 0)),
        "active_apps": active_apps,
    }


def fetch_live_source() -> dict:
    source_url = os.environ["LIVE_INGESTION_URL"].rstrip("/")
    with urlopen(f"{source_url}/health/source", timeout=3) as response:
        return json.loads(response.read())


def load_runtime_readiness() -> dict:
    def postgres_probe():
        with pg_conn.cursor() as cursor:
            cursor.execute("SELECT 1")

    dependencies = {"postgres": _check(pg_conn, postgres_probe)}
    dependencies.update({
        "kafka": kafka_ready.is_set() and benchmark_kafka_ready.is_set(),
        "redis": _check(redis_client, redis_client.ping if redis_client else None),
        "neo4j": _check(graph_driver, graph_driver.verify_connectivity if graph_driver else None),
        "clickhouse": _check(
            ch_client,
            lambda: ch_client.execute("EXISTS TABLE payment_events") == [(1,)],
        ),
    })
    try:
        s3_client = get_s3_client()
    except Exception:
        s3_client = None
    dependencies["minio"] = _check(
        s3_client, lambda: s3_client.head_bucket(Bucket="evidence") if s3_client else False,
    )

    spark_runtime = {"status": "unavailable", "alive_workers": 0, "active_apps": []}
    try:
        spark_runtime = fetch_spark_runtime()
        dependencies["spark"] = (
            spark_runtime["status"] == "ALIVE"
            and spark_runtime["alive_workers"] > 0
            and set(REQUIRED_SPARK_APPS).issubset(spark_runtime["active_apps"])
        )
    except Exception:
        dependencies["spark"] = False

    live_source = {
        "status": "unavailable", "configured": True, "kafka": False,
        "last_event_at": None, "event_types_seen": [],
    }
    try:
        live_source = fetch_live_source()
        dependencies["live_ingestion"] = live_source.get("kafka") is True
    except Exception:
        dependencies["live_ingestion"] = False

    return {
        "status": "ready" if all(dependencies.values()) else "not_ready",
        "mode": APP_MODE,
        **dependencies,
        "spark_runtime": spark_runtime,
        "live_source": live_source,
    }

