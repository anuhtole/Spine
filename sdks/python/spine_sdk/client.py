from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InterceptResult:
    status_code: int
    json: dict[str, Any]


class SpineClient:
    def __init__(
        self,
        *,
        base_url: str,
        org_key: str,
        http_client: httpx.Client,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._org_key = org_key
        self._http = http_client
        self._default_headers = default_headers or {}

    def _headers(self, request_id: str | None) -> dict[str, str]:
        h = {"X-Org-Key": self._org_key, **self._default_headers}
        if request_id:
            h["X-Request-ID"] = request_id
        return h

    def intercept(
        self,
        *,
        agent_id: uuid.UUID,
        action_type: str,
        target_resource: str | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        request_id: str | None = None,
    ) -> InterceptResult:
        correlation: dict[str, Any] = {}
        if trace_id:
            correlation["trace_id"] = trace_id
        if span_id:
            correlation["span_id"] = span_id
        if request_id:
            correlation["request_id"] = request_id

        body: dict[str, Any] = {
            "agent_id": str(agent_id),
            "action": {
                "action_type": action_type,
                "target_resource": target_resource,
                "metadata": metadata,
            },
        }
        if correlation:
            body["correlation"] = correlation

        r = self._http.post(
            f"{self._base}/v1/intercept",
            headers=self._headers(request_id),
            json=body,
        )
        return InterceptResult(status_code=r.status_code, json=r.json() if r.content else {})
