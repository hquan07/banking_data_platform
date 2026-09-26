"""
Analytics (ClickHouse) and KYC 360° router.
"""
import datetime
import random
from fastapi import APIRouter, Depends
from core.db import pg_conn, ch_client, graph_driver
from core.deps import get_current_user

router = APIRouter(prefix="/api", tags=["Analytics"])


@router.get("/analytics/history")
def get_history_analytics():
    if ch_client:
        try:
            query = """
                SELECT 
                    toDate(event_time) AS date,
                    count() AS total_tx,
                    sum(amount) AS total_amount,
                    sum(if(status='FRAUD', 1, 0)) AS total_fraud
                FROM fct_transactions
                GROUP BY date
                ORDER BY date DESC
                LIMIT 30
            """
            result = ch_client.execute(query)
            data = []
            for row in reversed(result):
                data.append({
                    "date": str(row[0]),
                    "total_tx": row[1],
                    "total_amount": row[2],
                    "total_fraud": row[3],
                })
            if data:
                return data
        except Exception as e:
            print(f"ClickHouse query error: {e}")

    # Mock fallback
    data = []
    for i in range(14, -1, -1):
        date = datetime.date.today() - datetime.timedelta(days=i)
        data.append({
            "date": str(date),
            "total_tx": 1000 + (i * 10) % 500,
            "total_amount": 500000 + (i * 5000) % 200000,
            "total_fraud": 5 + i % 10,
        })
    return data


@router.get("/accounts/{account_id}/kyc")
def get_kyc_profile(account_id: str, current_user: dict = Depends(get_current_user)):
    profile = {
        "account_id": account_id,
        "trust_score": None,
        "total_alerts": 0,
        "resolved_alerts": 0,
        "recent_transactions": [],
        "devices": [],
        "network_graph": {"nodes": [], "links": []},
    }

    # 1. Postgres: Alert history and trust score
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM alerts WHERE account_id = %s", (account_id,))
                profile["total_alerts"] = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM alerts WHERE account_id = %s AND status = 'RESOLVED'", (account_id,))
                profile["resolved_alerts"] = cur.fetchone()[0]

                if profile["total_alerts"] == 0:
                    profile["trust_score"] = 95
                elif profile["total_alerts"] < 5:
                    profile["trust_score"] = 70
                elif profile["total_alerts"] < 15:
                    profile["trust_score"] = 45
                else:
                    profile["trust_score"] = 20
        except Exception as e:
            print(f"KYC Postgres error: {e}")

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
                    links.append({"source": rec["src"], "target": rec["dst"], "value": rec.get("amt", 100)})
                    if rec["hop2"]:
                        nodes_set.add(rec["hop2"])
                        links.append({"source": rec["dst"], "target": rec["hop2"], "value": 50})

                profile["network_graph"] = {
                    "nodes": [{"id": n, "name": n, "group": 1 if n == account_id else 2} for n in nodes_set],
                    "links": links,
                }
        except Exception as e:
            print(f"KYC Neo4j error: {e}")

    # Mock fallback for network graph
    if not profile["network_graph"]["nodes"]:
        mock_peers = [f"ACC_{random.randint(1,100)}" for _ in range(4)]
        profile["network_graph"] = {
            "nodes": [{"id": account_id, "name": account_id, "group": 1}] + [{"id": p, "name": p, "group": 2} for p in mock_peers],
            "links": [{"source": account_id, "target": p, "value": random.randint(500, 8000)} for p in mock_peers],
        }

    # 3. Real recent transactions and devices from ClickHouse
    if ch_client:
        try:
            # Query recent transactions
            tx_query = """
                SELECT event_time, amount, payment_method
                FROM fct_transactions
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
                FROM fct_transactions
                WHERE account_id = %(account_id)s AND device_id != ''
                GROUP BY device_id
                LIMIT 5
            """
            device_result = ch_client.execute(device_query, {"account_id": account_id})
            if device_result:
                profile["devices"] = [
                    {"name": row[0], "last_seen": str(row[1]), "ip": "Unknown"}
                    for row in device_result
                ]
        except Exception as e:
            print(f"KYC ClickHouse error: {e}")

    # Fallback if no data found
    if not profile["recent_transactions"]:
        profile["recent_transactions"] = [
            {"time": str(datetime.datetime.now() - datetime.timedelta(minutes=i * 5)), "amount": round(random.uniform(50, 5000), 2), "type": random.choice(["TRANSFER", "PAYMENT", "DEPOSIT"])}
            for i in range(3)
        ]
    if not profile["devices"]:
        profile["devices"] = [
            {"name": "Unknown Device", "last_seen": "N/A", "ip": "N/A"}
        ]

    if profile["trust_score"] is None:
        profile["trust_score"] = 75

    return profile
