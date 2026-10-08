"""
Neo4j graph network router.
"""
from fastapi import APIRouter, HTTPException
from core.db import graph_driver
from services.graph_analytics import fraud_chain_payload

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


@router.get("/fraud-chains")
def get_benchmark_fraud_chains():
    if graph_driver is None:
        raise HTTPException(status_code=503, detail="Graph database unavailable")
    query = """
    MATCH (victim:BenchmarkAccount)-[transfer:BENCHMARK_TRANSACTION]->
          (mule:BenchmarkAccount)-[cashout:BENCHMARK_TRANSACTION]->
          (exit:BenchmarkAccount)
    WHERE transfer.transaction_type = 'TRANSFER'
      AND cashout.transaction_type = 'CASH_OUT'
      AND cashout.relative_step >= transfer.relative_step
      AND cashout.relative_step <= transfer.relative_step + 24
      AND transfer.amount >= cashout.amount * 0.80
      AND transfer.amount <= cashout.amount * 1.20
    RETURN victim.display_id AS victim,
           mule.display_id AS mule,
           exit.display_id AS exit,
           transfer.event_id AS transfer_event_id,
           cashout.event_id AS cashout_event_id,
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
            "chains": fraud_chain_payload(records),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Benchmark fraud chains unavailable") from exc
