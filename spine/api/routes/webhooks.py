import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import OrgAdminDep, OrgAuth, OrgIdDep, get_db
from spine.config.settings import settings
from spine.core.url_validation import validate_public_webhook_url
from spine.models.webhook import Webhook
from spine.schemas.webhook import WebhookCreate, WebhookCreatedResponse, WebhookResponse

router = APIRouter()


@router.post("", response_model=WebhookCreatedResponse)
async def create_webhook(
    payload: WebhookCreate, auth: OrgAuth = OrgAdminDep, db: AsyncSession = Depends(get_db)
) -> WebhookCreatedResponse:
    org_id = auth.org_id
    if settings.block_webhook_private_urls:
        try:
            validate_public_webhook_url(str(payload.url), require_https=settings.is_production)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    hmac_key = Webhook.new_hmac_key()
    wh = Webhook(org_id=org_id, url=str(payload.url), hmac_key=hmac_key, name=payload.name, events=payload.events)
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return WebhookCreatedResponse(
        id=wh.id,
        org_id=wh.org_id,
        url=wh.url,
        name=wh.name,
        events=wh.events,
        is_active=wh.is_active,
        hmac_key=hmac_key,
    )


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(org_id: uuid.UUID = OrgIdDep, db: AsyncSession = Depends(get_db)) -> list[WebhookResponse]:
    res = await db.execute(sa.select(Webhook).where(Webhook.org_id == org_id))
    rows = list(res.scalars().all())
    return [
        WebhookResponse(id=w.id, org_id=w.org_id, url=w.url, name=w.name, events=w.events, is_active=w.is_active)
        for w in rows
    ]


@router.delete("/{webhook_id}")
async def deactivate_webhook(
    webhook_id: uuid.UUID, org_id: uuid.UUID = OrgIdDep, db: AsyncSession = Depends(get_db)
) -> dict:
    res = await db.execute(sa.select(Webhook).where(Webhook.id == webhook_id).where(Webhook.org_id == org_id))
    wh = res.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    wh.is_active = False
    await db.commit()
    return {"status": "deactivated"}
