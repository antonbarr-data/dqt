from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.auth import google as google_oauth
from dqt_server.auth import service
from dqt_server.auth.dependencies import get_current_user, require_sysadmin
from dqt_server.auth.models import ROLE_SYSADMIN, User
from dqt_server.auth.schemas import Token, UserCreate, UserPromote, UserRead
from dqt_server.db.engine import get_db

router = APIRouter(tags=["auth"])


# ── email/password ──────────────────────────────────────────────────────────

@router.post("/api/v1/auth/register", response_model=UserRead, status_code=201)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    user = User(email=data.email, hashed_password=service.hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/api/v1/auth/login", response_model=Token)
async def login(data: UserCreate, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not service.verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    return {"access_token": service.create_token(user)}


# ── Google OAuth ─────────────────────────────────────────────────────────────

@router.get("/api/v1/auth/google/authorize")
def google_authorize() -> RedirectResponse:
    return RedirectResponse(url=google_oauth.get_authorize_url())


@router.get("/api/v1/auth/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    try:
        info = await google_oauth.exchange_code(code)
    except Exception:
        return RedirectResponse(f"{frontend_url}/login?error=oauth_failed")

    google_id: str = info["id"]
    email: str = info["email"]

    # Find by google_id first, then by email (links existing account)
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(email=email, google_id=google_id)
            db.add(user)
        else:
            user.google_id = google_id
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        return RedirectResponse(f"{frontend_url}/login?error=account_disabled")

    token = service.create_token(user)
    return RedirectResponse(f"{frontend_url}/auth/callback?token={token}")


# ── current user ─────────────────────────────────────────────────────────────

@router.get("/api/v1/auth/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


# ── Super Admin: user management ─────────────────────────────────────────────

@router.get("/api/v1/admin/users", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


@router.patch("/api/v1/admin/users/{user_id}/role", response_model=UserRead)
async def update_role(
    user_id: uuid.UUID,
    body: UserPromote,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_sysadmin),
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    allowed_roles = {"viewer", "editor", "admin", "sysadmin"}
    if body.role not in allowed_roles:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Role must be one of {allowed_roles}")
    user.role = body.role
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/api/v1/admin/users/{user_id}/active", response_model=UserRead)
async def set_active(
    user_id: uuid.UUID,
    active: bool,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_sysadmin),
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.email == service.SEEDED_SYSADMIN_EMAIL and not active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate the root Super Admin")
    user.is_active = active
    await db.commit()
    await db.refresh(user)
    return user
