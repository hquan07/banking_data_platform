import importlib.util
import os
import sys
from pathlib import Path

import jwt
import pytest


ROOT = Path(__file__).resolve().parents[2]
SERVICE_PATH = ROOT / "dashboard/backend/services/security_controls.py"
SPEC = importlib.util.spec_from_file_location("security_controls_test", SERVICE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key, seconds):
        self.expirations[key] = seconds


def test_fingerprint_is_stable_and_does_not_expose_source():
    value = MODULE.fingerprint("203.0.113.10")
    assert len(value) == 64
    assert value == MODULE.fingerprint("203.0.113.10")
    assert "203.0.113.10" not in value


def test_rate_limit_allows_boundary_then_rejects():
    redis = FakeRedis()
    decisions = [
        MODULE.consume_rate_limit(
            redis,
            scope="login",
            identity="analyst:client",
            limit=2,
            window_seconds=60,
            now=120.0,
        )
        for _ in range(3)
    ]
    assert [decision.allowed for decision in decisions] == [True, True, False]
    assert decisions[-1].remaining == 0
    assert decisions[-1].retry_after_seconds == 60
    assert next(iter(redis.expirations.values())) == 120


@pytest.mark.parametrize("limit,window", [(0, 60), (5, 0), (-1, 60)])
def test_rate_limit_rejects_invalid_configuration(limit, window):
    with pytest.raises(ValueError, match="must be positive"):
        MODULE.consume_rate_limit(
            FakeRedis(),
            scope="api",
            identity="client",
            limit=limit,
            window_seconds=window,
        )


def test_access_token_contains_session_and_issue_time(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-secret-key-that-is-at-least-32-chars")
    backend = ROOT / "dashboard/backend"
    sys.path.insert(0, str(backend))
    try:
        sys.modules.pop("core.security", None)
        from core.security import ALGORITHM, SECRET_KEY, create_access_token

        token = create_access_token({"sub": "analyst", "id": 7, "role": "ANALYST"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    finally:
        sys.path.remove(str(backend))
        sys.modules.pop("core.security", None)
    assert payload["sub"] == "analyst"
    assert payload["jti"]
    assert payload["iat"] < payload["exp"]


def test_security_event_migration_is_append_only_and_retained():
    migration = (ROOT / "dashboard/backend/sql/p2_security_controls.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS auth_sessions" in migration
    assert "CREATE TABLE IF NOT EXISTS security_events" in migration
    assert "security_events are append-only" in migration
    assert "retain_until" in migration

