import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import OrgAdminDep, OrgAuth, OrgIdDep, get_db
from spine.core.policy_cache import invalidate as invalidate_policy_cache
from spine.models.policy import Policy
from spine.schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate

router = APIRouter()


@router.post("", response_model=PolicyResponse)
async def create_policy(
    payload: PolicyCreate,
    auth: OrgAuth = OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    org_id = auth.org_id
    policy = Policy(
        org_id=org_id,
        agent_id=payload.agent_id,
        name=payload.name,
        rule_type=payload.rule_type,
        rule_config=payload.rule_config,
        compliance_framework=payload.compliance_framework,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    await invalidate_policy_cache(org_id)
    return PolicyResponse(
        id=policy.id,
        org_id=policy.org_id,
        agent_id=policy.agent_id,
        name=policy.name,
        rule_type=policy.rule_type,
        rule_config=policy.rule_config,
        compliance_framework=policy.compliance_framework,
        is_active=policy.is_active,
    )


@router.get("", response_model=list[PolicyResponse])
async def list_policies(org_id: uuid.UUID = OrgIdDep, db: AsyncSession = Depends(get_db)) -> list[PolicyResponse]:
    result = await db.execute(sa.select(Policy).where(Policy.org_id == org_id))
    policies = list(result.scalars().all())
    return [
        PolicyResponse(
            id=p.id,
            org_id=p.org_id,
            agent_id=p.agent_id,
            name=p.name,
            rule_type=p.rule_type,
            rule_config=p.rule_config,
            compliance_framework=p.compliance_framework,
            is_active=p.is_active,
        )
        for p in policies
    ]


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: uuid.UUID,
    payload: PolicyUpdate,
    auth: OrgAuth = OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    org_id = auth.org_id
    result = await db.execute(sa.select(Policy).where(Policy.id == policy_id).where(Policy.org_id == org_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    if payload.name is not None:
        policy.name = payload.name
    if payload.rule_type is not None:
        policy.rule_type = payload.rule_type
    if payload.rule_config is not None:
        policy.rule_config = payload.rule_config
    if payload.compliance_framework is not None:
        policy.compliance_framework = payload.compliance_framework
    if payload.is_active is not None:
        policy.is_active = payload.is_active

    await db.commit()
    await db.refresh(policy)
    await invalidate_policy_cache(org_id)
    return PolicyResponse(
        id=policy.id,
        org_id=policy.org_id,
        agent_id=policy.agent_id,
        name=policy.name,
        rule_type=policy.rule_type,
        rule_config=policy.rule_config,
        compliance_framework=policy.compliance_framework,
        is_active=policy.is_active,
    )


@router.delete("/{policy_id}")
async def deactivate_policy(
    policy_id: uuid.UUID, auth: OrgAuth = OrgAdminDep, db: AsyncSession = Depends(get_db)
) -> dict:
    org_id = auth.org_id
    result = await db.execute(sa.select(Policy).where(Policy.id == policy_id).where(Policy.org_id == org_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    policy.is_active = False
    await db.commit()
    await invalidate_policy_cache(org_id)
    return {"status": "deactivated"}
