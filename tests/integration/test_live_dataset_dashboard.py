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


def test_dataset_freshness_uses_shared_operational_contract():
    token = _login_token()
    rows = _get("/api/datasets/freshness?sla_threshold_seconds=3600", token)
    assert {row["dataset_id"] for row in rows} == set(DATASET_SEGMENTS)
    required = {
        "status", "reason", "observed_at", "last_success_at",
        "data_age_seconds", "sla_threshold_seconds",
        "reconciliation_completeness", "event_count",
    }
    assert all(required <= row.keys() for row in rows)
    assert all(row["status"] in {
        "ready", "idle", "running", "stale", "degraded", "failed",
        "completed", "not_applicable",
    } for row in rows)


def test_capability_manifest_is_versioned_and_rejects_unknown_versions():
    token = _login_token()
    manifest = _get("/api/capabilities?version=1", token)
    assert manifest["manifest_version"] == 1
    datasets = {item["dataset_id"]: item for item in manifest["datasets"]}
    assert datasets["ds3_paysim"]["tab_availability"]["analytics"]["supported"] is True
    assert datasets["ds1_creditcard"]["tab_availability"]["analytics"]["supported"] is False

    with pytest.raises(HTTPError) as unsupported:
        _get("/api/capabilities?version=999", token)
    assert unsupported.value.code == 406


def test_investigation_source_event_preserves_run_identity_and_payload():
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    connection = psycopg2.connect(
        host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_id, event_id, payload FROM benchmark_events "
                "WHERE dataset_id = 'ds3_paysim' ORDER BY ingested_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
    finally:
        connection.close()
    if row is None:
        pytest.skip("DS3 benchmark has no source event")

    run_id, event_id, payload = row
    token = _login_token()
    source = _get(
        f"/api/datasets/ds3_paysim/events/{event_id}?{urlencode({'run_id': str(run_id)})}",
        token,
    )
    assert source["dataset_id"] == "ds3_paysim"
    assert source["run_id"] == str(run_id)
    assert source["event_id"] == event_id
    assert source["payload"] == payload
    assert {"source_row_id", "event_type", "ground_truth_is_fraud", "source_file"} <= source.keys()
