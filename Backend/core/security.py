"""
JWT dual-token security + bcrypt password hashing + JTI-based revocation.

Access token:  60 minutes
Refresh token: 7 days  (stored as UserSession row keyed by JTI)
"""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
import bcrypt
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Replaced passlib with direct bcrypt to avoid unmaintained passlib ValueError on bcrypt v4.1+
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def hash_password(password: str) -> str:
    # Hash a password with a generated salt
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


# ── Token creation ────────────────────────────────────────────────────────────
def _make_token(data: dict, expire_delta: timedelta) -> tuple[str, str]:
    """Returns (encoded_jwt, jti)"""
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        **data,
        "jti": jti,
        "iat": now,
        "exp": now + expire_delta,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def create_access_token(user_id: str, role: str = "user") -> tuple[str, str]:
    """Returns (access_token, jti)"""
    return _make_token(
        {"sub": user_id, "role": role, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Returns (refresh_token, jti)"""
    return _make_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


# ── Token verification ────────────────────────────────────────────────────────
_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decode and validate a JWT. Raises 401 on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise _credentials_exc

    if payload.get("type") != expected_type:
        raise _credentials_exc

    return payload


# ── DB-backed revocation check ────────────────────────────────────────────────
async def check_jti_not_revoked(jti: str, db: AsyncSession) -> None:
    """Raises 401 if the session JTI is marked revoked in the DB."""
    from core.models import UserSession

    result = await db.execute(
        select(UserSession).where(UserSession.jti == jti)
    )
    session = result.scalar_one_or_none()
    if session is None or session.is_revoked:
        raise _credentials_exc


async def get_current_user(
    token: str,
    db: AsyncSession,
):
    """Validate access token and return the User object."""
    from core.models import User

    payload = decode_token(token, expected_type="access")
    user_id: str = payload.get("sub", "")
    jti: str = payload.get("jti", "")

    await check_jti_not_revoked(jti, db)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise _credentials_exc

    return user


# ── Password-reset tokens ─────────────────────────────────────────────────────
def generate_reset_token() -> tuple[str, str]:
    """Returns (raw_token, sha256_hash). Store only the hash in DB."""
    raw = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def constant_compare(a: str, b: str) -> bool:
    """Timing-safe string comparison."""
    return hmac.compare_digest(a.encode(), b.encode())


def validate_password_strength(password: str) -> bool:
    """Min 8 chars, at least one digit, one letter."""
    import re
    return (
        len(password) >= 8
        and bool(re.search(r"[A-Za-z]", password))
        and bool(re.search(r"\d", password))
    )
