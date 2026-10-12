"""Live retention boundary, protection, dry-run parity and idempotency checks."""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_E2E") != "1", reason="requires the running Docker Compose stack",
)


def test_retention_requires_matching_dry_run_and_preserves_protected_runs():
    import psycopg2
    import requests
    from dotenv import load_dotenv

    from governance.retention import RetentionRuntime

    load_dotenv()
    suffix = uuid.uuid4().hex[:8]
    source = f"e2e_ret_{suffix}"
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    old = cutoff - timedelta(days=1)
    run_ids = {name: str(uuid.uuid4()) for name in ("eligible", "held", "open", "boundary")}
    execution_ids = []

    connection = psycopg2.connect(
        host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    connection.autocommit = True
    runtime = None

    def cypher(statement, parameters=None):
        response = requests.post(
            "http://localhost:7474/db/neo4j/tx/commit",
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
            json={"statements": [{"statement": statement, "parameters": parameters or {}}]},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        assert not payload["errors"], payload["errors"]
        return [item["row"] for item in payload["results"][0]["data"]]

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE role = 'ADMIN' ORDER BY id LIMIT 1")
            owner_id = cursor.fetchone()[0]
            for name, run_id in run_ids.items():
                ended_at = cutoff if name == "boundary" else old
                cursor.execute(
                    """
                    INSERT INTO pipeline_runs
                        (run_id, status, owner_user_id, source_kind, dataset_id,
                         dataset_version, dataset_hash, contract_version,
                         evaluator_version, requested_rate, created_at, updated_at,
                         started_at, completed_at, legal_hold, legal_hold_reason,
                         legal_hold_at, legal_hold_by)
                    VALUES (%s, 'COMPLETED', %s, 'MANUAL_REPLAY', %s,
                            'retention-e2e', %s, 1, 'retention-e2e', 0,
                            %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run_id, owner_id, source, "a" * 64, ended_at, ended_at,
                        ended_at, ended_at, name == "held",
                        "E2E legal hold" if name == "held" else None,
                        ended_at if name == "held" else None,
                        owner_id if name == "held" else None,
                    ),
                )
                event_id = f"{source}:{name}"
                cursor.execute(
                    """
                    INSERT INTO benchmark_events
                        (run_id, event_id, trace_id, dataset_id, source_row_id,
                         event_type, relative_time_value, relative_time_unit,
                         payload, ground_truth_is_fraud, source_file, source_kind, ingested_at)
                    VALUES (%s, %s, %s, %s, %s, 'payment', 1, 'hours',
                            %s::jsonb, FALSE, 'retention-e2e.csv', 'synthetic', %s)
                    """,
                    (run_id, event_id, f"trace-{name}", source, name, json.dumps({}), ended_at),
                )
                cursor.execute(
                    """
                    INSERT INTO benchmark_evaluations
                        (run_id, event_id, dataset_id, evaluator_version,
                         predicted_fraud, max_score, triggered_rules, evaluated_at)
                    VALUES (%s, %s, %s, 'retention-e2e', FALSE, 0, '[]'::jsonb, %s)
                    """,
                    (run_id, event_id, source, ended_at),
                )
            cursor.execute(
                "INSERT INTO alerts (run_id, event_id, account_id, rule_name, dataset_id, status) "
                "VALUES (%s, %s, 'RETENTION_E2E', 'RETENTION_E2E', %s, 'INVESTIGATING')",
                (run_ids["open"], f"{source}:open", source),
            )

        for name in ("eligible", "held"):
            cypher(
                """
                MERGE (origin:BenchmarkAccount {id: $origin})
                SET origin.run_id = $run_id, origin.display_id = $origin
                MERGE (destination:BenchmarkAccount {id: $destination})
                SET destination.run_id = $run_id, destination.display_id = $destination
                MERGE (origin)-[event:BENCHMARK_TRANSACTION {event_id: $event_id}]->(destination)
                SET event.run_id = $run_id
                RETURN count(event)
                """,
                {
                    "run_id": run_ids[name], "origin": f"{run_ids[name]}:origin",
                    "destination": f"{run_ids[name]}:destination",
                    "event_id": f"{source}:graph:{name}",
                },
            )

        runtime = RetentionRuntime.from_environment()
        plan = runtime.build_plan(source, cutoff)
        assert plan.candidate_run_ids == (run_ids["eligible"],)
        assert plan.protected_runs["legal_hold"] == [run_ids["held"]]
        assert plan.protected_runs["open_case"] == [run_ids["open"]]
        assert plan.protected_runs["not_before_cutoff"] == [run_ids["boundary"]]
        assert plan.stores["postgres"]["candidate_count"] == 2
        assert plan.stores["neo4j"]["candidate_count"] == 3

        dry_run = runtime.record_dry_run(plan, "retention-e2e")
        execution_ids.append(dry_run["execution_id"])

        drift_run_id = str(uuid.uuid4())
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pipeline_runs
                    (run_id, status, owner_user_id, source_kind, dataset_id,
                     dataset_version, dataset_hash, contract_version,
                     evaluator_version, requested_rate, created_at, updated_at,
                     started_at, completed_at)
                VALUES (%s, 'COMPLETED', %s, 'MANUAL_REPLAY', %s,
                        'retention-e2e', %s, 1, 'retention-e2e', 0,
                        %s, %s, %s, %s)
                """,
                (drift_run_id, owner_id, source, "b" * 64, old, old, old, old),
            )
        drifted_plan = runtime.build_plan(source, cutoff)
        with pytest.raises(ValueError, match="candidates changed"):
            runtime.apply(drifted_plan, "retention-e2e", dry_run["execution_id"])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT execution_id::text FROM retention_executions "
                "WHERE approved_dry_run_id = %s AND status = 'REJECTED' "
                "ORDER BY started_at DESC LIMIT 1",
                (dry_run["execution_id"],),
            )
            execution_ids.append(cursor.fetchone()[0])
            cursor.execute("DELETE FROM pipeline_runs WHERE run_id = %s", (drift_run_id,))

        applied = runtime.apply(plan, "retention-e2e", dry_run["execution_id"])
        execution_ids.append(applied["execution_id"])
        assert applied["deleted"]["postgres"] == 2
        assert applied["deleted"]["neo4j"] == 3
        assert cypher(
            "MATCH ()-[event:BENCHMARK_TRANSACTION]->() "
            "WHERE event.run_id = $run_id RETURN count(event)",
            {"run_id": run_ids["eligible"]},
        )[0][0] == 0
        assert cypher(
            "MATCH ()-[event:BENCHMARK_TRANSACTION]->() "
            "WHERE event.run_id = $run_id RETURN count(event)",
            {"run_id": run_ids["held"]},
        )[0][0] == 1

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM benchmark_events WHERE run_id = %s",
                (run_ids["eligible"],),
            )
            assert cursor.fetchone()[0] == 0
            cursor.execute(
                "SELECT count(*) FROM benchmark_events WHERE run_id = ANY(%s::uuid[])",
                ([run_ids["held"], run_ids["open"], run_ids["boundary"]],),
            )
            assert cursor.fetchone()[0] == 3
            cursor.execute(
                "SELECT retention_purged_at IS NOT NULL FROM pipeline_runs WHERE run_id = %s",
                (run_ids["eligible"],),
            )
            assert cursor.fetchone()[0] is True

        second_plan = runtime.build_plan(source, cutoff)
        assert not second_plan.candidate_run_ids
        assert second_plan.protected_runs["already_purged"] == [run_ids["eligible"]]
        second_dry = runtime.record_dry_run(second_plan, "retention-e2e")
        execution_ids.append(second_dry["execution_id"])
        second_apply = runtime.apply(second_plan, "retention-e2e", second_dry["execution_id"])
        execution_ids.append(second_apply["execution_id"])
        assert second_apply["deleted"]["postgres"] == 0
    finally:
        if runtime is not None:
            runtime.close()
        cypher(
            "MATCH (node:BenchmarkAccount) WHERE node.run_id IN $run_ids DETACH DELETE node",
            {"run_ids": list(run_ids.values())},
        )
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM alerts WHERE dataset_id = %s", (source,))
            cursor.execute(
                "UPDATE pipeline_runs SET retention_execution_id = NULL WHERE run_id = ANY(%s::uuid[])",
                (list(run_ids.values()),),
            )
            cursor.execute("DELETE FROM pipeline_runs WHERE run_id = ANY(%s::uuid[])", (list(run_ids.values()),))
            if execution_ids:
                cursor.execute(
                    "DELETE FROM retention_execution_items WHERE execution_id = ANY(%s::uuid[])",
                    (execution_ids,),
                )
                cursor.execute(
                    "DELETE FROM retention_executions WHERE execution_id = ANY(%s::uuid[]) "
                    "AND mode = 'APPLY'",
                    (execution_ids,),
                )
                cursor.execute(
                    "DELETE FROM retention_executions WHERE execution_id = ANY(%s::uuid[])",
                    (execution_ids,),
                )
        connection.close()
