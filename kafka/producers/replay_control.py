"""PostgreSQL-backed lifecycle and progress tracking for dataset replay."""

from __future__ import annotations

import json
import os
import time
import uuid
from collections import defaultdict
from typing import Any, Iterable


class ReplayCancelled(RuntimeError):
    pass


class ReplayRunControl:
    def __init__(
        self,
        connection: Any,
        run_id: str,
        owner_user_id: int,
        requested_start_offset: int,
        requested_end_offset: int | None,
    ) -> None:
        self.connection = connection
        self.run_id = run_id
        self.owner_user_id = owner_user_id
        self.requested_start_offset = requested_start_offset
        self.requested_end_offset = requested_end_offset

    @classmethod
    def connect(cls, run_id: str | None, metadata: dict[str, Any]) -> "ReplayRunControl":
        import psycopg2

        connection = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "banking_postgres"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            connect_timeout=10,
        )
        connection.autocommit = False
        try:
            controller = cls._open(connection, run_id, metadata)
            controller.ensure_running()
            return controller
        except BaseException:
            connection.close()
            raise

    @classmethod
    def _open(
        cls, connection: Any, run_id: str | None, metadata: dict[str, Any],
    ) -> "ReplayRunControl":
        owner_username = os.environ.get("RUN_OWNER_USERNAME", "admin")
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s AND role = 'ADMIN'",
                    (owner_username,),
                )
                owner = cursor.fetchone()
                if owner is None:
                    raise ValueError(f"ADMIN run owner not found: {owner_username}")
                owner_user_id = owner[0]
                if run_id is None:
                    run_id = str(uuid.uuid4())
                    cursor.execute(
                        """
                        INSERT INTO pipeline_runs
                            (run_id, owner_user_id, source_kind, dataset_id,
                             dataset_version, dataset_hash, contract_version,
                             evaluator_version, requested_rate,
                             requested_start_offset, requested_end_offset)
                        VALUES (%s, %s, 'BENCHMARK_REPLAY', %s, %s, %s, 1, %s, %s, %s, %s)
                        """,
                        (
                            run_id, owner_user_id, metadata["dataset_id"],
                            metadata["dataset_version"], metadata["dataset_hash"],
                            metadata["evaluator_version"], metadata["requested_rate"],
                            metadata["requested_start_offset"], metadata.get("requested_end_offset"),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO pipeline_run_events
                            (run_id, event_type, old_status, new_status, actor_user_id, details)
                        VALUES (%s, 'CREATED', NULL, 'CREATED', %s, %s::jsonb)
                        """,
                        (run_id, owner_user_id, json.dumps({"created_by": "dataset_replay"})),
                    )
                    requested_start_offset = metadata["requested_start_offset"]
                    requested_end_offset = metadata.get("requested_end_offset")
                else:
                    try:
                        run_id = str(uuid.UUID(run_id))
                    except ValueError:
                        raise ValueError("run_id must be a UUID") from None
                    cursor.execute(
                        """
                        SELECT owner_user_id, dataset_id, dataset_version, dataset_hash,
                               contract_version, evaluator_version,
                               requested_start_offset, requested_end_offset
                        FROM pipeline_runs WHERE run_id = %s FOR UPDATE
                        """,
                        (run_id,),
                    )
                    existing = cursor.fetchone()
                    if existing is None:
                        raise ValueError(f"Pipeline run not found: {run_id}")
                    (
                        owner_user_id, dataset_id, dataset_version, dataset_hash,
                        contract_version, evaluator_version,
                        requested_start_offset, requested_end_offset,
                    ) = existing
                    if (
                        dataset_id != metadata["dataset_id"]
                        or dataset_version != metadata["dataset_version"]
                        or dataset_hash != metadata["dataset_hash"]
                        or contract_version != 1
                        or evaluator_version != metadata["evaluator_version"]
                    ):
                        raise ValueError("Existing run metadata does not match the replay source")
        return cls(
            connection, run_id, owner_user_id,
            requested_start_offset or 0, requested_end_offset,
        )

    def close(self) -> None:
        self.connection.close()

    def _status(self, *, lock: bool = False) -> tuple[str, int]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT status, version FROM pipeline_runs WHERE run_id = %s" + (" FOR UPDATE" if lock else ""),
                (self.run_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Pipeline run not found: {self.run_id}")
        return row[0], row[1]

    def _transition(self, old_status: str, new_status: str) -> None:
        timestamp_sql = {
            "RUNNING": "started_at = COALESCE(started_at, NOW())",
            "PAUSED": "paused_at = NOW()",
            "CANCELLED": "cancelled_at = NOW()",
            "COMPLETED": "completed_at = NOW()",
        }.get(new_status)
        assignments = ["status = %s", "version = version + 1", "updated_at = NOW()"]
        if timestamp_sql:
            assignments.append(timestamp_sql)
        with self.connection:
            with self.connection.cursor() as cursor:
                current, version = self._status(lock=True)
                if current != old_status:
                    return
                cursor.execute(
                    f"UPDATE pipeline_runs SET {', '.join(assignments)} "
                    "WHERE run_id = %s AND version = %s RETURNING version",
                    (new_status, self.run_id, version),
                )
                if cursor.fetchone() is None:
                    raise RuntimeError("Pipeline run changed while applying producer transition")
                cursor.execute(
                    """
                    INSERT INTO pipeline_run_events
                        (run_id, event_type, old_status, new_status, actor_user_id, details)
                    VALUES (%s, 'STATE_TRANSITION', %s, %s, %s, %s::jsonb)
                    """,
                    (
                        self.run_id, old_status, new_status, self.owner_user_id,
                        json.dumps({"actor": "dataset_replay"}),
                    ),
                )

    def ensure_running(self) -> None:
        status, _ = self._status()
        if status in {"CREATED", "PAUSED"}:
            self._transition(status, "RUNNING")
        elif status != "RUNNING":
            raise ValueError(f"Pipeline run is not resumable from {status}")

    def await_runnable(self, poll_seconds: float = 1.0) -> None:
        """Acknowledge pause/cancel requests and wait for an operator resume."""
        while True:
            status, _ = self._status()
            if status == "RUNNING":
                return
            if status == "PAUSING":
                self._transition("PAUSING", "PAUSED")
                continue
            if status == "PAUSED":
                time.sleep(poll_seconds)
                continue
            if status == "CANCELLING":
                self._transition("CANCELLING", "CANCELLED")
                raise ReplayCancelled(self.run_id)
            if status == "CANCELLED":
                raise ReplayCancelled(self.run_id)
            raise RuntimeError(f"Pipeline run stopped in state {status}")

    def resume_row(self, requested_start: int) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT counter_value FROM pipeline_run_counters "
                "WHERE run_id = %s AND counter_name = 'source_next_row'",
                (self.run_id,),
            )
            row = cursor.fetchone()
        return max(requested_start, row[0] if row else requested_start)

    def record_progress(self, acknowledgements: Iterable[dict[str, Any]]) -> None:
        items = list(acknowledgements)
        if not items:
            return
        offsets: dict[tuple[str, int], list[int]] = defaultdict(list)
        counts: dict[str, int] = defaultdict(int)
        next_row = 0
        for item in items:
            offsets[(item["topic"], item["partition"])].append(item["offset"])
            counts[item["outcome"]] += 1
            counts["scanned"] += 1
            next_row = max(next_row, item["source_row"] + 1)
        with self.connection:
            with self.connection.cursor() as cursor:
                for (topic, partition), values in offsets.items():
                    start, end = min(values), max(values) + 1
                    cursor.execute(
                        """
                        INSERT INTO pipeline_run_offsets
                            (run_id, topic, partition, start_offset, end_offset, current_offset)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (run_id, topic, partition) DO UPDATE SET
                            start_offset = LEAST(pipeline_run_offsets.start_offset, EXCLUDED.start_offset),
                            end_offset = GREATEST(pipeline_run_offsets.end_offset, EXCLUDED.end_offset),
                            current_offset = GREATEST(pipeline_run_offsets.current_offset, EXCLUDED.current_offset),
                            updated_at = NOW()
                        """,
                        (self.run_id, topic, partition, start, end, end),
                    )
                for counter_name, delta in counts.items():
                    cursor.execute(
                        """
                        INSERT INTO pipeline_run_counters (run_id, counter_name, counter_value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (run_id, counter_name) DO UPDATE SET
                            counter_value = pipeline_run_counters.counter_value + EXCLUDED.counter_value,
                            updated_at = NOW()
                        """,
                        (self.run_id, counter_name, delta),
                    )
                cursor.execute(
                    """
                    INSERT INTO pipeline_run_counters (run_id, counter_name, counter_value)
                    VALUES (%s, 'source_next_row', %s)
                    ON CONFLICT (run_id, counter_name) DO UPDATE SET
                        counter_value = GREATEST(pipeline_run_counters.counter_value, EXCLUDED.counter_value),
                        updated_at = NOW()
                    """,
                    (self.run_id, next_row),
                )

    def complete(self) -> None:
        status, _ = self._status()
        if status == "RUNNING":
            self._transition("RUNNING", "COMPLETED")
