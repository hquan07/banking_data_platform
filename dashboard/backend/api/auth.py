"""
Authentication router.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from core.db import pg_conn
from core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not pg_conn:
        raise HTTPException(status_code=500, detail="Database not connected")
    with pg_conn.cursor() as cur:
        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (form_data.username,))
        user = cur.fetchone()

    if not user or not verify_password(form_data.password, user[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user[1], "role": user[3], "id": user[0]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user[3], "username": user[1]}
