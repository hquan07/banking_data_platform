"""
Neo4j graph network router.
"""
from fastapi import APIRouter, HTTPException
from core.db import graph_driver
from services.graph_analytics import fraud_sequence_payload

router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.get("/circular")
def get_circular_graph():
    if graph_driver:
        query = """
        MATCH (a:Account)-[r1:TRANSFERRED_TO]->(b:Account)-[r2:TRANSFERRED_TO]->(c:Account)-[r3:TRANSFERRED_TO]->(a)
        RETURN a.id AS acc_a, b.id AS acc_b, c.id AS acc_c, r1.amount AS amt1, r2.amount AS amt2, r3.amount AS amt3
        LIMIT 50
        """
        try:
            with graph_driver.session() as session:
                result = session.run(query)
                records = list(result)

                if len(records) > 0:
                    nodes = set()
                    links = []
                    for rec in records:
                        nodes.add(rec["acc_a"])
                        nodes.add(rec["acc_b"])
                        nodes.add(rec["acc_c"])
                        links.append({"source": rec["acc_a"], "target": rec["acc_b"], "value": rec["amt1"]})
                        links.append({"source": rec["acc_b"], "target": rec["acc_c"], "value": rec["amt2"]})
                        links.append({"source": rec["acc_c"], "target": rec["acc_a"], "value": rec["amt3"]})

                    return {
                        "nodes": [{"id": n, "name": n, "group": 1} for n in nodes],
                        "links": links,
                    }
                return {"nodes": [], "links": []}
        except Exception as e:
            print(f"Neo4j query error: {e}")
            raise HTTPException(status_code=503, detail="Graph database unavailable") from e

    raise HTTPException(status_code=503, detail="Graph database unavailable")


@router.get("/benchmark")
def get_benchmark_graph():
    if graph_driver is None:
        raise HTTPException(status_code=503, detail="Graph database unavailable")
    query = """
    MATCH (source:BenchmarkAccount)-[event:BENCHMARK_TRANSACTION]->(target:BenchmarkAccount)
    RETURN source.display_id AS source, target.display_id AS target,
           event.amount AS amount, event.transaction_type AS transaction_type,
           event.relative_step AS relative_step
    ORDER BY event.relative_step DESC
    LIMIT 500
    """
    try:
        with graph_driver.session() as session:
            records = list(session.run(query))
        nodes = set()
        links = []
        for record in records:
            nodes.add(record["source"])
            nodes.add(record["target"])
            links.append({
                "source": record["source"], "target": record["target"],
                "value": record["amount"], "transaction_type": record["transaction_type"],
                "relative_step": record["relative_step"],
            })
        return {
            "dataset_id": "ds3_paysim",
            "provenance": "synthetic_simulation",
            "nodes": [{"id": node, "name": node, "group": 1} for node in sorted(nodes)],
            "links": links,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Benchmark graph unavailable") from exc


@router.get("/money-flow")
def get_benchmark_money_flow():
    if graph_driver is None:
        raise HTTPException(status_code=503, detail="Graph database unavailable")
    query = """
    MATCH ()-[event:BENCHMARK_TRANSACTION]->()
    RETURN event.transaction_type AS transaction_type,
           count(*) AS count, sum(event.amount) AS total_amount
    ORDER BY total_amount DESC
    """
    try:
        with graph_driver.session() as session:
            records = list(session.run(query))
        return [
            {"transaction_type": row["transaction_type"], "count": row["count"],
             "total_amount": row["total_amount"]}
            for row in records
        ]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Benchmark money flow unavailable") from exc


@router.get("/fraud-sequences")
def get_benchmark_fraud_sequences():
    if graph_driver is None:
        raise HTTPException(status_code=503, detail="Graph database unavailable")
    query = """
    MATCH (transfer_origin:BenchmarkAccount)-[transfer:BENCHMARK_TRANSACTION]->
          (transfer_destination:BenchmarkAccount)
    MATCH (cashout_origin:BenchmarkAccount)-[cashout:BENCHMARK_TRANSACTION]->
          (cashout_destination:BenchmarkAccount)
    WHERE transfer.transaction_type = 'TRANSFER'
      AND cashout.transaction_type = 'CASH_OUT'
      AND cashout.source_row_number = transfer.source_row_number + 1
      AND cashout.relative_step = transfer.relative_step
      AND abs(cashout.amount - transfer.amount) <= 0.01
    RETURN transfer_origin.display_id AS transfer_origin,
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
           transfer.ground_truth_is_fraud AS ground_truth_fraud
    ORDER BY cashout.relative_step DESC
    LIMIT 100
    """
    try:
        with graph_driver.session() as session:
            records = list(session.run(query))
        return {
            "dataset_id": "ds3_paysim",
            "provenance": "synthetic_simulation",
            "match_basis": "adjacent_source_rows_same_step_and_amount",
            "sequences": fraud_sequence_payload(records),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Benchmark fraud sequences unavailable") from exc
