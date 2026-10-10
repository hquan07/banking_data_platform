"""Live API must use the database role, not the JWT's stale role claim."""

import os
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_E2E") != "1", reason="requires live Compose stack")


def test_role_revocation_and_case_search():
    from dotenv import load_dotenv
    import psycopg2

    load_dotenv()
    with psycopg2.connect(
        host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username FROM users WHERE role = 'ANALYST' ORDER BY id LIMIT 1")
            analyst_id, analyst_name = cursor.fetchone()
            cursor.execute("SELECT id, username FROM users WHERE role = 'ADMIN' ORDER BY id LIMIT 1")
            admin_id, admin_name = cursor.fetchone()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

    def token(user_id, username):
        encode = lambda value: base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).rstrip(b"=")
        signing_input = b".".join((encode({"alg": "HS256", "typ": "JWT"}),
                                   encode({"id": user_id, "sub": username, "role": "ADMIN", "exp": int(expiry.timestamp())})))
        signature = hmac.new(os.environ["JWT_SECRET_KEY"].encode(), signing_input, hashlib.sha256).digest()
        return (signing_input + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")).decode()

    analyst_request = Request(
        "http://localhost:8000/api/users",
        headers={"Authorization": f"Bearer {token(analyst_id, analyst_name)}"},
    )
    with pytest.raises(HTTPError) as error:
        urlopen(analyst_request, timeout=10)
    assert error.value.code == 403

    admin_request = Request(
        "http://localhost:8000/api/alerts?page=1&limit=1&search=NONEXISTENT_CASE_SEARCH_42",
        headers={"Authorization": f"Bearer {token(admin_id, admin_name)}"},
    )
    with urlopen(admin_request, timeout=10) as response:
        result = json.load(response)
    assert result["total"] == 0
    assert result["data"] == []

    protected_analytics = [
        "/api/graph/circular",
        "/api/graph/benchmark",
        "/api/graph/money-flow",
        "/api/graph/fraud-sequences",
        "/api/analytics/history",
    ]
    for path in protected_analytics:
        with pytest.raises(HTTPError) as error:
            urlopen(f"http://localhost:8000{path}", timeout=10)
        assert error.value.code == 401

        authorized_request = Request(
            f"http://localhost:8000{path}",
            headers={"Authorization": f"Bearer {token(admin_id, admin_name)}"},
        )
        with urlopen(authorized_request, timeout=10) as response:
            assert response.status == 200

    import websocket

    with pytest.raises(websocket.WebSocketBadStatusException):
        websocket.create_connection("ws://localhost:8000/ws/stream", timeout=5)
    connection = websocket.create_connection(
        "ws://localhost:8000/ws/stream", timeout=5,
        subprotocols=["bearer", token(admin_id, admin_name)],
    )
    try:
        assert connection.getsubprotocol() == "bearer"
    finally:
        connection.close()
