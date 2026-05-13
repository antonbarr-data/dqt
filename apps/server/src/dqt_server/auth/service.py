from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from dqt_server.auth.models import User

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"
_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

SEEDED_SYSADMIN_EMAIL = "antonbar@gmail.com"


def _secret() -> str:
    s = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
    return s


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


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
