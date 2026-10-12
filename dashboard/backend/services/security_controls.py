"""Durable session, audit and Redis-backed rate-limit controls."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from prometheus_client import Counter, Gauge


SECURITY_EVENTS = Counter(
    "banking_security_events_total",
    "Security events recorded by type and outcome",
    ("event_type", "outcome"),
)
RATE_LIMIT_REJECTIONS = Counter(
    "banking_rate_limit_rejections_total",
    "Requests rejected by a bounded rate-limit scope",
    ("scope",),
)
ACTIVE_SESSIONS = Gauge(
    "banking_active_sessions",
    "Unexpired and non-revoked dashboard sessions",
)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


def fingerprint(value: str | None) -> str:
    """Return a non-reversible, fixed-width identifier for audit correlation."""
    return hashlib.sha256((value or "unknown").encode()).hexdigest()


def consume_rate_limit(
    redis_client: Any,
    *,
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int,
    now: float | None = None,
) -> RateLimitDecision:
    if limit <= 0 or window_seconds <= 0:
        raise ValueError("Rate-limit values must be positive")
    observed = time.time() if now is None else now
    bucket = int(observed // window_seconds)
    key = f"security:rate:{scope}:{bucket}:{fingerprint(identity)}"
    value = int(redis_client.incr(key))
    if value == 1:
        redis_client.expire(key, window_seconds * 2)
    retry_after = max(1, int(((bucket + 1) * window_seconds) - observed))
    allowed = value <= limit
    if not allowed:
        RATE_LIMIT_REJECTIONS.labels(scope).inc()
    return RateLimitDecision(
        allowed=allowed,
        remaining=max(0, limit - value),
        retry_after_seconds=retry_after,
    )


def login_limit(redis_client: Any, username: str, source: str) -> RateLimitDecision:
    return consume_rate_limit(
        redis_client,
        scope="login",
        identity=f"{username.strip().lower()}:{source}",
        limit=int(os.environ.get("LOGIN_RATE_LIMIT", "10")),
        window_seconds=int(os.environ.get("LOGIN_RATE_WINDOW_SECONDS", "60")),
    )


def api_limit(redis_client: Any, identity: str) -> RateLimitDecision:
    return consume_rate_limit(
        redis_client,
        scope="api",
        identity=identity,
        limit=int(os.environ.get("API_RATE_LIMIT", "240")),
        window_seconds=int(os.environ.get("API_RATE_WINDOW_SECONDS", "60")),
    )


def record_security_event(
    connection: Any,
    *,
    event_type: str,
    outcome: str,
    source: str,
    actor_user_id: int | None = None,
    session_jti: str | None = None,
    subject: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO security_events
                (event_type, outcome, actor_user_id, session_jti,
                 source_fingerprint, subject_fingerprint, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                event_type,
                outcome,
                actor_user_id,
                session_jti,
                fingerprint(source),
                fingerprint(subject) if subject else None,
                json.dumps(details or {}, sort_keys=True),
            ),
        )
    SECURITY_EVENTS.labels(event_type, outcome).inc()


def create_session(
    connection: Any,
    *,
    token_jti: str,
    user_id: int,
    expires_at: datetime,
    source: str,
    user_agent: str | None,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO auth_sessions
                (token_jti, user_id, expires_at, source_fingerprint,
                 user_agent_fingerprint)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                token_jti,
                user_id,
                expires_at,
                fingerprint(source),
                fingerprint(user_agent),
            ),
        )


def revoke_session(
    connection: Any,
    *,
    token_jti: str,
    user_id: int,
    reason: str,
) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = NOW(), revoke_reason = %s
            WHERE token_jti = %s AND user_id = %s AND revoked_at IS NULL
            RETURNING token_jti
            """,
            (reason, token_jti, user_id),
        )
        return cursor.fetchone() is not None


def revoke_all_sessions(connection: Any, *, user_id: int, reason: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = NOW(), revoke_reason = %s
            WHERE user_id = %s AND revoked_at IS NULL AND expires_at > NOW()
            """,
            (reason, user_id),
        )
        return cursor.rowcount


def list_active_sessions(connection: Any, user_id: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT token_jti, issued_at, expires_at, source_fingerprint,
                   user_agent_fingerprint
            FROM auth_sessions
            WHERE user_id = %s AND revoked_at IS NULL AND expires_at > NOW()
            ORDER BY issued_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
    return [
        {
            "session_id": str(row[0]),
            "issued_at": row[1],
            "expires_at": row[2],
            "source_fingerprint": row[3],
            "user_agent_fingerprint": row[4],
        }
        for row in rows
    ]


def refresh_active_session_metric(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM auth_sessions "
            "WHERE revoked_at IS NULL AND expires_at > NOW()"
        )
        ACTIVE_SESSIONS.set(cursor.fetchone()[0])


def utc_expiry(minutes: int) -> datetime:
    from datetime import timedelta

    return datetime.now(timezone.utc) + timedelta(minutes=minutes)
