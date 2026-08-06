import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import ApprovalOrgDep, get_db
from spine.core.approval_grants import create_grant_from_approval, proposed_to_action
from spine.core.event_bus import approval_payload, publish_event_async
from spine.models.approval import Approval
from spine.schemas.approval import ApprovalCreate, ApprovalDecision, ApprovalResponse

router = APIRouter()


@router.post("", response_model=ApprovalResponse)
async def create_approval(
    payload: ApprovalCreate,
    org_id: uuid.UUID = ApprovalOrgDep,
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    if payload.proposed.agent_id != payload.agent_id:
        raise HTTPException(status_code=400, detail="agent_id must match proposed.agent_id")
    a = Approval(
        org_id=org_id,
        agent_id=payload.agent_id,
        proposed=payload.proposed.model_dump(mode="json"),
        status="pending",
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    action = proposed_to_action(a.proposed)
    await publish_event_async(
        org_id,
        "approval",
        approval_payload(
            approval_id=a.id,
            org_id=org_id,
            agent_id=a.agent_id,
            status="pending",
            audit_event_id=a.audit_event_id,
            action_type=action.action_type if action else None,
            target_resource=action.target_resource if action else None,
        ),
    )
    return ApprovalResponse(
        id=a.id,
        org_id=a.org_id,
        agent_id=a.agent_id,
        status=a.status,
        decision=a.decision,
        decided_by=a.decided_by,
        audit_event_id=a.audit_event_id,
        proposed=a.proposed,
    )


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    org_id: uuid.UUID = ApprovalOrgDep,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ApprovalResponse]:
    stmt = sa.select(Approval).where(Approval.org_id == org_id)
    if status_filter:
        stmt = stmt.where(Approval.status == status_filter)
    res = await db.execute(stmt.order_by(Approval.created_at.desc()))
    rows = list(res.scalars().all())
    return [
        ApprovalResponse(
            id=r.id,
            org_id=r.org_id,
            agent_id=r.agent_id,
            status=r.status,
            decision=r.decision,
            decided_by=r.decided_by,
            audit_event_id=r.audit_event_id,
            proposed=r.proposed,
        )
        for r in rows
    ]


@router.post("/{approval_id}/decide", response_model=ApprovalResponse)
async def decide_approval(
    approval_id: uuid.UUID,
    payload: ApprovalDecision,
    org_id: uuid.UUID = ApprovalOrgDep,
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    res = await db.execute(sa.select(Approval).where(Approval.id == approval_id).where(Approval.org_id == org_id))
    a = res.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    if a.status != "pending":
        raise HTTPException(status_code=409, detail="Approval is not pending")

    a.status = "approved" if payload.action == "approve" else "rejected"
    a.decision = a.status
    a.decided_by = payload.decided_by
    a.decided_at = datetime.now(timezone.utc)

    action = proposed_to_action(a.proposed)
    if payload.action == "approve" and action:
        await create_grant_from_approval(
            db,
            org_id=a.org_id,
            agent_id=a.agent_id,
            approval_id=a.id,
            action=action,
            decided_by=payload.decided_by,
        )

    await db.commit()
    await db.refresh(a)

    act = proposed_to_action(a.proposed)
    await publish_event_async(
        org_id,
        "approval",
        approval_payload(
            approval_id=a.id,
            org_id=a.org_id,
            agent_id=a.agent_id,
            status=a.status,
            audit_event_id=a.audit_event_id,
            action_type=act.action_type if act else None,
            target_resource=act.target_resource if act else None,
            reason=a.decision,
        ),
    )

    return ApprovalResponse(
        id=a.id,
        org_id=a.org_id,
        agent_id=a.agent_id,
        status=a.status,
        decision=a.decision,
        decided_by=a.decided_by,
        audit_event_id=a.audit_event_id,
        proposed=a.proposed,
    )
