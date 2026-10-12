"""Bounded temporal graph queries and path-level evidence formatting."""

from __future__ import annotations

from typing import Any, Iterable


MAX_STEP_WINDOW = 168.0


def validate_temporal_bounds(
    step_from: float | None,
    step_to: float | None,
) -> tuple[float | None, float | None]:
    if (step_from is None) != (step_to is None):
        raise ValueError("step_from and step_to must be provided together")
    if step_from is not None:
        if step_from < 0 or step_to < step_from:
            raise ValueError("invalid relative-step window")
        if step_to - step_from > MAX_STEP_WINDOW:
            raise ValueError(f"relative-step window cannot exceed {int(MAX_STEP_WINDOW)} hours")
    return step_from, step_to


def temporal_path_query(hop_count: int, *, anchor_by_event: bool) -> str:
    """Return a Cypher query with only the validated hop count interpolated."""
    if not 1 <= hop_count <= 3:
        raise ValueError("hop_count must be between 1 and 3")
    if anchor_by_event:
        anchor = """
        MATCH (anchor_source:BenchmarkAccount)-[anchor:BENCHMARK_TRANSACTION]->
              (anchor_target:BenchmarkAccount)
        WHERE anchor.run_id = $run_id AND anchor.event_id = $event_id
        WITH [anchor_source, anchor_target] AS seeds
        UNWIND seeds AS seed
        """
    else:
        anchor = """
        MATCH (seed:BenchmarkAccount)
        WHERE (seed.run_id = $run_id OR seed.id STARTS WITH $run_prefix)
          AND (seed.id = $account_id OR seed.display_id = $account_id)
        """
    return anchor + f"""
        MATCH path=(seed)-[:BENCHMARK_TRANSACTION*1..{hop_count}]-(neighbor:BenchmarkAccount)
        WHERE ALL(edge IN relationships(path) WHERE
            edge.run_id = $run_id
            AND coalesce(edge.risk_score, 0) >= $min_risk_score
            AND ($step_from IS NULL OR edge.relative_step >= $step_from)
            AND ($step_to IS NULL OR edge.relative_step <= $step_to)
        )
        WITH path
        ORDER BY length(path),
                 reduce(latest = 0.0, edge IN relationships(path) |
                    CASE WHEN edge.relative_step > latest THEN edge.relative_step ELSE latest END) DESC
        LIMIT $limit
        UNWIND range(0, size(relationships(path)) - 1) AS hop_index
        WITH path, hop_index, relationships(path)[hop_index] AS event
        RETURN [edge IN relationships(path) | edge.event_id] AS path_event_ids,
               length(path) AS path_length,
               hop_index,
               startNode(event).id AS source_id,
               startNode(event).display_id AS source_display_id,
               endNode(event).id AS target_id,
               endNode(event).display_id AS target_display_id,
               event.event_id AS event_id,
               event.trace_id AS trace_id,
               event.run_id AS run_id,
               coalesce(event.dataset_id, 'ds3_paysim') AS dataset_id,
               event.transaction_type AS transaction_type,
               event.amount AS amount,
               event.relative_step AS relative_step,
               coalesce(event.relative_time_unit, 'hours') AS relative_time_unit,
               event.source_row_number AS source_row_number,
               event.source_file AS source_file,
               coalesce(event.source_kind, 'synthetic_simulation') AS source_kind,
               coalesce(event.risk_score, 0) AS risk_score,
               coalesce(event.triggered_rules, []) AS triggered_rules,
               coalesce(event.evaluator_version, 'unknown') AS evaluator_version,
               toString(event.processed_at) AS processed_at
        ORDER BY path_event_ids, hop_index
    """


def path_evidence_payload(records: Iterable[Any]) -> list[dict[str, Any]]:
    paths: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in records:
        ordered_key = tuple(row["path_event_ids"])
        reversed_key = tuple(reversed(ordered_key))
        key = min(ordered_key, reversed_key)
        path = paths.setdefault(key, {
            "path_id": ":".join(key),
            "evidence_basis": "participant_path",
            "participant_linked": True,
            "path_length": int(row["path_length"]),
            "nodes": {},
            "edges": [],
            "_edge_ids": set(),
        })
        path["nodes"][row["source_id"]] = {
            "id": row["source_id"], "display_id": row["source_display_id"],
        }
        path["nodes"][row["target_id"]] = {
            "id": row["target_id"], "display_id": row["target_display_id"],
        }
        if row["event_id"] in path["_edge_ids"]:
            continue
        path["_edge_ids"].add(row["event_id"])
        path["edges"].append({
            "hop_index": int(row["hop_index"]),
            "source": row["source_id"], "target": row["target_id"],
            "event_id": row["event_id"], "trace_id": row["trace_id"],
            "run_id": row["run_id"], "dataset_id": row["dataset_id"],
            "transaction_type": row["transaction_type"],
            "amount": float(row["amount"]),
            "relative_step": float(row["relative_step"]),
            "relative_time_unit": row["relative_time_unit"],
            "source_row_number": int(row["source_row_number"]),
            "source_file": row["source_file"], "source_kind": row["source_kind"],
            "risk_score": float(row["risk_score"]),
            "triggered_rules": list(row["triggered_rules"]),
            "evaluator_version": row["evaluator_version"],
            "processed_at": row["processed_at"],
        })
    response = []
    for path in paths.values():
        path.pop("_edge_ids")
        path["nodes"] = list(path["nodes"].values())
        path["edges"].sort(key=lambda edge: edge["hop_index"])
        response.append(path)
    return response
