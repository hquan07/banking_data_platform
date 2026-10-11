"""Live lifecycle and isolation checks for durable benchmark replay runs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from base64 import b64encode
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_E2E") != "1",
    reason="requires the running Docker Compose stack",
)
ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "http://localhost:8000/api"


def _connection():
    from dotenv import load_dotenv
    import psycopg2

    load_dotenv(ROOT / ".env")
    connection = psycopg2.connect(
        host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    connection.autocommit = True
    return connection


def _token() -> str:
    request = Request(
        f"{BASE_URL}/auth/login",
        data=urlencode({
            "username": "admin",
            "password": os.environ["DASHBOARD_ADMIN_PASSWORD"],
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)["access_token"]


def _transition(token: str, run_id: str, status: str, version: int) -> dict:
    request = Request(
        f"{BASE_URL}/runs/{run_id}/transition", method="POST",
        data=json.dumps({"status": status, "version": version}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def _launch(
    version: str, *, events: int, rate: float,
    run_id: str | None = None, dataset: str = "ds1_creditcard",
):
    environment = os.environ.copy()
    environment.update({"POSTGRES_HOST": "localhost", "POSTGRES_PORT": "5433"})
    command = [
        sys.executable, str(ROOT / "kafka/producers/dataset_replay.py"),
        "--dataset", dataset,
        "--raw-dir", str(ROOT / "datasets/raw"),
        "--bootstrap", "localhost:9094",
        "--dataset-version", version,
        "--max-events", str(events),
        "--rate", str(rate),
        "--control-interval", "1",
        "--max-in-flight", "1",
    ]
    if run_id:
        command.extend(["--run-id", run_id])
    return subprocess.Popen(
        command, cwd=ROOT, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def _one(connection, sql: str, values=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, values)
        return cursor.fetchone()


def _wait_for(callback, *, timeout: float = 30):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = callback()
        if last:
            return last
        time.sleep(0.2)
    raise AssertionError(f"Timed out waiting for live replay state; last={last!r}")


def _run_row(connection, version: str):
    return _one(
        connection,
        "SELECT run_id::text, status, version FROM pipeline_runs "
        "WHERE dataset_version = %s ORDER BY created_at DESC LIMIT 1",
        (version,),
    )


def _finish(process: subprocess.Popen, timeout: float = 40) -> dict:
    output, _ = process.communicate(timeout=timeout)
    assert process.returncode == 0, output
    for line in reversed(output.splitlines()):
        try:
            summary = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(summary, dict) and "run_id" in summary:
            return summary
    raise AssertionError(f"Producer returned no JSON summary: {output}")


def _materialized_counts(connection, run_id: str):
    return _one(
        connection,
        "SELECT "
        "(SELECT count(*) FROM benchmark_events WHERE run_id = %s),"
        "(SELECT count(*) FROM benchmark_evaluations WHERE run_id = %s),"
        "COALESCE((SELECT counter_value FROM pipeline_run_counters "
        "WHERE run_id = %s AND counter_name = 'evaluated'), 0)",
        (run_id, run_id, run_id),
    )


def _publish_duplicate(run_id: str):
    from kafka import KafkaProducer

    connection = _connection()
    try:
        row = _one(
            connection,
            "SELECT event_id, trace_id, dataset_id, source_row_id, event_type, "
            "relative_time_value, relative_time_unit, payload, ground_truth_is_fraud, "
            "source_file, source_kind FROM benchmark_events "
            "WHERE run_id = %s ORDER BY source_row_id::bigint LIMIT 1",
            (run_id,),
        )
    finally:
        connection.close()
    event = {
        "schema_version": 1,
        "run_id": run_id,
        "event_id": row[0],
        "trace_id": row[1],
        "dataset_id": row[2],
        "source_row_id": row[3],
        "event_type": row[4],
        "event_time": {"kind": "relative", "value": row[5], "unit": row[6], "origin": None},
        "payload": row[7],
        "ground_truth": {"is_fraud": row[8]},
        "provenance": {"source_file": row[9], "source_kind": row[10]},
    }
    producer = KafkaProducer(bootstrap_servers="localhost:9094", acks="all")
    try:
        encoded = json.dumps(event, separators=(",", ":")).encode()
        for _ in range(2):
            producer.send(
                "benchmark-events", key=f"{run_id}:{row[0]}".encode(), value=encoded,
            ).get(timeout=10)
    finally:
        producer.close(timeout=10)


def _neo4j_run_scope(run_id: str):
    credentials = b64encode(
        f"{os.environ['NEO4J_USER']}:{os.environ['NEO4J_PASSWORD']}".encode(),
    ).decode()
    request = Request(
        "http://localhost:7474/db/neo4j/tx/commit",
        data=json.dumps({"statements": [{
            "statement": """
                MATCH (origin:BenchmarkAccount)-[event:BENCHMARK_TRANSACTION]->
                      (destination:BenchmarkAccount)
                WHERE event.run_id = $run_id
                RETURN count(event),
                       all(identifier IN collect(origin.id) + collect(destination.id)
                           WHERE identifier STARTS WITH $prefix)
            """,
            "parameters": {"run_id": run_id, "prefix": f"{run_id}:"},
        }]}).encode(),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=10) as response:
        payload = json.load(response)
    assert payload["errors"] == []
    return tuple(payload["results"][0]["data"][0]["row"])


def test_live_replay_pause_cancel_retry_duplicate_and_run_isolation():
    connection = _connection()
    token = _token()
    marker = uuid.uuid4().hex[:10]
    try:
        pause_version = f"e2e-pause-{marker}"
        paused_process = _launch(pause_version, events=8, rate=2)
        run = _wait_for(
            lambda: (row if (row := _run_row(connection, pause_version))
                         and row[1] == "RUNNING" else None),
        )
        run_id = run[0]
        _transition(token, run_id, "PAUSING", run[2])
        paused = _wait_for(
            lambda: (row if (row := _run_row(connection, pause_version))[1] == "PAUSED" else None),
        )
        _transition(token, run_id, "RUNNING", paused[2])
        pause_summary = _finish(paused_process)
        assert pause_summary["published"] == 8
        _wait_for(lambda: _materialized_counts(connection, run_id) == (8, 8, 8))
        assert _run_row(connection, pause_version)[1] == "COMPLETED"

        cancel_version = f"e2e-cancel-{marker}"
        cancelled_process = _launch(cancel_version, events=20, rate=2)
        cancelling = _wait_for(
            lambda: (row if (row := _run_row(connection, cancel_version))
                         and row[1] == "RUNNING" else None),
        )
        _transition(token, cancelling[0], "CANCELLING", cancelling[2])
        cancel_summary = _finish(cancelled_process)
        assert cancel_summary["cancelled"] is True
        assert _run_row(connection, cancel_version)[1] == "CANCELLED"

        retry_version = f"e2e-retry-{marker}"
        interrupted = _launch(retry_version, events=8, rate=2)
        retry_run = _wait_for(
            lambda: (row if (row := _run_row(connection, retry_version))
                         and row[1] == "RUNNING" else None),
        )
        retry_run_id = retry_run[0]
        _wait_for(lambda: (
            (row := _one(
                connection,
                "SELECT counter_value >= 2 FROM pipeline_run_counters "
                "WHERE run_id = %s AND counter_name = 'source_next_row'",
                (retry_run_id,),
            )) and row[0]
        ))
        interrupted.terminate()
        interrupted.wait(timeout=10)
        assert _run_row(connection, retry_version)[1] == "RUNNING"

        resumed = _launch(retry_version, events=8, rate=0, run_id=retry_run_id)
        retry_summary = _finish(resumed)
        assert retry_summary["start_row"] >= 2
        _wait_for(lambda: _materialized_counts(connection, retry_run_id) == (8, 8, 8))
        assert _run_row(connection, retry_version)[1] == "COMPLETED"

        _publish_duplicate(retry_run_id)
        time.sleep(3)
        assert _materialized_counts(connection, retry_run_id) == (8, 8, 8)

        same_event_id = _one(
            connection,
            "SELECT event_id FROM benchmark_events WHERE run_id = %s "
            "ORDER BY source_row_id::bigint LIMIT 1",
            (run_id,),
        )[0]
        assert _one(
            connection,
            "SELECT count(DISTINCT run_id) FROM benchmark_events "
            "WHERE event_id = %s AND run_id IN (%s, %s)",
            (same_event_id, run_id, retry_run_id),
        )[0] == 2
    finally:
        connection.close()


def test_two_paysim_runs_use_separate_graph_namespaces():
    connection = _connection()
    marker = uuid.uuid4().hex[:10]
    try:
        summaries = []
        for suffix in ("a", "b"):
            process = _launch(
                f"e2e-graph-{marker}-{suffix}", events=2, rate=0,
                dataset="ds3_paysim",
            )
            summaries.append(_finish(process))

        first_id, second_id = (summary["run_id"] for summary in summaries)
        assert first_id != second_id
        _wait_for(lambda: _materialized_counts(connection, first_id) == (2, 2, 2))
        _wait_for(lambda: _materialized_counts(connection, second_id) == (2, 2, 2))
        assert _wait_for(lambda: (
            scope if (scope := _neo4j_run_scope(first_id))[0] == 2 else None
        )) == (2, True)
        assert _wait_for(lambda: (
            scope if (scope := _neo4j_run_scope(second_id))[0] == 2 else None
        )) == (2, True)
    finally:
        connection.close()
