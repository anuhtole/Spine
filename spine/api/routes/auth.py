import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import get_db
from spine.auth.jwt import create_access_token, decode_access_token
from spine.auth.passwords import hash_password, verify_password
from spine.models.organization import Organization
from spine.models.user import Membership, User
from spine.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, UserInfo

router = APIRouter()

_bearer = HTTPBearer(auto_error=False)


async def _get_user_info(db: AsyncSession, user: User) -> UserInfo | None:
    """Load the first active membership for a user and return UserInfo."""
    result = await db.execute(
        sa.select(Membership, Organization)
        .join(Organization, Membership.org_id == Organization.id)
        .where(Membership.user_id == user.id)
        .limit(1)
    )
    row = result.first()
    if not row:
        return None
    membership, org = row
    return UserInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        org_id=org.id,
        org_name=org.name,
        role=membership.role,
    )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    result = await db.execute(sa.select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    info = await _get_user_info(db, user)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any organization",
        )

    token = create_access_token(user_id=user.id, org_id=info.org_id, role=info.role)
    return LoginResponse(token=token, user=info)


@router.get("/me", response_model=UserInfo)
async def me(
    db: AsyncSession = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserInfo:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    claims = decode_access_token(creds.credentials)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = uuid.UUID(claims["sub"])
    result = await db.execute(sa.select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    info = await _get_user_info(db, user)
    if not info:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization membership")

    return info


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    claims = decode_access_token(creds.credentials)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = uuid.UUID(claims["sub"])
    result = await db.execute(sa.select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)
    await db.commit()
