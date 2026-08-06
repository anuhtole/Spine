"""Sync audit logger for Celery workers."""

from __future__ import annotations

import hashlib
import json
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from spine.models.audit_event import AuditEvent


def _canonical_json(obj: dict | None) -> str:
    return json.dumps(obj or {}, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def _hash_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def log_event_sync(
    session: Session,
    *,
    agent_id: uuid.UUID,
    org_id: uuid.UUID,
    action_type: str,
    target_resource: str | None,
    decision: str,
    policy_id: uuid.UUID | None,
    metadata: dict | None,
    session_id: uuid.UUID | None = None,
) -> AuditEvent:
    if session.bind and session.bind.dialect.name == "postgresql":
        session.execute(sa.text("SELECT pg_advisory_xact_lock(hashtext(:k))").bindparams(k=str(org_id)))

    last = session.execute(
        sa.select(AuditEvent).where(AuditEvent.org_id == org_id).order_by(AuditEvent.sequence.desc()).limit(1)
    ).scalar_one_or_none()
    prev_hash = last.event_hash if last else None
    next_seq = (last.sequence + 1) if last else 1

    payload = {
        "org_id": str(org_id),
        "agent_id": str(agent_id),
        "sequence": next_seq,
        "prev_hash": prev_hash,
        "action_type": action_type,
        "target_resource": target_resource,
        "decision": decision,
        "policy_id": str(policy_id) if policy_id else None,
        "metadata": metadata or {},
    }
    if session_id is not None:
        payload["session_id"] = str(session_id)
    event_hash = _hash_hex(_canonical_json(payload))

    event = AuditEvent(
        agent_id=agent_id,
        org_id=org_id,
        action_type=action_type,
        target_resource=target_resource,
        policy_decision=decision,
        policy_id=policy_id,
        metadata_=metadata,
        sequence=next_seq,
        prev_hash=prev_hash,
        event_hash=event_hash,
        session_id=session_id,
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    from spine.core.event_bus import audit_event_payload, publish_event_sync

    publish_event_sync(org_id, "audit", audit_event_payload(event))

    return event
