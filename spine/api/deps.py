import hmac
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import sqlalchemy as sa
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from spine.auth.jwt import decode_access_token
from spine.auth.oidc import decode_bearer_token, has_role
from spine.config.settings import settings
from spine.db.database import SessionLocal
from spine.models.api_key import ApiKey
from spine.models.user import Membership


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def _admin_key_valid(x_api_key: str | None) -> bool:
    if not x_api_key or not settings.admin_api_key:
        return False
    return hmac.compare_digest(x_api_key, settings.admin_api_key)


def require_admin_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not _admin_key_valid(x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


AdminKeyDep = Depends(require_admin_api_key)

_bearer = HTTPBearer(auto_error=False)


def require_admin_access(
    x_api_key: str | None = Header(default=None),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    if _admin_key_valid(x_api_key):
        return
    if creds and creds.scheme.lower() == "bearer":
        claims = decode_bearer_token(creds.credentials)
        if claims and has_role(claims, settings.oidc_admin_role):
            return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


AdminAccessDep = Depends(require_admin_access)


@dataclass(frozen=True)
class OrgAuth:
    org_id: uuid.UUID
    role: str | None
    user_id: uuid.UUID | None
    via_api_key: bool

    @property
    def is_org_admin(self) -> bool:
        return self.via_api_key or self.role == "admin"


async def require_org_access(
    db: AsyncSession = Depends(get_db),
    x_org_key: str | None = Header(default=None),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> OrgAuth:
    if x_org_key:
        key_hash = ApiKey.hash_raw_key(x_org_key)
        result = await db.execute(
            sa.select(ApiKey).where(ApiKey.key_hash == key_hash).where(ApiKey.revoked_at.is_(None))
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            return OrgAuth(org_id=api_key.org_id, role=None, user_id=None, via_api_key=True)

    if creds and creds.scheme.lower() == "bearer":
        claims = decode_access_token(creds.credentials)
        if claims:
            user_id = uuid.UUID(claims["sub"])
            org_id = uuid.UUID(claims["org"])
            result = await db.execute(
                sa.select(Membership).where(
                    Membership.user_id == user_id,
                    Membership.org_id == org_id,
                )
            )
            membership = result.scalar_one_or_none()
            if membership:
                return OrgAuth(
                    org_id=org_id,
                    role=membership.role,
                    user_id=user_id,
                    via_api_key=False,
                )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid credentials")


async def require_org_id(auth: OrgAuth = Depends(require_org_access)) -> uuid.UUID:
    return auth.org_id


async def require_org_admin(auth: OrgAuth = Depends(require_org_access)) -> OrgAuth:
    if not auth.is_org_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin role required",
        )
    return auth


async def require_approval_org_access(
    org_id: uuid.UUID,
    x_api_key: str | None = Header(default=None),
    auth: OrgAuth = Depends(require_org_access),
) -> uuid.UUID:
    """Platform admin (API key) may access any org; JWT org admins only their org."""
    if _admin_key_valid(x_api_key):
        return org_id
    if not auth.is_org_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization admin role required")
    if org_id != auth.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-organization access denied")
    return org_id


OrgIdDep = Depends(require_org_id)
OrgAuthDep = Depends(require_org_access)
OrgAdminDep = Depends(require_org_admin)
ApprovalOrgDep = Depends(require_approval_org_access)
