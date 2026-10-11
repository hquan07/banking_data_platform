"""Compose-backed processor heartbeat contract."""

import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_E2E") != "1",
    reason="requires live Compose stack",
)

BASE_URL = "http://localhost:8000"
EXPECTED = {
    "payment_processor",
    "fraud_engine",
    "benchmark_processor",
    "live_graph_processor",
    "benchmark_graph_processor",
}


def _token():
    from dotenv import load_dotenv

    load_dotenv()
    body = urlencode({
        "username": os.environ.get("E2E_USERNAME", "admin"),
        "password": os.environ["DASHBOARD_ADMIN_PASSWORD"],
    }).encode()
    request = Request(
        f"{BASE_URL}/api/auth/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)["access_token"]


def test_all_required_processors_publish_current_heartbeats():
    token = _token()
    request = Request(
        f"{BASE_URL}/api/operations/processors",
        headers={"Authorization": f"Bearer {token}"},
    )
    deadline = time.monotonic() + 90
    payload = None
    while time.monotonic() < deadline:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
        if payload["status"] == "ready":
            break
        time.sleep(3)

    assert payload is not None
    assert payload["status"] == "ready"
    by_name = {item["processor_name"]: item for item in payload["processors"]}
    assert set(by_name) == EXPECTED
    assert all(by_name[name]["status"] == "running" for name in EXPECTED)
    assert all(by_name[name]["heartbeat_age_seconds"] <= 45 for name in EXPECTED)
