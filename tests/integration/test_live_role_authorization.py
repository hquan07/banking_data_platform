"""Live API must use the database role, not the JWT's stale role claim."""

import os
import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt
import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_E2E") != "1", reason="requires live Compose stack")


def test_role_revocation_and_case_search():
    from dotenv import load_dotenv

    load_dotenv()
    def login(username, password):
        request = Request(
            "http://localhost:8000/api/auth/login",
            data=urlencode({"username": username, "password": password}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(request, timeout=10) as response:
            return json.load(response)["access_token"]

    analyst_token = login("analyst_1", os.environ["DASHBOARD_ANALYST_PASSWORD"])
    stale_claim = jwt.decode(
        analyst_token, options={"verify_signature": False}, algorithms=["HS256"],
    )
    stale_claim["role"] = "ADMIN"
    analyst_token = jwt.encode(stale_claim, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    admin_token = login("admin", os.environ["DASHBOARD_ADMIN_PASSWORD"])

    analyst_request = Request(
        "http://localhost:8000/api/users",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    with pytest.raises(HTTPError) as error:
        urlopen(analyst_request, timeout=10)
    assert error.value.code == 403

    admin_request = Request(
        "http://localhost:8000/api/alerts?page=1&limit=1&search=NONEXISTENT_CASE_SEARCH_42",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    with urlopen(admin_request, timeout=10) as response:
        result = json.load(response)
    assert result["total"] == 0
    assert result["data"] == []

    protected_analytics = [
        "/api/graph/circular",
        "/api/graph/benchmark",
        "/api/graph/evidence?run_id=00000000-0000-0000-0000-000000000000&event_id=missing",
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
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        with urlopen(authorized_request, timeout=10) as response:
            assert response.status == 200

    import websocket

    with pytest.raises(websocket.WebSocketBadStatusException):
        websocket.create_connection("ws://localhost:8000/ws/stream", timeout=5)
    connection = websocket.create_connection(
        "ws://localhost:8000/ws/stream", timeout=5,
        subprotocols=["bearer", admin_token],
    )
    try:
        assert connection.getsubprotocol() == "bearer"
    finally:
        connection.close()
