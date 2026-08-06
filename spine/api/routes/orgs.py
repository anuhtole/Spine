import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import AdminAccessDep, get_db
from spine.models.api_key import ApiKey
from spine.models.organization import Organization
from spine.schemas.org import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    OrganizationCreate,
    OrganizationResponse,
)

router = APIRouter()


@router.post("", response_model=OrganizationResponse, dependencies=[AdminAccessDep])
async def create_org(payload: OrganizationCreate, db: AsyncSession = Depends(get_db)) -> OrganizationResponse:
    org = Organization(name=payload.name, plan=payload.plan or "starter")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return OrganizationResponse(id=org.id, name=org.name, plan=org.plan)


@router.post("/{org_id}/api-keys", response_model=ApiKeyCreatedResponse, dependencies=[AdminAccessDep])
async def create_org_api_key(
    org_id: uuid.UUID, payload: ApiKeyCreate, db: AsyncSession = Depends(get_db)
) -> ApiKeyCreatedResponse:
    result = await db.execute(sa.select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    raw_key = ApiKey.new_raw_key()
    api_key = ApiKey(org_id=org_id, key_hash=ApiKey.hash_raw_key(raw_key), name=payload.name)
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return ApiKeyCreatedResponse(id=api_key.id, org_id=api_key.org_id, name=api_key.name, raw_key=raw_key)


@router.post("/{org_id}/api-keys/{key_id}/revoke", dependencies=[AdminAccessDep])
async def revoke_org_api_key(org_id: uuid.UUID, key_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    from datetime import datetime, timezone

    result = await db.execute(sa.select(ApiKey).where(ApiKey.id == key_id).where(ApiKey.org_id == org_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    if key.revoked_at is not None:
        return {"status": "already_revoked"}
    key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "revoked"}
