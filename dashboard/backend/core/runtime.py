"""Explicit runtime mode and startup configuration validation."""

import os


APP_MODE = os.environ.get("APP_MODE", "integration").lower()
if APP_MODE not in {"integration", "production"}:
    raise RuntimeError("APP_MODE must be integration or production")


def validate_runtime_config() -> None:
    required = (
        "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "JWT_SECRET_KEY",
        "DASHBOARD_ADMIN_PASSWORD", "DASHBOARD_ANALYST_PASSWORD",
    )
    required += (
        "KAFKA_BOOTSTRAP_SERVER", "REDIS_HOST", "NEO4J_URI",
        "NEO4J_USER", "NEO4J_PASSWORD", "CLICKHOUSE_HOST",
        "CLICKHOUSE_DB", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD",
        "MINIO_ENDPOINT", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD",
        "LIVE_INGESTION_URL",
    )
    missing = [name for name in required if not os.environ.get(name) or os.environ[name].startswith("replace-with-")]
    if missing:
        raise RuntimeError(f"Missing or placeholder configuration: {', '.join(missing)}")
