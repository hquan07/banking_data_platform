"""Live authentication session, revocation and rate-limit checks."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_E2E") != "1", reason="requires live Compose stack",
)
BASE_URL = "http://127.0.0.1:8000"


def _request(path, *, data=None, token=None, expected=200):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(data).encode()
    request = Request(f"{BASE_URL}{path}", data=data, headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            assert response.status == expected
            return json.loads(response.read())
    except HTTPError as exc:
        body = exc.read().decode()
        assert exc.code == expected, body
        return json.loads(body)


def test_session_is_persisted_and_immediately_revoked():
    token = _request(
        "/api/auth/login",
        data={"username": "admin", "password": os.environ["DASHBOARD_ADMIN_PASSWORD"]},
    )["access_token"]
    sessions = _request("/api/auth/sessions", token=token)["sessions"]
    assert sessions
    assert any(row["session_id"] == jwt.decode(
        token, options={"verify_signature": False}, algorithms=["HS256"],
    )["jti"] for row in sessions)
    assert _request("/api/auth/logout", data={}, token=token)["revoked"] is True
    _request("/api/auth/sessions", token=token, expected=401)


def test_expired_or_unknown_session_is_rejected():
    payload = {
        "sub": "admin",
        "id": 1,
        "role": "ADMIN",
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=2),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    _request("/api/auth/sessions", token=token, expected=401)

    payload.update(
        {
            "jti": "not-a-uuid",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
        }
    )
    malformed = jwt.encode(payload, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    _request("/api/auth/sessions", token=malformed, expected=401)


def test_login_rate_limit_records_rejection():
    username = f"missing-{uuid.uuid4().hex}"
    limit = int(os.environ.get("LOGIN_RATE_LIMIT", "10"))
    for _ in range(limit):
        _request(
            "/api/auth/login",
            data={"username": username, "password": "not-a-real-password"},
            expected=401,
        )
    _request(
        "/api/auth/login",
        data={"username": username, "password": "not-a-real-password"},
        expected=429,
    )


def test_security_events_are_visible_and_retention_is_enforced():
    from dotenv import load_dotenv
    import psycopg2

    load_dotenv()
    connection = psycopg2.connect(
        host="localhost",
        port=5433,
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM security_events "
                "WHERE event_type IN ('LOGIN', 'LOGOUT')"
            )
            assert cursor.fetchone()[0] > 0
        with pytest.raises(psycopg2.errors.RaiseException, match="append-only"):
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE security_events SET details = details "
                    "WHERE event_id = (SELECT max(event_id) FROM security_events)"
                )
        connection.rollback()
    finally:
        connection.close()

    with urlopen(f"{BASE_URL}/metrics", timeout=10) as response:
        metrics = response.read().decode()
    assert "banking_security_events_total" in metrics
    assert "banking_rate_limit_rejections_total" in metrics
    assert "banking_active_sessions" in metrics
