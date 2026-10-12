"""Live contracts for run-scoped, bounded temporal graph evidence."""

import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_E2E") != "1",
    reason="requires the running Docker Compose stack",
)

BASE_URL = "http://localhost:8000"


def _login_token() -> str:
    from dotenv import load_dotenv

    load_dotenv()
    request = Request(
        f"{BASE_URL}/api/auth/login",
        data=urlencode({
            "username": "admin",
            "password": os.environ["DASHBOARD_ADMIN_PASSWORD"],
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)["access_token"]


def _get(path: str, token: str):
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urlopen(request, timeout=20) as response:
        assert response.status == 200
        return json.load(response)


def _sample_benchmark_edge() -> tuple[str, str]:
    import requests
    from dotenv import load_dotenv

    load_dotenv()
    response = requests.post(
        "http://localhost:7474/db/neo4j/tx/commit",
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
        json={"statements": [{"statement": """
            MATCH ()-[event:BENCHMARK_TRANSACTION]->()
            WHERE event.run_id IS NOT NULL AND event.event_id IS NOT NULL
            RETURN event.run_id, event.event_id
            ORDER BY event.relative_step DESC, event.source_row_number DESC
            LIMIT 1
        """}]},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    assert not payload["errors"], payload["errors"]
    rows = payload["results"][0]["data"]
    assert rows, "A completed DS3 replay is required for graph evidence checks"
    return tuple(rows[0]["row"])


def test_temporal_evidence_is_bounded_run_scoped_and_source_traceable():
    run_id, event_id = _sample_benchmark_edge()
    token = _login_token()

    graph = _get(f"/api/graph/benchmark?run_id={run_id}&limit=10", token)
    assert graph["bounded"] is True
    assert graph["run_ids"] == [run_id]
    assert graph["links"]
    assert all(link["run_id"] == run_id for link in graph["links"])
    assert all(link["source_row_number"] >= 0 for link in graph["links"])
    assert all(link["relative_time_unit"] == "hours" for link in graph["links"])
    assert all(link["source_kind"] == "synthetic_simulation" for link in graph["links"])

    evidence = _get(
        f"/api/graph/evidence?run_id={run_id}&event_id={event_id}"
        "&hop_count=1&limit=10",
        token,
    )
    assert evidence["run_id"] == run_id
    assert evidence["bounded"] is True
    assert evidence["bounds"]["hop_count"] == 1
    assert evidence["anchor"]["event_id"] == event_id
    assert evidence["paths"]
    assert all(path["path_length"] == 1 for path in evidence["paths"])
    assert all(path["evidence_basis"] == "participant_path" for path in evidence["paths"])
    edges = [edge for path in evidence["paths"] for edge in path["edges"]]
    assert event_id in {edge["event_id"] for edge in edges}
    assert all(edge["run_id"] == run_id for edge in edges)
    assert all(edge["source_row_number"] >= 0 for edge in edges)
    assert all(edge["source_kind"] == "synthetic_simulation" for edge in edges)

    request = Request(
        f"{BASE_URL}/api/graph/evidence?run_id={run_id}&event_id={event_id}"
        "&step_from=0&step_to=169",
        headers={"Authorization": f"Bearer {token}"},
    )
    with pytest.raises(HTTPError) as error:
        urlopen(request, timeout=10)
    assert error.value.code == 422
