import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.models.idempotency import IdempotencyKey, fingerprint_json


async def get_cached_json(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    idempotency_key: str,
    request_obj: dict[str, Any],
) -> dict[str, Any] | None:
    fp = fingerprint_json(request_obj)

    res = await db.execute(
        sa.select(IdempotencyKey)
        .where(IdempotencyKey.org_id == org_id)
        .where(IdempotencyKey.idempotency_key == idempotency_key)
    )
    row = res.scalar_one_or_none()
    if not row:
        return None
    if row.request_fingerprint != fp:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency-Key conflict")
    return row.response_json


async def save_json(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    idempotency_key: str,
    request_obj: dict[str, Any],
    response_obj: dict[str, Any],
    status_code: int = 200,
) -> None:
    fp = fingerprint_json(request_obj)
    row = IdempotencyKey(
        org_id=org_id,
        idempotency_key=idempotency_key,
        request_fingerprint=fp,
        status_code=status_code,
        response_json=response_obj,
    )
    db.add(row)
    await db.commit()
