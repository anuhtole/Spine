from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from spine.config.settings import settings
from spine.models.approval_grant import ApprovalGrant
from spine.schemas.intercept import AgentAction


def action_match_key(*, agent_id: uuid.UUID, action: AgentAction) -> str:
    target = (action.target_resource or "").strip()
    return f"{agent_id}|{action.action_type}|{target}"


async def find_active_grant(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    action: AgentAction,
) -> ApprovalGrant | None:
    key = action_match_key(agent_id=agent_id, action=action)
    now = datetime.now(timezone.utc)
    result = await session.execute(
        sa.select(ApprovalGrant)
        .where(ApprovalGrant.org_id == org_id)
        .where(ApprovalGrant.agent_id == agent_id)
        .where(ApprovalGrant.match_key == key)
        .where(ApprovalGrant.revoked_at.is_(None))
        .where(ApprovalGrant.expires_at > now)
        .order_by(ApprovalGrant.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_grant_from_approval(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    approval_id: uuid.UUID,
    action: AgentAction,
    decided_by: str,
) -> ApprovalGrant:
    ttl = max(60, settings.approval_grant_ttl_seconds)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    grant = ApprovalGrant(
        org_id=org_id,
        agent_id=agent_id,
        approval_id=approval_id,
        action_type=action.action_type,
        target_resource=action.target_resource,
        match_key=action_match_key(agent_id=agent_id, action=action),
        decided_by=decided_by,
        expires_at=expires_at,
    )
    session.add(grant)
    await session.flush()
    return grant


def proposed_to_action(proposed: dict) -> AgentAction | None:
    action = proposed.get("action")
    if not isinstance(action, dict):
        return None
    action_type = action.get("action_type")
    if not action_type or not isinstance(action_type, str):
        return None
    target = action.get("target_resource")
    target_resource = str(target) if target is not None else None
    metadata = action.get("metadata")
    meta = metadata if isinstance(metadata, dict) else None
    return AgentAction(action_type=action_type, target_resource=target_resource, metadata=meta)
