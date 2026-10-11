"""Live PostgreSQL/ClickHouse reconciliation persistence checks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest

from shared.reconciliation.payment import payment_store_outcome, snapshot_window_key
from shared.reconciliation.persistence import persist_outcome
from shared.reconciliation.run import reconcile_benchmark_run


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_E2E") != "1", reason="requires live Compose stack",
)
ROOT = Path(__file__).resolve().parents[2]


def test_reconciliation_migration_and_cross_store_exact_match():
    from dotenv import load_dotenv
    import psycopg2

    load_dotenv(ROOT / ".env")
    connection = psycopg2.connect(
        host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    connection.autocommit = True
    migration = (ROOT / "dashboard/backend/sql/p2_reconciliation.sql").read_text()
    run_id = str(uuid.uuid4())
    try:
        with connection.cursor() as cursor:
            cursor.execute(migration)
            cursor.execute(migration)
            cursor.execute(
                "SELECT payment_id, event_id FROM core_banking.payment_event "
                "ORDER BY timestamp DESC NULLS LAST LIMIT 100"
            )
            candidates = cursor.fetchall()
            cursor.execute(
                "SELECT id FROM users WHERE role = 'ADMIN' ORDER BY id LIMIT 1"
            )
            owner_id = cursor.fetchone()[0]
        assert candidates, "live PostgreSQL has no payment events"

        credentials = b64encode(
            f"{os.environ['CLICKHOUSE_USER']}:{os.environ['CLICKHOUSE_PASSWORD']}".encode(),
        ).decode()
        request = Request(
            f"http://localhost:8123/?database={quote(os.environ['CLICKHOUSE_DB'])}",
            data=(
                "SELECT payment_id, event_id FROM payment_events FINAL LIMIT 1000 "
                "FORMAT JSONEachRow"
            ).encode(),
            headers={"Authorization": f"Basic {credentials}"},
        )
        with urlopen(request, timeout=10) as response:
            clickhouse_rows = []
            for line in response:
                if line.strip():
                    row = json.loads(line)
                    clickhouse_rows.append((row["payment_id"], row["event_id"]))
        postgres_rows = candidates
        postgres = dict(postgres_rows)
        clickhouse = dict(clickhouse_rows)
        payment_id = next(
            identity for identity, event_id in postgres.items()
            if clickhouse.get(identity) == event_id
        )
        event_id = postgres[payment_id]

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pipeline_runs
                    (run_id, status, owner_user_id, source_kind, dataset_id,
                     dataset_version, dataset_hash, contract_version,
                     evaluator_version, requested_rate, started_at, completed_at)
                VALUES (%s, 'COMPLETED', %s, 'LIVE_INGESTION', 'payment_events',
                        %s, %s, 1, 'fraud-engine-v1', 0, NOW(), NOW())
                """,
                (run_id, owner_id, f"reconciliation-e2e-{run_id[:8]}", "f" * 64),
            )

        events = [{
            "payment_id": payment_id,
            "event_id": event_id,
            "_source": {"topic": "payment-events", "partition": 0, "offset": 0},
        }]
        observed_at = datetime.now(timezone.utc)
        window_key = snapshot_window_key(events)
        for store, rows in (
            ("POSTGRESQL", postgres_rows), ("CLICKHOUSE", clickhouse_rows),
        ):
            selected = [row for row in rows if row[0] == payment_id]
            outcome = payment_store_outcome(
                events, selected, observed_at=observed_at, due_at=observed_at,
            )
            for _ in range(2):
                persist_outcome(
                    connection, run_id=run_id, store=store,
                    metric="payment_event_identity", window_key=window_key,
                    freshness_sla_seconds=0, outcome=outcome,
                )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pipeline_reconciliation_checks WHERE run_id = %s",
                (run_id,),
            )
            assert cursor.fetchone()[0] == 2
            cursor.execute(
                "SELECT store, classification, expected_count, actual_count "
                "FROM pipeline_reconciliation_results WHERE run_id = %s ORDER BY store",
                (run_id,),
            )
            assert cursor.fetchall() == [
                ("CLICKHOUSE", "EXACT", 1, 1),
                ("POSTGRESQL", "EXACT", 1, 1),
            ]
    finally:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM pipeline_runs WHERE run_id = %s", (run_id,))
        connection.close()


def test_completed_benchmark_run_reconciles_kafka_and_postgres_materializations():
    from dotenv import load_dotenv
    import psycopg2

    load_dotenv(ROOT / ".env")
    environment = os.environ.copy()
    environment.update({"POSTGRES_HOST": "localhost", "POSTGRES_PORT": "5433"})
    result = subprocess.run(
        [
            sys.executable, str(ROOT / "kafka/producers/dataset_replay.py"),
            "--dataset", "ds1_creditcard", "--raw-dir", str(ROOT / "datasets/raw"),
            "--bootstrap", "localhost:9094", "--dataset-version",
            f"reconciliation-e2e-{uuid.uuid4().hex[:10]}",
            "--max-events", "3", "--rate", "0", "--control-interval", "1",
        ],
        cwd=ROOT, env=environment, check=True, capture_output=True, text=True,
    )
    summary = json.loads(result.stdout.splitlines()[-1])
    run_id = summary["run_id"]
    connection = psycopg2.connect(
        host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    try:
        deadline = datetime.now(timezone.utc).timestamp() + 20
        while True:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM benchmark_evaluations WHERE run_id = %s",
                    (run_id,),
                )
                if cursor.fetchone()[0] == 3:
                    break
            if datetime.now(timezone.utc).timestamp() >= deadline:
                pytest.fail("benchmark evaluations did not materialize")
            import time
            time.sleep(0.2)

        checks = reconcile_benchmark_run(
            connection, run_id, freshness_sla_seconds=0,
            kafka_bootstrap="localhost:9094",
        )
        assert set(checks) == {
            "KAFKA:accepted_events", "POSTGRESQL:benchmark_events",
            "EVALUATIONS:benchmark_evaluations", "ALERTS:rule_alerts",
            "DLQ:quarantined_events",
        }
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pipeline_reconciliation_results "
                "WHERE run_id = %s AND classification = 'EXACT'",
                (run_id,),
            )
            assert cursor.fetchone()[0] == 5
    finally:
        connection.close()
