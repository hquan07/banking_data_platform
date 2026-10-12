"""Dry-run-first, source-scoped retention planning and execution."""

from __future__ import annotations

import hashlib
import json
import os
from shared.runtime_secrets import get_secret
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


TERMINAL_RUN_STATES = frozenset({"COMPLETED", "CANCELLED", "FAILED"})
OPEN_CASE_STATES = frozenset({"PENDING", "INVESTIGATING"})
SOURCE_PATTERN = re.compile(r"^[a-z0-9_]+$")


def parse_cutoff(value: str, *, now: datetime | None = None) -> datetime:
    """Parse an explicit timezone-aware cutoff and reject current/future time."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("cutoff must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("cutoff must include a timezone")
    cutoff = parsed.astimezone(timezone.utc)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if cutoff >= current:
        raise ValueError("cutoff must be in the past")
    return cutoff


def validate_source(source: str) -> str:
    if not SOURCE_PATTERN.fullmatch(source):
        raise ValueError("source must contain only lowercase letters, numbers and underscores")
    return source


def classify_run_rows(
    rows: Iterable[Mapping[str, Any]], cutoff: datetime,
) -> tuple[list[str], dict[str, list[str]]]:
    """Classify run rows without ever treating the cutoff boundary as expired."""
    candidates: list[str] = []
    protected: dict[str, list[str]] = {}
    for row in rows:
        run_id = str(row["run_id"])
        reason = None
        if row["status"] not in TERMINAL_RUN_STATES:
            reason = "active_or_paused"
        elif row.get("retention_purged_at") is not None:
            reason = "already_purged"
        elif bool(row.get("legal_hold")):
            reason = "legal_hold"
        elif int(row.get("open_case_count") or 0) > 0:
            reason = "open_case"
        else:
            ended_at = row.get("ended_at")
            if ended_at is None or ended_at >= cutoff:
                reason = "not_before_cutoff"
        if reason:
            protected.setdefault(reason, []).append(run_id)
        else:
            candidates.append(run_id)
    return sorted(candidates), {key: sorted(value) for key, value in sorted(protected.items())}


def _json_default(value: Any):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


@dataclass(frozen=True)
class RetentionPlan:
    source: str
    cutoff: datetime
    candidate_run_ids: tuple[str, ...]
    protected_runs: Mapping[str, list[str]]
    stores: Mapping[str, Mapping[str, Any]]

    def canonical(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "cutoff": self.cutoff.astimezone(timezone.utc).isoformat(),
            "candidate_run_ids": list(self.candidate_run_ids),
            "protected_runs": self.protected_runs,
            "stores": self.stores,
        }

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.canonical(), sort_keys=True, separators=(",", ":"), default=_json_default,
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    def summary(self) -> dict[str, Any]:
        payload = self.canonical()
        payload["candidate_fingerprint"] = self.fingerprint
        payload["dry_run_required_for_apply"] = True
        return payload


class _ClickHouseConnectAdapter:
    """Expose the small clickhouse-driver interface used by this module."""

    def __init__(self, client: Any):
        self.client = client

    def execute(self, query: str, parameters: Mapping[str, Any] | None = None):
        if query.lstrip().upper().startswith("SELECT"):
            return self.client.query(query, parameters=parameters).result_rows
        self.client.command(query, parameters=parameters)
        return []

    def disconnect(self) -> None:
        self.client.close()


class _SingleRecordResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def single(self) -> dict[str, Any]:
        if len(self.rows) != 1:
            raise RuntimeError(f"Neo4j query expected one row, received {len(self.rows)}")
        return self.rows[0]


class _Neo4jHttpDriver:
    """Minimal fallback for environments without the Neo4j Python driver."""

    def __init__(self, url: str, user: str, password: str):
        self.url, self.auth = url, (user, password)

    def session(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def run(self, statement: str, **parameters: Any) -> _SingleRecordResult:
        import requests

        response = requests.post(
            self.url, auth=self.auth,
            json={"statements": [{"statement": statement, "parameters": parameters}]},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(payload["errors"][0].get("message", "Neo4j query failed"))
        result = payload["results"][0]
        columns = result["columns"]
        rows = [dict(zip(columns, item["row"])) for item in result["data"]]
        return _SingleRecordResult(rows)

    def close(self) -> None:
        return None


class RetentionRuntime:
    """Runtime adapters plus durable audit for one retention command."""

    def __init__(self, postgres: Any, graph: Any, clickhouse: Any, s3: Any):
        self.postgres = postgres
        self.graph = graph
        self.clickhouse = clickhouse
        self.s3 = s3

    @classmethod
    def from_environment(cls) -> "RetentionRuntime":
        import boto3
        import psycopg2
        from botocore.client import Config as BotoConfig

        postgres = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5433")),
            dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
            password=get_secret("POSTGRES_PASSWORD", required=True), connect_timeout=10,
        )
        postgres.autocommit = True
        try:
            from neo4j import GraphDatabase

            graph = GraphDatabase.driver(
                os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
            )
        except ImportError:
            graph = _Neo4jHttpDriver(
                os.environ.get(
                    "NEO4J_HTTP_URL", "http://localhost:7474/db/neo4j/tx/commit",
                ),
                os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"],
            )
        try:
            from clickhouse_driver import Client

            clickhouse = Client(
                host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
                port=int(os.environ.get("CLICKHOUSE_PORT", "9002")),
                database=os.environ["CLICKHOUSE_DB"], user=os.environ["CLICKHOUSE_USER"],
                password=get_secret("CLICKHOUSE_PASSWORD", required=True), send_receive_timeout=15,
            )
        except ImportError:
            import clickhouse_connect

            http_client = clickhouse_connect.get_client(
                host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
                port=int(os.environ.get("CLICKHOUSE_HTTP_PORT", "8123")),
                database=os.environ["CLICKHOUSE_DB"], username=os.environ["CLICKHOUSE_USER"],
                password=get_secret("CLICKHOUSE_PASSWORD", required=True), connect_timeout=10,
            )
            clickhouse = _ClickHouseConnectAdapter(http_client)
        s3 = boto3.client(
            "s3", endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"),
            aws_access_key_id=os.environ["MINIO_ROOT_USER"],
            aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )
        return cls(postgres, graph, clickhouse, s3)

    def close(self) -> None:
        self.postgres.close()
        self.graph.close()
        self.clickhouse.disconnect()

    def _run_rows(self, source: str) -> list[dict[str, Any]]:
        if source == "live_payment":
            return []
        with self.postgres.cursor() as cursor:
            cursor.execute(
                """
                SELECT run.run_id, run.status,
                       COALESCE(run.completed_at, run.cancelled_at, run.failed_at, run.updated_at) AS ended_at,
                       run.legal_hold, run.retention_purged_at,
                       count(alert.alert_id) FILTER (
                           WHERE alert.status IN ('PENDING', 'INVESTIGATING')
                       ) AS open_case_count
                FROM pipeline_runs run
                LEFT JOIN alerts alert ON alert.run_id = run.run_id
                WHERE run.dataset_id = %s
                GROUP BY run.run_id
                """,
                (source,),
            )
            columns = [item.name for item in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _protected_live_event_ids(self) -> list[str]:
        with self.postgres.cursor() as cursor:
            cursor.execute(
                "SELECT event_id FROM alerts WHERE run_id IS NULL "
                "AND payment_id IS NOT NULL "
                "AND status IN ('PENDING', 'INVESTIGATING') AND event_id IS NOT NULL"
            )
            return sorted({row[0] for row in cursor.fetchall()})

    def _postgres_preview(
        self, source: str, cutoff: datetime, run_ids: list[str], protected_runs: Mapping[str, list[str]],
    ) -> dict[str, Any]:
        with self.postgres.cursor() as cursor:
            if source == "live_payment":
                protected_events = self._protected_live_event_ids()
                cursor.execute(
                    "SELECT count(*) FROM core_banking.payment_event "
                    "WHERE timestamp < %s AND NOT (event_id = ANY(%s::text[]))",
                    (cutoff, protected_events),
                )
                live_rows = cursor.fetchone()[0]
                return {
                    "candidate_count": live_rows,
                    "protected_count": len(protected_events),
                    "details": {
                        "live_payment_events": live_rows,
                        "protected_open_case_event_ids": protected_events,
                    },
                }
            if not run_ids:
                event_count = evaluation_count = 0
            else:
                cursor.execute(
                    "SELECT count(*) FROM benchmark_events WHERE run_id = ANY(%s::uuid[])",
                    (run_ids,),
                )
                event_count = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT count(*) FROM benchmark_evaluations WHERE run_id = ANY(%s::uuid[])",
                    (run_ids,),
                )
                evaluation_count = cursor.fetchone()[0]
        return {
            "candidate_count": event_count + evaluation_count,
            "protected_count": sum(len(value) for value in protected_runs.values()),
            "details": {
                "benchmark_events": event_count,
                "benchmark_evaluations": evaluation_count,
            },
        }

    def _graph_preview(self, source: str, run_ids: list[str]) -> dict[str, Any]:
        if not run_ids:
            return {"candidate_count": 0, "protected_count": 0, "details": {"relationships": 0, "nodes": 0}}
        with self.graph.session() as session:
            relationships = session.run(
                "MATCH ()-[event:BENCHMARK_TRANSACTION]->() "
                "WHERE event.run_id IN $run_ids RETURN count(event) AS count",
                run_ids=run_ids,
            ).single()["count"]
            nodes = session.run(
                "MATCH (node:BenchmarkAccount) WHERE node.run_id IN $run_ids "
                "OR any(run_id IN $run_ids WHERE node.id STARTS WITH run_id + ':') "
                "RETURN count(node) AS count",
                run_ids=run_ids,
            ).single()["count"]
        return {
            "candidate_count": relationships + nodes,
            "protected_count": 0,
            "details": {"relationships": relationships, "nodes": nodes},
        }

    def _source_alerts(self, source: str) -> tuple[dict[int, str], set[str]]:
        with self.postgres.cursor() as cursor:
            if source == "live_payment":
                cursor.execute(
                    "SELECT alert_id, status FROM alerts "
                    "WHERE run_id IS NULL AND dataset_id IS NULL AND payment_id IS NOT NULL"
                )
            else:
                cursor.execute("SELECT alert_id, status FROM alerts WHERE dataset_id = %s", (source,))
            statuses = {int(row[0]): row[1] for row in cursor.fetchall()}
            if not statuses:
                return {}, set()
            cursor.execute(
                "SELECT object_key FROM evidence_files WHERE alert_id = ANY(%s::bigint[])",
                (list(statuses),),
            )
            return statuses, {row[0] for row in cursor.fetchall()}

    def _minio_preview(self, source: str, cutoff: datetime) -> dict[str, Any]:
        statuses, referenced = self._source_alerts(source)
        candidates, protected = [], []
        continuation = None
        while True:
            params = {"Bucket": "evidence", "Prefix": "alerts/"}
            if continuation:
                params["ContinuationToken"] = continuation
            page = self.s3.list_objects_v2(**params)
            for item in page.get("Contents", []):
                parts = item["Key"].split("/", 2)
                if len(parts) < 3 or not parts[1].isdigit():
                    continue
                alert_id = int(parts[1])
                if alert_id not in statuses or item["LastModified"].astimezone(timezone.utc) >= cutoff:
                    continue
                if item["Key"] in referenced or statuses[alert_id] in OPEN_CASE_STATES:
                    protected.append(item["Key"])
                else:
                    candidates.append(item["Key"])
            if not page.get("IsTruncated"):
                break
            continuation = page["NextContinuationToken"]
        return {
            "candidate_count": len(candidates), "protected_count": len(protected),
            "details": {"bucket": "evidence", "candidate_keys": sorted(candidates)},
        }

    def _clickhouse_preview(self, source: str, cutoff: datetime) -> dict[str, Any]:
        if source != "live_payment":
            return {
                "candidate_count": 0, "protected_count": 0,
                "details": {"table": "payment_events", "scope": "not_applicable"},
            }
        protected = self._protected_live_event_ids()
        clause = "event_time < %(cutoff)s"
        params: dict[str, Any] = {"cutoff": cutoff}
        if protected:
            clause += " AND event_id NOT IN %(protected)s"
            params["protected"] = tuple(protected)
        count = self.clickhouse.execute(
            f"SELECT count() FROM payment_events WHERE {clause}", params,
        )[0][0]
        return {
            "candidate_count": count, "protected_count": len(protected),
            "details": {"table": "payment_events", "protected_open_case_event_ids": protected},
        }

    def build_plan(self, source: str, cutoff: datetime) -> RetentionPlan:
        source = validate_source(source)
        rows = self._run_rows(source)
        candidate_ids, protected_runs = classify_run_rows(rows, cutoff)
        stores = {
            "postgres": self._postgres_preview(source, cutoff, candidate_ids, protected_runs),
            "neo4j": self._graph_preview(source, candidate_ids),
            "minio": self._minio_preview(source, cutoff),
            "clickhouse": self._clickhouse_preview(source, cutoff),
            "kafka": {
                "candidate_count": 0, "protected_count": 0,
                "details": {"managed_by": "topic_retention", "destructive_cleanup": False},
            },
            "spark_checkpoints": {
                "candidate_count": 0, "protected_count": 1,
                "details": {"managed_by": "recovery_policy", "automatic_cleanup": False},
            },
        }
        return RetentionPlan(
            source=source, cutoff=cutoff, candidate_run_ids=tuple(candidate_ids),
            protected_runs=protected_runs, stores=stores,
        )

    def _start_execution(
        self, plan: RetentionPlan, mode: str, actor: str, approved_dry_run_id: str | None,
    ) -> str:
        with self.postgres.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO retention_executions
                    (mode, source, cutoff_at, requested_by, approved_dry_run_id,
                     candidate_fingerprint, candidate_run_ids, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s::uuid[], %s::jsonb)
                RETURNING execution_id::text
                """,
                (
                    mode, plan.source, plan.cutoff, actor, approved_dry_run_id,
                    plan.fingerprint, list(plan.candidate_run_ids),
                    json.dumps(plan.summary(), default=_json_default),
                ),
            )
            execution_id = cursor.fetchone()[0]
            for store, item in plan.stores.items():
                cursor.execute(
                    """
                    INSERT INTO retention_execution_items
                        (execution_id, store, candidate_count, protected_count, details)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        execution_id, store, item["candidate_count"],
                        item["protected_count"], json.dumps(item["details"], default=_json_default),
                    ),
                )
        return execution_id

    def _finish_execution(
        self, execution_id: str, status: str, *, summary: Mapping[str, Any], error: str | None = None,
    ) -> None:
        with self.postgres.cursor() as cursor:
            cursor.execute(
                "UPDATE retention_executions SET status = %s, summary = %s::jsonb, "
                "error_message = %s, finished_at = NOW() WHERE execution_id = %s",
                (status, json.dumps(summary, default=_json_default), error, execution_id),
            )

    def _set_deleted(self, execution_id: str, store: str, count: int, details: Mapping[str, Any]) -> None:
        with self.postgres.cursor() as cursor:
            cursor.execute(
                "UPDATE retention_execution_items SET deleted_count = %s, "
                "details = details || %s::jsonb WHERE execution_id = %s AND store = %s",
                (count, json.dumps(details, default=_json_default), execution_id, store),
            )

    def record_dry_run(self, plan: RetentionPlan, actor: str) -> dict[str, Any]:
        execution_id = self._start_execution(plan, "DRY_RUN", actor, None)
        summary = plan.summary() | {"execution_id": execution_id, "mode": "DRY_RUN", "status": "COMPLETED"}
        self._finish_execution(execution_id, "COMPLETED", summary=summary)
        return summary

    def _approved_plan(self, dry_run_id: str) -> tuple[str, str, datetime]:
        with self.postgres.cursor() as cursor:
            cursor.execute(
                "SELECT candidate_fingerprint, source, cutoff_at FROM retention_executions "
                "WHERE execution_id = %s AND mode = 'DRY_RUN' AND status = 'COMPLETED'",
                (dry_run_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise ValueError("approved dry-run does not exist or is not completed")
        return row[0], row[1], row[2]

    def _apply_graph(self, run_ids: list[str]) -> int:
        if not run_ids:
            return 0
        with self.graph.session() as session:
            relationships = session.run(
                "MATCH ()-[event:BENCHMARK_TRANSACTION]->() WHERE event.run_id IN $run_ids "
                "DELETE event RETURN count(*) AS deleted", run_ids=run_ids,
            ).single()["deleted"]
            nodes = session.run(
                "MATCH (node:BenchmarkAccount) WHERE node.run_id IN $run_ids "
                "OR any(run_id IN $run_ids WHERE node.id STARTS WITH run_id + ':') "
                "DETACH DELETE node RETURN count(*) AS deleted", run_ids=run_ids,
            ).single()["deleted"]
        return relationships + nodes

    def _apply_minio(self, keys: list[str]) -> int:
        for key in keys:
            self.s3.delete_object(Bucket="evidence", Key=key)
        return len(keys)

    def _apply_clickhouse(self, plan: RetentionPlan) -> int:
        item = plan.stores["clickhouse"]
        if plan.source != "live_payment" or not item["candidate_count"]:
            return 0
        protected = item["details"]["protected_open_case_event_ids"]
        clause = "event_time < %(cutoff)s"
        params: dict[str, Any] = {"cutoff": plan.cutoff}
        if protected:
            clause += " AND event_id NOT IN %(protected)s"
            params["protected"] = tuple(protected)
        self.clickhouse.execute(
            f"ALTER TABLE payment_events DELETE WHERE {clause} SETTINGS mutations_sync = 2",
            params,
        )
        return int(item["candidate_count"])

    def _apply_postgres(self, plan: RetentionPlan, execution_id: str) -> int:
        run_ids = list(plan.candidate_run_ids)
        with self.postgres.cursor() as cursor:
            if plan.source == "live_payment":
                protected = plan.stores["postgres"]["details"]["protected_open_case_event_ids"]
                cursor.execute(
                    "DELETE FROM core_banking.payment_event WHERE timestamp < %s "
                    "AND NOT (event_id = ANY(%s::text[]))",
                    (plan.cutoff, protected),
                )
                return cursor.rowcount
            if not run_ids:
                return 0
            cursor.execute(
                "DELETE FROM benchmark_evaluations WHERE run_id = ANY(%s::uuid[])",
                (run_ids,),
            )
            evaluations = cursor.rowcount
            cursor.execute(
                "DELETE FROM benchmark_events WHERE run_id = ANY(%s::uuid[])",
                (run_ids,),
            )
            events = cursor.rowcount
            cursor.execute(
                "UPDATE pipeline_runs SET retention_purged_at = NOW(), retention_execution_id = %s "
                "WHERE run_id = ANY(%s::uuid[])",
                (execution_id, run_ids),
            )
            cursor.execute(
                """
                INSERT INTO pipeline_run_events
                    (run_id, event_type, old_status, new_status, details)
                SELECT run_id, 'RETENTION_PURGED', status, status,
                       jsonb_build_object('execution_id', %s::text, 'source', %s, 'cutoff', %s::text)
                FROM pipeline_runs WHERE run_id = ANY(%s::uuid[])
                """,
                (execution_id, plan.source, plan.cutoff.isoformat(), run_ids),
            )
        return evaluations + events

    def apply(self, plan: RetentionPlan, actor: str, approved_dry_run_id: str) -> dict[str, Any]:
        expected, source, cutoff = self._approved_plan(approved_dry_run_id)
        rejection = None
        if source != plan.source or cutoff.astimezone(timezone.utc) != plan.cutoff:
            rejection = "approved dry-run scope does not match source and cutoff"
        elif expected != plan.fingerprint:
            rejection = "retention candidates changed; run a new dry-run before apply"
        if rejection:
            execution_id = self._start_execution(plan, "APPLY", actor, approved_dry_run_id)
            summary = plan.summary() | {
                "execution_id": execution_id, "mode": "APPLY", "status": "REJECTED",
                "approved_dry_run_id": approved_dry_run_id, "rejection_reason": rejection,
            }
            self._finish_execution(execution_id, "REJECTED", summary=summary, error=rejection)
            raise ValueError(f"{rejection}; rejected execution {execution_id}")
        execution_id = self._start_execution(plan, "APPLY", actor, approved_dry_run_id)
        deleted: dict[str, int] = {}
        try:
            deleted["neo4j"] = self._apply_graph(list(plan.candidate_run_ids))
            self._set_deleted(execution_id, "neo4j", deleted["neo4j"], {"applied": True})
            keys = list(plan.stores["minio"]["details"]["candidate_keys"])
            deleted["minio"] = self._apply_minio(keys)
            self._set_deleted(execution_id, "minio", deleted["minio"], {"applied": True})
            deleted["clickhouse"] = self._apply_clickhouse(plan)
            self._set_deleted(execution_id, "clickhouse", deleted["clickhouse"], {"applied": True})
            deleted["postgres"] = self._apply_postgres(plan, execution_id)
            self._set_deleted(execution_id, "postgres", deleted["postgres"], {"applied": True})
            summary = plan.summary() | {
                "execution_id": execution_id, "mode": "APPLY", "status": "COMPLETED",
                "approved_dry_run_id": approved_dry_run_id, "deleted": deleted,
            }
            self._finish_execution(execution_id, "COMPLETED", summary=summary)
            return summary
        except Exception as exc:
            summary = plan.summary() | {
                "execution_id": execution_id, "mode": "APPLY", "status": "FAILED",
                "approved_dry_run_id": approved_dry_run_id, "deleted": deleted,
            }
            self._finish_execution(
                execution_id, "FAILED", summary=summary,
                error=f"{type(exc).__name__}: {str(exc)[:900]}",
            )
            raise
