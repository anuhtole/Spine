"""Redact sensitive values before SSE, API responses, logs, and LLM prompts."""

from __future__ import annotations

import json
import re
from typing import Any

_REDACTED = "[REDACTED]"
_TRUNCATED = "[TRUNCATED]"

_SENSITIVE_KEY = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|auth|bearer|"
    r"cookie|session|ssn|social|credential|private[_-]?key|hmac|"
    r"access[_-]?key|refresh[_-]?key|client[_-]?secret)",
    re.IGNORECASE,
)

_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")
_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b", re.IGNORECASE)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_LONG_HEX = re.compile(r"\b[a-fA-F0-9]{32,}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

_DEFAULT_MAX_DEPTH = 10
_DEFAULT_MAX_KEYS = 64
_DEFAULT_METADATA_BYTES = 8192
_DEFAULT_REASONING_CHARS = 500
_STREAM_REASONING_CHARS = 240


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY.search(key))


def redact_string(value: str, *, max_len: int | None = None) -> str:
    if not value:
        return value
    out = value
    out = _EMAIL.sub(_REDACTED, out)
    out = _BEARER.sub("Bearer [REDACTED]", out)
    out = _JWT.sub(_REDACTED, out)
    out = _SSN.sub(_REDACTED, out)
    out = _CC.sub(_REDACTED, out)
    out = _LONG_HEX.sub(_REDACTED, out)
    if max_len is not None and len(out) > max_len:
        return out[:max_len] + f"… ({_TRUNCATED})"
    return out


def redact_value(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = _DEFAULT_MAX_DEPTH,
    max_keys: int = _DEFAULT_MAX_KEYS,
) -> Any:
    if depth > max_depth:
        return _TRUNCATED
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return redact_string(value, max_len=2048)
    if isinstance(value, (list, tuple)):
        return [redact_value(v, depth=depth + 1, max_depth=max_depth, max_keys=max_keys) for v in value[:max_keys]]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for i, (k, v) in enumerate(value.items()):
            if i >= max_keys:
                out["_truncated_keys"] = len(value) - max_keys
                break
            key = str(k)
            if _is_sensitive_key(key):
                out[key] = _REDACTED
            else:
                out[key] = redact_value(v, depth=depth + 1, max_depth=max_depth, max_keys=max_keys)
        return out
    return redact_string(str(value), max_len=512)


def cap_metadata_size(metadata: dict[str, Any] | None, *, max_bytes: int = _DEFAULT_METADATA_BYTES) -> dict[str, Any]:
    if not metadata:
        return {}
    redacted = redact_value(metadata)
    try:
        encoded = json.dumps(redacted, default=str)
    except (TypeError, ValueError):
        return {"_error": "metadata_not_serializable"}
    if len(encoded) <= max_bytes:
        return redacted if isinstance(redacted, dict) else {}
    return {
        "_truncated": True,
        "_preview": redact_string(encoded[: max_bytes // 2]),
    }


def stream_safe_audit_payload(event) -> dict[str, Any]:
    meta = cap_metadata_size(event.metadata_)
    return {
        "id": str(event.id),
        "agent_id": str(event.agent_id),
        "org_id": str(event.org_id),
        "action_type": event.action_type,
        "target_resource": redact_string(event.target_resource or "", max_len=256) or None,
        "policy_decision": event.policy_decision,
        "policy_id": str(event.policy_id) if event.policy_id else None,
        "metadata": meta,
        "sequence": event.sequence,
    }


def stream_safe_plan_payload(*, evaluation, drift_score: float, session_id) -> dict[str, Any]:
    """Plan-bound evaluation payload for SSE. Reasoning is redacted/truncated."""
    return {
        "id": str(evaluation.id),
        "org_id": str(evaluation.org_id),
        "agent_id": str(evaluation.agent_id),
        "session_id": str(session_id),
        "audit_event_id": str(evaluation.audit_event_id),
        "alignment": evaluation.alignment,
        "confidence": evaluation.confidence,
        "drift_contribution": evaluation.drift_contribution,
        "drift_score": float(drift_score),
        "reasoning": redact_string(evaluation.reasoning or "", max_len=_STREAM_REASONING_CHARS),
        "approval_id": str(evaluation.approval_id) if evaluation.approval_id else None,
    }


def api_safe_audit_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    return cap_metadata_size(metadata)


def api_safe_reasoning(reasoning: str | None, *, max_len: int = _DEFAULT_REASONING_CHARS) -> str:
    return redact_string(reasoning or "", max_len=max_len)
