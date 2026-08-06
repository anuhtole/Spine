from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as pyjwt

from spine.config.settings import settings

_ALGORITHM = "HS256"
_TOKEN_LIFETIME = timedelta(hours=24)


def create_access_token(
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    role: str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + (expires_delta or _TOKEN_LIFETIME)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org": str(org_id),
        "role": role,
        "iat": now,
        "exp": exp,
    }
    return pyjwt.encode(payload, settings.effective_jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return pyjwt.decode(token, settings.effective_jwt_secret, algorithms=[_ALGORITHM])
    except pyjwt.PyJWTError:
        return None
