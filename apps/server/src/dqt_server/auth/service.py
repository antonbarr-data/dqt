from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from dqt_server.auth.models import User

_ALGORITHM = "HS256"
_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

SEEDED_SYSADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@localhost")


def _secret() -> str:
    return os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user: User, picture: str | None = None) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "tenant": user.tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_EXPIRE_MINUTES),
    }
    if picture:
        payload["picture"] = picture
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
