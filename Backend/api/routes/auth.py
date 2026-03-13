"""
Auth routes: register, login, logout, refresh, forgot-password, reset-password.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from core.database import get_db
from core.models import User, UserSession
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
    constant_compare,
    validate_password_strength,
)
from core.config import settings
from api.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _create_session(
    user_id: str,
    jti: str,
    expires_at: datetime,
    db: AsyncSession,
    request: Request | None = None,
) -> None:
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    session = UserSession(
        user_id=user_id,
        jti=jti,
        ip_address=ip,
        user_agent=ua,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    if not validate_password_strength(req.password):
        raise HTTPException(
            status_code=422,
            detail="Password must be ≥8 chars and contain letters and digits",
        )

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
    )
    db.add(user)
    await db.flush()
    return {"message": "User registered", "user_id": user.id}


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access_token, access_jti = create_access_token(user.id, user.role)
    refresh_token, refresh_jti = create_refresh_token(user.id)

    access_expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    refresh_expires = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    # Store BOTH JTIs as sessions (access JTI for fast revocation checks)
    await _create_session(user.id, access_jti, access_expires, db, request)
    await _create_session(user.id, refresh_jti, refresh_expires, db, request)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    token_data: str = Depends(lambda: None),  # placeholder
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Revoke all active sessions for the user."""
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == current_user.id, UserSession.is_revoked == False)
        .values(is_revoked=True)
    )
    return {"message": "Logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db), request: Request = None):
    payload = decode_token(req.refresh_token, expected_type="refresh")
    user_id = payload.get("sub", "")
    old_jti = payload.get("jti", "")

    # Revoke old refresh session
    old_session_result = await db.execute(
        select(UserSession).where(UserSession.jti == old_jti)
    )
    old_session = old_session_result.scalar_one_or_none()
    if not old_session or old_session.is_revoked:
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token")

    old_session.is_revoked = True

    # Issue new tokens
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    access_token, access_jti = create_access_token(user.id, user.role)
    refresh_token, refresh_jti = create_refresh_token(user.id)

    access_expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    refresh_expires = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    await _create_session(user.id, access_jti, access_expires, db, request)
    await _create_session(user.id, refresh_jti, refresh_expires, db, request)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Always returns 200 to prevent email enumeration."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if user:
        raw_token, hashed_token = generate_reset_token()
        user.password_reset_token = hashed_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
        )
        # In production: enqueue email task via Celery
        # For now: log the reset link (dev mode)
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        print(f"[DEV] Password reset link for {req.email}: {reset_link}")

    return {"message": "If that email is registered, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    import hashlib

    token_hash = hashlib.sha256(req.token.encode()).hexdigest()

    result = await db.execute(
        select(User).where(User.password_reset_token == token_hash)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    now = datetime.now(timezone.utc)
    token_expires = user.reset_token_expires
    if token_expires is None or (
        token_expires.tzinfo is None
        and now.replace(tzinfo=None) > token_expires
    ) or (
        token_expires.tzinfo is not None and now > token_expires
    ):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    if not validate_password_strength(req.new_password):
        raise HTTPException(
            status_code=422,
            detail="Password must be ≥8 chars and contain letters and digits",
        )

    user.hashed_password = hash_password(req.new_password)
    user.password_reset_token = None
    user.reset_token_expires = None

    # Revoke all sessions
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id)
        .values(is_revoked=True)
    )

    return {"message": "Password reset successful. Please log in again."}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
    }
