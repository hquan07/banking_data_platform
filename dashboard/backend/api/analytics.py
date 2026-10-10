"""
Analytics (ClickHouse) and KYC 360° router.
"""
from fastapi import APIRouter, Depends, HTTPException
from core.db import pg_conn, ch_client, graph_driver
from core.deps import get_current_user

router = APIRouter(prefix="/api", tags=["Analytics"])


@router.get("/analytics/history")
def get_history_analytics(current_user: dict = Depends(get_current_user)):
    if ch_client:
        try:
            query = """
                SELECT 
                    toDate(event_time) AS date,
                    count() AS total_tx,
                    sum(amount) AS total_amount
                FROM payment_events FINAL
                GROUP BY date
                ORDER BY date DESC
                LIMIT 30
            """
            result = ch_client.execute(query)
            alert_counts = {}
            if pg_conn:
                with pg_conn.cursor() as cur:
                    cur.execute("SELECT created_at::date, count(*) FROM alerts GROUP BY created_at::date")
                    alert_counts = {str(day): count for day, count in cur.fetchall()}
            return [
                {
                    "date": str(row[0]),
                    "total_tx": row[1],
                    "total_amount": row[2],
                    "total_alerts": alert_counts.get(str(row[0]), 0),
                }
                for row in reversed(result)
            ]
        except Exception as e:
            print(f"ClickHouse query error: {e}")
            raise HTTPException(status_code=503, detail="Analytics database unavailable") from e
    raise HTTPException(status_code=503, detail="Analytics database unavailable")


@router.get("/accounts/{account_id}/kyc")
def get_kyc_profile(account_id: str, current_user: dict = Depends(get_current_user)):
    if pg_conn is None or graph_driver is None or ch_client is None:
        raise HTTPException(status_code=503, detail="KYC dependencies unavailable")
    profile = {
        "account_id": account_id,
        "total_alerts": 0,
        "resolved_alerts": 0,
        "recent_transactions": [],
        "devices": [],
        "network_graph": {"nodes": [], "links": []},
    }

    # 1. Postgres: case history
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM alerts WHERE account_id = %s", (account_id,))
                profile["total_alerts"] = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM alerts WHERE account_id = %s AND status = 'RESOLVED'", (account_id,))
                profile["resolved_alerts"] = cur.fetchone()[0]

        except Exception as e:
            print(f"KYC Postgres error: {e}")
            raise HTTPException(status_code=503, detail="KYC database unavailable") from e

    # 2. Neo4j: Network graph for this account
    if graph_driver:
        try:
            query = """
            MATCH (a:Account {id: $account_id})-[r:TRANSFERRED_TO]-(b:Account)
            OPTIONAL MATCH (b)-[r2:TRANSFERRED_TO]-(c:Account)
            WHERE c.id <> $account_id
            RETURN DISTINCT a.id AS src, b.id AS dst, type(r) AS rel, r.amount AS amt, c.id AS hop2
            LIMIT 30
            """
            with graph_driver.session() as session:
                result = session.run(query, account_id=account_id)
                records = list(result)
                nodes_set = {account_id}
                links = []
                for rec in records:
                    nodes_set.add(rec["dst"])
                    links.append({"source": rec["src"], "target": rec["dst"], "value": rec["amt"]})
                    if rec["hop2"]:
                        nodes_set.add(rec["hop2"])
                        links.append({"source": rec["dst"], "target": rec["hop2"], "value": rec["amt"]})

                profile["network_graph"] = {
                    "nodes": [{"id": n, "name": n, "group": 1 if n == account_id else 2} for n in nodes_set],
                    "links": links,
                }
        except Exception as e:
            print(f"KYC Neo4j error: {e}")
            raise HTTPException(status_code=503, detail="Graph database unavailable") from e

    # 3. Real recent transactions and devices from ClickHouse
    if ch_client:
        try:
            # Query recent transactions
            tx_query = """
                SELECT event_time, amount, payment_method
                FROM payment_events FINAL
                WHERE account_id = %(account_id)s
                ORDER BY event_time DESC
                LIMIT 10
            """
            tx_result = ch_client.execute(tx_query, {"account_id": account_id})
            if tx_result:
                profile["recent_transactions"] = [
                    {"time": str(row[0]), "amount": float(row[1]), "type": row[2]}
                    for row in tx_result
                ]

            # Query devices
            device_query = """
                SELECT device_id, max(event_time)
                FROM payment_events FINAL
                WHERE account_id = %(account_id)s AND device_id != ''
                GROUP BY device_id
                LIMIT 5
            """
            device_result = ch_client.execute(device_query, {"account_id": account_id})
            if device_result:
                profile["devices"] = [
                    {"name": row[0], "last_seen": str(row[1])}
                    for row in device_result
                ]
        except Exception as e:
            print(f"KYC ClickHouse error: {e}")
            raise HTTPException(status_code=503, detail="Analytics database unavailable") from e

    return profile
