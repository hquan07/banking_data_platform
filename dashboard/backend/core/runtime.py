"""Explicit runtime mode and startup configuration validation."""

import os


APP_MODE = os.environ.get("APP_MODE", "integration").lower()
if APP_MODE not in {"demo", "integration", "production"}:
    raise RuntimeError("APP_MODE must be demo, integration or production")

ENABLE_MOCK_DATA = os.environ.get("ENABLE_MOCK_DATA", "false").lower() == "true"
if ENABLE_MOCK_DATA and APP_MODE != "demo":
    raise RuntimeError("ENABLE_MOCK_DATA requires APP_MODE=demo")


def demo_mode() -> bool:
    return APP_MODE == "demo"


def validate_runtime_config() -> None:
    required = (
        "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "JWT_SECRET_KEY",
        "DASHBOARD_ADMIN_PASSWORD", "DASHBOARD_ANALYST_PASSWORD",
    )
    if APP_MODE != "demo":
        required += (
            "KAFKA_BOOTSTRAP_SERVER", "REDIS_HOST", "NEO4J_URI",
            "NEO4J_USER", "NEO4J_PASSWORD", "CLICKHOUSE_HOST",
            "CLICKHOUSE_DB", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD",
            "MINIO_ENDPOINT", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD",
        )
    missing = [name for name in required if not os.environ.get(name) or os.environ[name].startswith("replace-with-")]
    if missing:
        raise RuntimeError(f"Missing or placeholder configuration: {', '.join(missing)}")
