"""Live migration, authorization, API and optimistic-lock checks for pipeline runs."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_E2E") != "1", reason="requires the running Docker Compose stack",
)
BASE_URL = "http://localhost:8000/api"


def _token(username, password):
    request = Request(
        f"{BASE_URL}/auth/login",
        data=urlencode({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)["access_token"]


def _request(method, path, token, payload=None):
    request = Request(
        f"{BASE_URL}{path}", method=method,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        return response.status, json.load(response)


def test_run_control_migration_and_api_contract():
    from dotenv import load_dotenv
    import psycopg2

    load_dotenv()
    migration = (
        Path(__file__).resolve().parents[2] / "dashboard/backend/sql/p2_run_control.sql"
    ).read_text(encoding="utf-8")
    connection = psycopg2.connect(
        host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    connection.autocommit = True
    run_id = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(migration)
            cursor.execute(migration)

        admin = _token("admin", os.environ["DASHBOARD_ADMIN_PASSWORD"])
        analyst = _token("analyst_1", os.environ["DASHBOARD_ANALYST_PASSWORD"])
        create_payload = {
            "source_kind": "BENCHMARK_REPLAY",
            "dataset_id": "ds3_paysim",
            "dataset_version": "test-v1",
            "dataset_hash": "a" * 64,
            "contract_version": 1,
            "evaluator_version": "rules-v1",
            "requested_rate": 50,
            "requested_start_offset": 0,
            "requested_end_offset": 10,
        }

        with pytest.raises(HTTPError) as denied:
            _request("POST", "/runs", analyst, create_payload)
        assert denied.value.code == 403

        code, created = _request("POST", "/runs", admin, create_payload)
        assert code == 201
        run_id = created["run_id"]
        assert created["status"] == "CREATED"
        assert created["version"] == 1

        with pytest.raises(psycopg2.errors.CheckViolation):
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE pipeline_runs SET status = 'PAUSED' WHERE run_id = %s",
                    (run_id,),
                )

        _, listing = _request("GET", "/runs?status=CREATED&dataset_id=ds3_paysim", analyst)
        assert any(item["run_id"] == run_id for item in listing["data"])
        _, detail = _request("GET", f"/runs/{run_id}", analyst)
        assert detail["offsets"] == []
        assert detail["counters"] == []
        assert detail["reconciliation"] == []
        assert detail["quality"]["status"] == "idle"
        assert detail["quality"]["observed_at"]
        assert detail["quality"]["reconciliation_completeness"] == 0
        assert detail["events"][0]["event_type"] == "CREATED"

        _, running = _request("POST", f"/runs/{run_id}/transition", admin, {
            "status": "RUNNING", "version": 1,
        })
        assert running["version"] == 2
        assert running["started_at"] is not None

        with pytest.raises(HTTPError) as stale:
            _request("POST", f"/runs/{run_id}/transition", admin, {
                "status": "PAUSING", "version": 1,
            })
        assert stale.value.code == 409

        version = 2
        for state in ("PAUSING", "PAUSED", "RUNNING", "CANCELLING", "CANCELLED"):
            _, changed = _request("POST", f"/runs/{run_id}/transition", admin, {
                "status": state, "version": version,
            })
            version += 1
            assert changed["status"] == state
            assert changed["version"] == version

        _, final_detail = _request("GET", f"/runs/{run_id}", analyst)
        assert len(final_detail["events"]) == 7
        assert final_detail["events"][-1]["new_status"] == "CANCELLED"

        with pytest.raises(HTTPError) as terminal:
            _request("POST", f"/runs/{run_id}/transition", admin, {
                "status": "RUNNING", "version": version,
            })
        assert terminal.value.code == 422
    finally:
        if run_id:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM pipeline_runs WHERE run_id = %s", (run_id,))
        connection.close()
