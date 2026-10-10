"""Live contract checks for the dataset-backed dashboard APIs."""

import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_E2E") != "1",
    reason="requires live Compose stack",
)

BASE_URL = "http://localhost:8000"
DATASET_SEGMENTS = {
    "ds1_creditcard": {"amount_band"},
    "ds3_paysim": {"transaction_type"},
    "ds4_baf": {"source", "device_os", "payment_type", "age_band"},
}


def _login_token():
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


def _get(path, token):
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urlopen(request, timeout=20) as response:
        assert response.status == 200
        return json.load(response)


def test_dataset_dashboard_contracts_are_authenticated_and_source_scoped():
    with pytest.raises(HTTPError) as error:
        urlopen(f"{BASE_URL}/api/datasets/status", timeout=10)
    assert error.value.code == 401

    token = _login_token()
    status = _get("/api/datasets/status", token)
    assert {item["dataset_id"] for item in status} == set(DATASET_SEGMENTS)
    assert all(item["status"] == "loaded" and item["event_count"] > 0 for item in status)

    for dataset_id, expected_segments in DATASET_SEGMENTS.items():
        overview = _get(f"/api/datasets/{dataset_id}/overview", token)
        assert overview["dataset_id"] == dataset_id
        assert overview["event_count"] > 0
        assert overview["evaluated_count"] <= overview["event_count"]
        assert set(overview["confusion_matrix"]) == {"tp", "fp", "tn", "fn"}

        timeseries = _get(f"/api/datasets/{dataset_id}/timeseries", token)
        assert timeseries
        assert {"bucket", "time_unit", "event_count", "fraud_count", "total_amount"} <= timeseries[0].keys()

        segments = _get(f"/api/datasets/{dataset_id}/segments", token)
        assert segments["dataset_id"] == dataset_id
        assert set(segments["segments"]) == expected_segments
        assert all(rows for rows in segments["segments"].values())

    with pytest.raises(HTTPError) as error:
        _get("/api/datasets/not-a-dataset/overview", token)
    assert error.value.code == 404


def test_dataset_specific_diagnostics_keep_their_native_contracts():
    token = _login_token()
    balance = _get("/api/datasets/balance-anomalies", token)
    assert balance["total_events"] > 0
    assert balance["evaluated_events"] <= balance["total_events"]

    account = _get("/api/datasets/account-risk", token)
    assert account["total_applications"] > 0
    assert isinstance(account["by_source"], list)
    assert isinstance(account["by_device_os"], list)

    behavior = _get("/api/datasets/behavior-distributions", token)
    assert behavior["velocity_heatmap"]
    assert behavior["session_bins"]

    assert isinstance(_get("/api/datasets/performance", token), list)
    assert isinstance(_get("/api/datasets/rule-hits", token), list)
    assert isinstance(_get("/api/datasets/model-candidates", token), list)
