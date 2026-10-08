"""
Neo4j graph network router.
"""
from fastapi import APIRouter, HTTPException
from core.db import graph_driver

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
