from __future__ import annotations

import uuid
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from spine.core.audit_logger import _canonical_json, _hash_hex
from spine.models.audit_event import AuditEvent


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    org_id: uuid.UUID
    checked: int
    first_bad_sequence: int | None
    error: str | None = None


def _recompute_event_hash(e: AuditEvent) -> str:
    payload = {
        "org_id": str(e.org_id),
        "agent_id": str(e.agent_id),
        "sequence": e.sequence,
        "prev_hash": e.prev_hash,
        "action_type": e.action_type,
        "target_resource": e.target_resource,
        "decision": e.policy_decision,
        "policy_id": str(e.policy_id) if e.policy_id else None,
        "metadata": e.metadata_ or {},
    }
    # Match writer: only include session_id when present. Pre-0010 rows
    # have session_id=NULL and recompute identically (no key in canonical JSON).
    if e.session_id is not None:
        payload["session_id"] = str(e.session_id)
    return _hash_hex(_canonical_json(payload))


async def verify_org_chain(db: AsyncSession, *, org_id: uuid.UUID, limit: int = 50_000) -> VerifyResult:
    res = await db.execute(
        sa.select(AuditEvent).where(AuditEvent.org_id == org_id).order_by(AuditEvent.sequence.asc()).limit(limit)
    )
    events = list(res.scalars().all())
    if not events:
        return VerifyResult(ok=True, org_id=org_id, checked=0, first_bad_sequence=None)

    prev: str | None = None
    expected_seq = 1
    for e in events:
        if e.sequence != expected_seq:
            return VerifyResult(
                ok=False,
                org_id=org_id,
                checked=expected_seq - 1,
                first_bad_sequence=e.sequence,
                error="sequence_mismatch",
            )
        if e.prev_hash != prev:
            return VerifyResult(
                ok=False,
                org_id=org_id,
                checked=expected_seq - 1,
                first_bad_sequence=e.sequence,
                error="prev_hash_mismatch",
            )
        h = _recompute_event_hash(e)
        if h != (e.event_hash or ""):
            return VerifyResult(
                ok=False,
                org_id=org_id,
                checked=expected_seq - 1,
                first_bad_sequence=e.sequence,
                error="event_hash_mismatch",
            )
        prev = e.event_hash
        expected_seq += 1

    return VerifyResult(ok=True, org_id=org_id, checked=len(events), first_bad_sequence=None)
