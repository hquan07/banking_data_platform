"""
Authentication router.
"""
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from core.db import pg_conn, redis_client
from core.deps import get_current_user
from core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from services.security_controls import (
    create_session,
    list_active_sessions,
    login_limit,
    record_security_event,
    revoke_all_sessions,
    revoke_session,
    utc_expiry,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    if not pg_conn:
        raise HTTPException(status_code=503, detail="Database not connected")
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Rate-limit store unavailable")
    source = request.client.host if request.client else "unknown"
    decision = login_limit(redis_client, form_data.username, source)
    if not decision.allowed:
        record_security_event(
            pg_conn,
            event_type="LOGIN",
            outcome="RATE_LIMITED",
            source=source,
            subject=form_data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash, role, is_active "
            "FROM users WHERE username = %s",
            (form_data.username,),
        )
        user = cur.fetchone()

    if not user or not user[4] or not verify_password(form_data.password, user[2]):
        record_security_event(
            pg_conn,
            event_type="LOGIN",
            outcome="DENIED",
            source=source,
            subject=form_data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = utc_expiry(ACCESS_TOKEN_EXPIRE_MINUTES)
    token_jti = str(uuid.uuid4())
    access_token = create_access_token(
        data={"sub": user[1], "role": user[3], "id": user[0], "jti": token_jti},
        expires_delta=access_token_expires,
    )
    create_session(
        pg_conn,
        token_jti=token_jti,
        user_id=user[0],
        expires_at=expires_at,
        source=source,
        user_agent=request.headers.get("user-agent"),
    )
    record_security_event(
        pg_conn,
        event_type="LOGIN",
        outcome="SUCCESS",
        source=source,
        actor_user_id=user[0],
        session_jti=token_jti,
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user[3], "username": user[1]}


@router.get("/sessions")
async def sessions(current_user=Depends(get_current_user)):
    return {"sessions": list_active_sessions(pg_conn, current_user["id"])}


@router.post("/logout")
async def logout(request: Request, current_user=Depends(get_current_user)):
    revoked = revoke_session(
        pg_conn,
        token_jti=current_user["jti"],
        user_id=current_user["id"],
        reason="USER_LOGOUT",
    )
    record_security_event(
        pg_conn,
        event_type="LOGOUT",
        outcome="SUCCESS" if revoked else "NOOP",
        source=request.client.host if request.client else "unknown",
        actor_user_id=current_user["id"],
        session_jti=current_user["jti"],
    )
    return {"revoked": revoked}


@router.post("/logout-all")
async def logout_all(request: Request, current_user=Depends(get_current_user)):
    revoked = revoke_all_sessions(
        pg_conn,
        user_id=current_user["id"],
        reason="USER_LOGOUT_ALL",
    )
    record_security_event(
        pg_conn,
        event_type="LOGOUT_ALL",
        outcome="SUCCESS",
        source=request.client.host if request.client else "unknown",
        actor_user_id=current_user["id"],
        session_jti=current_user["jti"],
        details={"revoked_sessions": revoked},
    )
    return {"revoked_sessions": revoked}
