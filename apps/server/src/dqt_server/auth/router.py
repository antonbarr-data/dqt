from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.auth import google as google_oauth
from dqt_server.auth import service
from dqt_server.auth.dependencies import get_current_user, require_sysadmin
from dqt_server.auth.models import ROLE_SYSADMIN, User
from dqt_server.auth.schemas import Token, UserCreate, UserCreateAdmin, UserPatch, UserPromote, UserRead
from dqt_server.db.engine import get_db
from dqt_server.models.core import OncallShift

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

    picture: str | None = info.get("picture")
    token = service.create_token(user, picture=picture)
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


@router.post("/api/v1/admin/users", response_model=UserRead, status_code=201)
async def create_user(
    data: UserCreateAdmin,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
) -> User:
    from dqt_server.api.v1.oncall import redistribute_oncall_days
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    hashed = service.hash_password(data.password) if data.password else None
    user = User(
        email=data.email,
        name=data.name or None,
        hashed_password=hashed,
        role=data.role,
        oncall_eligible=data.oncall_eligible,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if data.oncall_eligible:
        await redistribute_oncall_days(db)
    return user


@router.patch("/api/v1/admin/users/{user_id}", response_model=UserRead)
async def patch_user(
    user_id: uuid.UUID,
    body: UserPatch,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
) -> User:
    from dqt_server.api.v1.oncall import redistribute_oncall_days
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    oncall_changed = False
    if body.name is not None:
        user.name = body.name or None
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        if user.email == service.SEEDED_SYSADMIN_EMAIL and not body.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate the root Super Admin")
        user.is_active = body.is_active
    if body.oncall_eligible is not None and body.oncall_eligible != user.oncall_eligible:
        user.oncall_eligible = body.oncall_eligible
        oncall_changed = True
    await db.commit()
    await db.refresh(user)
    if oncall_changed:
        await redistribute_oncall_days(db)
    return user


@router.delete("/api/v1/admin/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
) -> None:
    from dqt_server.api.v1.oncall import redistribute_oncall_days
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.email == service.SEEDED_SYSADMIN_EMAIL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete the root Super Admin")
    was_eligible = user.oncall_eligible
    await db.execute(sa_delete(OncallShift).where(OncallShift.user_id == str(user_id)))
    await db.delete(user)
    await db.commit()
    if was_eligible:
        await redistribute_oncall_days(db)
