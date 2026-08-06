import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import OrgAdminDep, OrgAuth, get_db
from spine.models.api_key import ApiKey
from spine.schemas.org import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse

router = APIRouter()


def _to_response(key: ApiKey) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=key.id,
        org_id=key.org_id,
        name=key.name,
        created_at=key.created_at,
        revoked_at=key.revoked_at,
        is_active=key.revoked_at is None,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    auth: OrgAuth = OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    result = await db.execute(sa.select(ApiKey).where(ApiKey.org_id == auth.org_id).order_by(ApiKey.created_at.desc()))
    return [_to_response(k) for k in result.scalars().all()]


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    auth: OrgAuth = OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    raw_key = ApiKey.new_raw_key()
    api_key = ApiKey(
        org_id=auth.org_id,
        key_hash=ApiKey.hash_raw_key(raw_key),
        name=payload.name,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return ApiKeyCreatedResponse(
        id=api_key.id,
        org_id=api_key.org_id,
        name=api_key.name,
        raw_key=raw_key,
    )


@router.post("/{key_id}/revoke", response_model=ApiKeyResponse)
async def revoke_api_key(
    key_id: uuid.UUID,
    auth: OrgAuth = OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    result = await db.execute(sa.select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == auth.org_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    if key.revoked_at is None:
        key.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(key)
    return _to_response(key)
