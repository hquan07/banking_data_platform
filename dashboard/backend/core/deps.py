"""
FastAPI dependency injection functions.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import InvalidTokenError
from core.security import SECRET_KEY, ALGORITHM
from core.db import pg_conn

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def resolve_user_token(token: str):
    """Authenticate JWT identity, then authorize using the current DB role."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if not username or not isinstance(user_id, int):
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    if pg_conn is None:
        raise HTTPException(status_code=503, detail="User database unavailable")
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute("SELECT username, role FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="User database unavailable") from exc
    if row is None or row[0] != username:
        raise credentials_exception
    return {"username": row[0], "role": row[1], "id": user_id}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    return resolve_user_token(token)
