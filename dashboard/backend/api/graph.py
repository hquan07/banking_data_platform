"""Neo4j graph network and bounded temporal evidence APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from core.db import graph_driver
from core.deps import get_current_user
from services.graph_analytics import fraud_sequence_payload
from services.graph_evidence import (
    path_evidence_payload,
    temporal_path_query,
    validate_temporal_bounds,
)


router = APIRouter(prefix="/api/graph", tags=["Graph"], dependencies=[Depends(get_current_user)])


def _driver_required():
    if graph_driver is None:
        raise HTTPException(status_code=503, detail="Graph database unavailable")


def _validated_bounds(step_from: float | None, step_to: float | None):
    try:
        return validate_temporal_bounds(step_from, step_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/circular")
def get_circular_graph():
    _driver_required()
    query = """
    MATCH (a:Account)-[r1:TRANSFERRED_TO]->(b:Account)-[r2:TRANSFERRED_TO]->
          (c:Account)-[r3:TRANSFERRED_TO]->(a)
    RETURN a.id AS acc_a, b.id AS acc_b, c.id AS acc_c,
           r1.amount AS amt1, r2.amount AS amt2, r3.amount AS amt3
    LIMIT 50
    """
    try:
        with graph_driver.session() as session:
            records = list(session.run(query))
        nodes = set()
        links = []
        for record in records:
            nodes.update((record["acc_a"], record["acc_b"], record["acc_c"]))
            links.extend((
                {"source": record["acc_a"], "target": record["acc_b"], "value": record["amt1"]},
                {"source": record["acc_b"], "target": record["acc_c"], "value": record["amt2"]},
                {"source": record["acc_c"], "target": record["acc_a"], "value": record["amt3"]},
            ))
        return {"nodes": [{"id": node, "name": node, "group": 1} for node in nodes], "links": links}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Graph database unavailable") from exc


@router.get("/benchmark")
def get_benchmark_graph(
    run_id: UUID | None = None,
    account_id: str | None = Query(None, min_length=1, max_length=160),
    step_from: float | None = Query(None, ge=0),
    step_to: float | None = Query(None, ge=0),
    min_risk_score: float = Query(0, ge=0, le=100),
    limit: int = Query(500, ge=1, le=500),
):
    _driver_required()
    step_from, step_to = _validated_bounds(step_from, step_to)
    query = """
    MATCH (source:BenchmarkAccount)-[event:BENCHMARK_TRANSACTION]->(target:BenchmarkAccount)
    WHERE ($run_id IS NULL OR event.run_id = $run_id)
      AND ($account_id IS NULL OR source.id = $account_id OR target.id = $account_id
           OR source.display_id = $account_id OR target.display_id = $account_id)
      AND coalesce(event.risk_score, 0) >= $min_risk_score
      AND ($step_from IS NULL OR event.relative_step >= $step_from)
      AND ($step_to IS NULL OR event.relative_step <= $step_to)
    RETURN source.id AS source_id, source.display_id AS source_display_id,
           target.id AS target_id, target.display_id AS target_display_id,
           event.event_id AS event_id, event.run_id AS run_id,
           event.amount AS amount, event.transaction_type AS transaction_type,
           event.relative_step AS relative_step,
           coalesce(event.relative_time_unit, 'hours') AS relative_time_unit,
           event.source_row_number AS source_row_number,
           event.source_file AS source_file,
           coalesce(event.source_kind, 'synthetic_simulation') AS source_kind,
           coalesce(event.risk_score, 0) AS risk_score,
           coalesce(event.triggered_rules, []) AS triggered_rules,
           coalesce(event.evaluator_version, 'unknown') AS evaluator_version
    ORDER BY event.relative_step DESC, event.source_row_number DESC
    LIMIT $limit
    """
    try:
        with graph_driver.session() as session:
            records = list(session.run(
                query, run_id=str(run_id) if run_id else None, account_id=account_id,
                step_from=step_from, step_to=step_to, min_risk_score=min_risk_score,
                limit=limit,
            ))
        nodes = {}
        links = []
        run_ids = set()
        for record in records:
            nodes[record["source_id"]] = {
                "id": record["source_id"], "name": record["source_display_id"], "group": 1,
            }
            nodes[record["target_id"]] = {
                "id": record["target_id"], "name": record["target_display_id"], "group": 1,
            }
            if record["run_id"]:
                run_ids.add(record["run_id"])
            links.append({
                "source": record["source_id"], "target": record["target_id"],
                "event_id": record["event_id"], "run_id": record["run_id"],
                "value": float(record["amount"]),
                "transaction_type": record["transaction_type"],
                "relative_step": float(record["relative_step"]),
                "relative_time_unit": record["relative_time_unit"],
                "source_row_number": int(record["source_row_number"]),
                "source_file": record["source_file"], "source_kind": record["source_kind"],
                "risk_score": float(record["risk_score"]),
                "triggered_rules": list(record["triggered_rules"]),
                "evaluator_version": record["evaluator_version"],
            })
        return {
            "dataset_id": "ds3_paysim", "provenance": "synthetic_simulation",
            "run_ids": sorted(run_ids), "bounded": True,
            "filters": {
                "run_id": str(run_id) if run_id else None, "account_id": account_id,
                "step_from": step_from, "step_to": step_to,
                "min_risk_score": min_risk_score, "limit": limit,
            },
            "nodes": list(nodes.values()), "links": links,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Benchmark graph unavailable") from exc


@router.get("/evidence")
def get_temporal_graph_evidence(
    run_id: UUID,
    account_id: str | None = Query(None, min_length=1, max_length=160),
    event_id: str | None = Query(None, min_length=1, max_length=120),
    step_from: float | None = Query(None, ge=0),
    step_to: float | None = Query(None, ge=0),
    hop_count: int = Query(2, ge=1, le=3),
    min_risk_score: float = Query(0, ge=0, le=100),
    limit: int = Query(40, ge=1, le=100),
):
    _driver_required()
    if not account_id and not event_id:
        raise HTTPException(status_code=422, detail="account_id or event_id is required")
    step_from, step_to = _validated_bounds(step_from, step_to)
    query = temporal_path_query(hop_count, anchor_by_event=bool(event_id))
    parameters = {
        "run_id": str(run_id), "run_prefix": f"{run_id}:",
        "account_id": account_id, "event_id": event_id,
        "step_from": step_from, "step_to": step_to,
        "min_risk_score": min_risk_score, "limit": limit,
    }
    try:
        with graph_driver.session() as session:
            records = list(session.run(query, **parameters))
        return {
            "dataset_id": "ds3_paysim", "run_id": str(run_id),
            "provenance": "synthetic_simulation", "bounded": True,
            "anchor": {"account_id": account_id, "event_id": event_id},
            "bounds": {
                "step_from": step_from, "step_to": step_to,
                "hop_count": hop_count, "min_risk_score": min_risk_score,
                "limit": limit,
            },
            "paths": path_evidence_payload(records),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Temporal graph evidence unavailable") from exc


@router.get("/money-flow")
def get_benchmark_money_flow(run_id: UUID | None = None):
    _driver_required()
    query = """
    MATCH ()-[event:BENCHMARK_TRANSACTION]->()
    WHERE $run_id IS NULL OR event.run_id = $run_id
    RETURN event.transaction_type AS transaction_type,
           count(*) AS count, sum(event.amount) AS total_amount
    ORDER BY total_amount DESC
    """
    try:
        with graph_driver.session() as session:
            records = list(session.run(query, run_id=str(run_id) if run_id else None))
        return [{
            "transaction_type": row["transaction_type"], "count": row["count"],
            "total_amount": row["total_amount"],
        } for row in records]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Benchmark money flow unavailable") from exc


@router.get("/fraud-sequences")
def get_benchmark_fraud_sequences(
    run_id: UUID | None = None,
    step_from: float | None = Query(None, ge=0),
    step_to: float | None = Query(None, ge=0),
    min_risk_score: float = Query(0, ge=0, le=100),
    limit: int = Query(100, ge=1, le=200),
):
    _driver_required()
    step_from, step_to = _validated_bounds(step_from, step_to)
    query = """
    MATCH (transfer_origin:BenchmarkAccount)-[transfer:BENCHMARK_TRANSACTION]->
          (transfer_destination:BenchmarkAccount)
    MATCH (cashout_origin:BenchmarkAccount)-[cashout:BENCHMARK_TRANSACTION]->
          (cashout_destination:BenchmarkAccount)
    WHERE transfer.transaction_type = 'TRANSFER'
      AND cashout.transaction_type = 'CASH_OUT'
      AND cashout.run_id = transfer.run_id
      AND ($run_id IS NULL OR transfer.run_id = $run_id)
      AND cashout.source_row_number = transfer.source_row_number + 1
      AND cashout.relative_step = transfer.relative_step
      AND abs(cashout.amount - transfer.amount) <= 0.01
      AND CASE WHEN coalesce(transfer.risk_score, 0) > coalesce(cashout.risk_score, 0)
               THEN coalesce(transfer.risk_score, 0) ELSE coalesce(cashout.risk_score, 0) END
          >= $min_risk_score
      AND ($step_from IS NULL OR transfer.relative_step >= $step_from)
      AND ($step_to IS NULL OR transfer.relative_step <= $step_to)
    RETURN transfer.run_id AS run_id,
           transfer_origin.display_id AS transfer_origin,
           transfer_destination.display_id AS transfer_destination,
           cashout_origin.display_id AS cashout_origin,
           cashout_destination.display_id AS cashout_destination,
           transfer.event_id AS transfer_event_id,
           cashout.event_id AS cashout_event_id,
           transfer.source_row_number AS transfer_source_row,
           cashout.source_row_number AS cashout_source_row,
           transfer.amount AS transfer_amount,
           cashout.amount AS cashout_amount,
           transfer.relative_step AS transfer_step,
           cashout.relative_step AS cashout_step,
           coalesce(transfer.relative_time_unit, 'hours') AS relative_time_unit,
           transfer.source_file AS source_file,
           coalesce(transfer.source_kind, 'synthetic_simulation') AS source_kind,
           coalesce(transfer.risk_score, 0) AS transfer_risk_score,
           coalesce(cashout.risk_score, 0) AS cashout_risk_score,
           transfer.ground_truth_is_fraud AS ground_truth_fraud
    ORDER BY cashout.relative_step DESC
    LIMIT $limit
    """
    try:
        with graph_driver.session() as session:
            records = list(session.run(
                query, run_id=str(run_id) if run_id else None,
                step_from=step_from, step_to=step_to,
                min_risk_score=min_risk_score, limit=limit,
            ))
        return {
            "dataset_id": "ds3_paysim", "provenance": "synthetic_simulation",
            "evidence_basis": "source_row_adjacency",
            "match_basis": "adjacent_source_rows_same_step_and_amount",
            "bounded": True,
            "sequences": fraud_sequence_payload(records),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Benchmark fraud sequences unavailable") from exc
