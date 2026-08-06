from __future__ import annotations

import hmac
import json
from typing import Any

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from spine.config.settings import settings
from spine.models.webhook import Webhook


def _should_send(events: list[str] | None, decision: str) -> bool:
    if not events:
        return True
    return f"decision:{decision}" in set(events) or "decision:*" in set(events)


def _should_send_plan_drift(events: list[str] | None) -> bool:
    if not events:
        return True
    ev = set(events)
    return "decision:plan_drift" in ev or "decision:*" in ev or "plan.drift" in ev or "spine.plan.drift" in ev


def _sign_hex_key(hex_key: str, body_bytes: bytes) -> str:
    key = bytes.fromhex(hex_key)
    return hmac.new(key, body_bytes, "sha256").hexdigest()


# Reused across calls so we keep the connection pool / TCP-TLS state warm.
# httpx.AsyncClient is safe to share across coroutines.
_async_client: httpx.AsyncClient | None = None


def _get_async_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(timeout=settings.webhook_timeout_seconds)
    return _async_client


async def dispatch_intercept_event(db: AsyncSession, *, org_id, payload: dict[str, Any]) -> None:
    decision = str(payload.get("decision", ""))
    result = await db.execute(sa.select(Webhook).where(Webhook.org_id == org_id).where(Webhook.is_active.is_(True)))
    hooks = list(result.scalars().all())
    if not hooks:
        return

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    client = _get_async_client()
    for wh in hooks:
        if not _should_send(wh.events, decision):
            continue
        signature = _sign_hex_key(wh.hmac_key, body)
        headers = {
            "content-type": "application/json",
            "X-Spine-Event": "spine.intercept",
            "X-Spine-Signature": f"v1={signature}",
        }
        try:
            await client.post(wh.url, content=body, headers=headers)
        except Exception:
            # swallow - webhook failures must not take down the control plane
            continue


def dispatch_plan_drift_event_sync(session, *, org_id, payload: dict[str, Any]) -> None:
    """Dispatch a spine.plan.drift webhook from the Celery worker (sync)."""
    hooks = list(
        session.execute(sa.select(Webhook).where(Webhook.org_id == org_id).where(Webhook.is_active.is_(True)))
        .scalars()
        .all()
    )
    if not hooks:
        return

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    with httpx.Client(timeout=settings.webhook_timeout_seconds) as client:
        for wh in hooks:
            if not _should_send_plan_drift(wh.events):
                continue
            signature = _sign_hex_key(wh.hmac_key, body)
            headers = {
                "content-type": "application/json",
                "X-Spine-Event": "spine.plan.drift",
                "X-Spine-Signature": f"v1={signature}",
            }
            try:
                client.post(wh.url, content=body, headers=headers)
            except Exception:
                continue
