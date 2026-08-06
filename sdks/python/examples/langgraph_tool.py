"""
Example pattern: wrap an existing tool function with a Spine intercept check.

This file is not executed by the repo tests; it is a copy/paste template.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from spine_sdk import SpineClient


def guard_tool(
    client: SpineClient,
    *,
    agent_id: uuid.UUID,
    action_type: str,
    target_resource_for_action: Callable[..., str | None],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator factory: returns a decorator that checks intercept before calling the wrapped tool.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            target = target_resource_for_action(*args, **kwargs)
            res = client.intercept(
                agent_id=agent_id,
                action_type=action_type,
                target_resource=target,
            )
            if res.status_code != 200 or not res.json.get("allowed", False):
                raise RuntimeError(f"Spine blocked tool call: {res.json}")
            return fn(*args, **kwargs)

        return wrapped

    return decorator


# Example:
# client = SpineClient(base_url="http://localhost:8000", org_key="spine_...", http_client=httpx.Client())
