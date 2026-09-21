"""
Neo4j graph network router.
"""
import random
from fastapi import APIRouter
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
        except Exception as e:
            print(f"Neo4j query error: {e}")

    # Mock fallback
    return {
        "nodes": [
            {"id": "ACC_92", "name": "ACC_92", "group": 1},
            {"id": "ACC_11", "name": "ACC_11", "group": 1},
            {"id": "ACC_44", "name": "ACC_44", "group": 2},
            {"id": "ACC_05", "name": "ACC_05", "group": 2},
            {"id": "ACC_73", "name": "ACC_73", "group": 3},
            {"id": "Crypto_Ex", "name": "Crypto Ex", "group": 4},
        ],
        "links": [
            {"source": "ACC_92", "target": "ACC_11", "value": 5000},
            {"source": "ACC_11", "target": "ACC_44", "value": 4500},
            {"source": "ACC_44", "target": "ACC_92", "value": 4000},
            {"source": "ACC_05", "target": "ACC_73", "value": 8000},
            {"source": "ACC_73", "target": "ACC_05", "value": 7500},
            {"source": "ACC_44", "target": "Crypto_Ex", "value": 12000},
        ],
    }
