"""
FastAPI dependency: get_current_user from Authorization Bearer token.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_token, check_jti_not_revoked
from core.models import User

from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token, expected_type="access")
    user_id: str = payload.get("sub", "")
    jti: str = payload.get("jti", "")

    await check_jti_not_revoked(jti, db)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise _credentials_exc

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
