"""Helpers to block tool execution when Spine denies an action."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from spine_sdk.client import SpineClient


class SpineBlockedError(RuntimeError):
    def __init__(self, *, decision: str | None, reason: str | None, payload: dict[str, Any]) -> None:
        self.decision = decision
        self.reason = reason
        self.payload = payload
        msg = reason or decision or "blocked"
        super().__init__(f"Spine blocked action: {msg}")


def require_allowed(
    client: SpineClient,
    *,
    agent_id: uuid.UUID,
    action_type: str,
    target_resource: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call intercept; raise SpineBlockedError if not allowed. Returns JSON body on success."""
    res = client.intercept(
        agent_id=agent_id,
        action_type=action_type,
        target_resource=target_resource,
        metadata=metadata,
    )
    body = res.json or {}
    if res.status_code != 200 or not body.get("allowed", False):
        raise SpineBlockedError(
            decision=body.get("decision"),
            reason=body.get("reason"),
            payload=body,
        )
    return body


def guard_tool(
    client: SpineClient,
    *,
    agent_id: uuid.UUID,
    action_type: str,
    target_resource_for_action: Callable[..., str | None],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: run intercept before the wrapped callable."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            target = target_resource_for_action(*args, **kwargs)
            require_allowed(
                client,
                agent_id=agent_id,
                action_type=action_type,
                target_resource=target,
            )
            return fn(*args, **kwargs)

        return wrapped

    return decorator
