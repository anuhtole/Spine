import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import OrgIdDep, get_db
from spine.config.settings import settings
from spine.core.event_bus import subscribe_org_events
from spine.core.redaction import api_safe_audit_metadata
from spine.models.audit_event import AuditEvent
from spine.schemas.audit import AuditEventResponse
from spine.schemas.events import SpineStreamEvent

router = APIRouter()


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def _stream_org_activity(org_id: uuid.UUID) -> AsyncIterator[str]:
    connected = SpineStreamEvent(
        type="connected",
        org_id=org_id,
        ts=datetime.now(timezone.utc),
        data={"org_id": str(org_id)},
    )
    yield _format_sse("connected", connected.model_dump(mode="json"))

    subscriber = subscribe_org_events(org_id)
    next_event_task: asyncio.Task | None = asyncio.create_task(subscriber.__anext__())
    heartbeat_interval = max(5, settings.sse_heartbeat_seconds)

    try:
        while True:
            assert next_event_task is not None
            done, _pending = await asyncio.wait(
                {next_event_task},
                timeout=heartbeat_interval,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                hb = SpineStreamEvent(
                    type="heartbeat",
                    org_id=org_id,
                    ts=datetime.now(timezone.utc),
                    data={},
                )
                yield _format_sse("heartbeat", hb.model_dump(mode="json"))
                continue

            try:
                msg = next_event_task.result()
            except StopAsyncIteration:
                break
            next_event_task = asyncio.create_task(subscriber.__anext__())
            yield _format_sse(msg.type, msg.model_dump(mode="json"))
    finally:
        if next_event_task and not next_event_task.done():
            next_event_task.cancel()
        await subscriber.aclose()


@router.get("/stream")
async def stream_audit_activity(org_id: uuid.UUID = OrgIdDep) -> StreamingResponse:
    if not settings.sse_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSE disabled")

    return StreamingResponse(
        _stream_org_activity(org_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("", response_model=list[AuditEventResponse])
async def list_audit_events(
    agent_id: uuid.UUID | None = None,
    limit: int = 100,
    org_id: uuid.UUID = OrgIdDep,
    db: AsyncSession = Depends(get_db),
) -> list[AuditEventResponse]:
    limit = max(1, min(limit, 500))

    stmt = sa.select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit)
    stmt = stmt.where(AuditEvent.org_id == org_id)
    if agent_id:
        stmt = stmt.where(AuditEvent.agent_id == agent_id)

    result = await db.execute(stmt)
    events = list(result.scalars().all())
    return [
        AuditEventResponse(
            id=e.id,
            agent_id=e.agent_id,
            org_id=e.org_id,
            action_type=e.action_type,
            target_resource=e.target_resource,
            policy_decision=e.policy_decision,
            policy_id=e.policy_id,
            metadata=api_safe_audit_metadata(e.metadata_),
            timestamp=e.timestamp,
        )
        for e in events
    ]


@router.get("/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: uuid.UUID, org_id: uuid.UUID = OrgIdDep, db: AsyncSession = Depends(get_db)
) -> AuditEventResponse:
    result = await db.execute(sa.select(AuditEvent).where(AuditEvent.id == event_id).where(AuditEvent.org_id == org_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found")
    return AuditEventResponse(
        id=event.id,
        agent_id=event.agent_id,
        org_id=event.org_id,
        action_type=event.action_type,
        target_resource=event.target_resource,
        policy_decision=event.policy_decision,
        policy_id=event.policy_id,
        metadata=api_safe_audit_metadata(event.metadata_),
        timestamp=event.timestamp,
    )
