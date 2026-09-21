"""
Users management and Admin stats router.
"""
from fastapi import APIRouter, Depends, HTTPException
from core.db import pg_conn
from core.deps import get_current_user

router = APIRouter(prefix="/api", tags=["Users"])


@router.get("/users")
def get_users(current_user: dict = Depends(get_current_user)):
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT id, username, role FROM users ORDER BY id")
                rows = cur.fetchall()
                return [{"id": row[0], "username": row[1], "role": row[2]} for row in rows]
        except Exception as e:
            print(f"Error fetching users: {e}")
    return []


@router.get("/admin/users-stats")
def get_users_stats(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                # Basic stats & severity breakdown
                cur.execute("""
                    SELECT u.id, u.username, u.role,
                           COUNT(a.alert_id) AS total_assigned,
                           SUM(CASE WHEN a.status = 'RESOLVED' THEN 1 ELSE 0 END) AS total_resolved,
                           SUM(CASE WHEN a.status IN ('PENDING', 'INVESTIGATING') THEN 1 ELSE 0 END) AS pending,
                           COALESCE(AVG(a.risk_score), 0) AS avg_risk,
                           SUM(CASE WHEN a.risk_score > 85 THEN 1 ELSE 0 END) AS high_risk,
                           SUM(CASE WHEN a.risk_score BETWEEN 60 AND 85 THEN 1 ELSE 0 END) AS medium_risk,
                           SUM(CASE WHEN a.risk_score < 60 THEN 1 ELSE 0 END) AS low_risk
                    FROM users u
                    LEFT JOIN alerts a ON u.id = a.assignee_id
                    GROUP BY u.id, u.username, u.role
                    ORDER BY u.id
                """)
                rows = cur.fetchall()
                stats = []
                for row in rows:
                    user_id = row[0]

                    # Rule breakdown
                    cur.execute("""
                        SELECT rule_name, COUNT(*) 
                        FROM alerts 
                        WHERE assignee_id = %s 
                        GROUP BY rule_name
                    """, (user_id,))
                    rule_rows = cur.fetchall()
                    rules_breakdown = {r[0]: r[1] for r in rule_rows}

                    stats.append({
                        "id": user_id,
                        "username": row[1],
                        "role": row[2],
                        "total_assigned": int(row[3] or 0),
                        "total_resolved": int(row[4] or 0),
                        "pending": int(row[5] or 0),
                        "avg_risk": round(float(row[6] or 0), 2),
                        "severity": {
                            "high": int(row[7] or 0),
                            "medium": int(row[8] or 0),
                            "low": int(row[9] or 0),
                        },
                        "rules": rules_breakdown,
                    })
                return stats
        except Exception as e:
            print(f"Error fetching user stats: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    return []
