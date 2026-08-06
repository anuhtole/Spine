#!/usr/bin/env python3
"""Spine PreToolUse hook for Claude Code.

Installation puts this at ~/.spine/hook.py and adds the following to
~/.claude/settings.json:

    {
      "hooks": {
        "PreToolUse": [
          {
            "matcher": "*",
            "hooks": [
              { "type": "command", "command": "python3 ~/.spine/hook.py" }
            ]
          }
        ]
      }
    }

For each tool call the hook:
  1. Reads JSON from stdin (Claude Code's PreToolUse payload).
  2. Builds a Spine /v1/intercept request body.
  3. POSTs to Spine with the configured org key.
  4. Emits {"decision":"block","reason":...} on stdout to block, or exits 0
     with no stdout to allow.

Fail-closed by default: if Spine is unreachable or returns an error, the
tool is blocked. Set SPINE_FAIL_OPEN=true in the env for dev only.

Config is read from ~/.spine/config.json:
    {
      "base_url": "https://api.demo.spinelayer.com",
      "org_key": "spine_...",
      "agent_id": "uuid",
      "fail_closed": true,
      "timeout_seconds": 10,
      "debug": false
    }

Per-project session ID is read from <project>/.spine/session_id when present.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

# Allow `python3 hook.py` from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tool_mapping import build_intercept_body  # noqa: E402

CONFIG_PATH = Path(os.environ.get("SPINE_CONFIG_PATH", str(Path.home() / ".spine" / "config.json")))
DEFAULT_TIMEOUT = 10.0
SESSION_FILE_REL = ".spine/session_id"


def _debug(cfg: dict, msg: str) -> None:
    if cfg.get("debug"):
        sys.stderr.write(f"[spine-hook] {msg}\n")


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return {}


def _resolve_session_id(cwd: str | None) -> str | None:
    """Read .spine/session_id from the project root, if it exists."""
    if not cwd:
        return None
    sf = Path(cwd) / SESSION_FILE_REL
    if not sf.exists():
        return None
    try:
        sid = sf.read_text().strip()
        # Basic UUID sanity check.
        uuid.UUID(sid)
        return sid
    except Exception:
        return None


def _post_intercept(cfg: dict, body: dict[str, Any]) -> tuple[bool, dict[str, Any] | None, str | None]:
    """POST to Spine. Returns (ok, response_json, error_msg)."""
    base = (cfg.get("base_url") or "").rstrip("/")
    org_key = cfg.get("org_key") or ""
    if not base or not org_key:
        return False, None, "spine config missing base_url or org_key"

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/v1/intercept",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Org-Key": org_key,
            "X-Request-ID": str(uuid.uuid4()),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", DEFAULT_TIMEOUT)) as resp:
            raw = resp.read()
            try:
                return True, json.loads(raw), None
            except Exception:
                return False, None, f"non-JSON response: {raw[:200]!r}"
    except urllib.error.HTTPError as exc:
        body_text = ""
        try:
            body_text = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return False, None, f"HTTP {exc.code}: {body_text}"
    except urllib.error.URLError as exc:
        return False, None, f"network error: {exc.reason}"
    except Exception as exc:
        return False, None, f"unexpected error: {exc}"


def _emit_block(reason: str) -> None:
    """Emit a PreToolUse block response on stdout and exit 0."""
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        # Older/alternate Claude Code shape (decision/reason). Including both
        # is harmless and increases compatibility across hook versions.
        "decision": "block",
        "reason": reason,
    }
    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()


def main() -> int:
    cfg = _load_config()
    fail_closed = cfg.get("fail_closed", True)
    fail_open_env = os.environ.get("SPINE_FAIL_OPEN", "").lower() in {"1", "true", "yes"}
    if fail_open_env:
        fail_closed = False

    try:
        raw_in = sys.stdin.read()
    except Exception:
        # If we can't even read stdin, fail-closed is the safe default.
        if fail_closed:
            _emit_block("Spine hook: could not read tool call payload")
            return 0
        return 0

    try:
        payload = json.loads(raw_in) if raw_in.strip() else {}
    except Exception as exc:
        _debug(cfg, f"non-JSON stdin: {exc}; raw={raw_in[:200]!r}")
        if fail_closed:
            _emit_block("Spine hook: malformed tool call payload")
            return 0
        return 0

    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    cwd = payload.get("cwd") or os.getcwd()
    cc_session_id = payload.get("session_id") or payload.get("sessionId")

    agent_id = cfg.get("agent_id") or ""
    if not agent_id:
        if fail_closed:
            _emit_block("Spine hook: agent_id not configured in ~/.spine/config.json")
            return 0
        return 0

    spine_session_id = _resolve_session_id(cwd)
    request_id = str(cc_session_id) if cc_session_id else None

    body = build_intercept_body(
        agent_id=agent_id,
        tool_name=tool_name,
        tool_input=tool_input,
        session_id=spine_session_id,
        request_id=request_id,
    )
    _debug(
        cfg,
        f"intercept tool_name={tool_name!r} action_type={body['action']['action_type']!r} "
        f"target={body['action'].get('target_resource')!r} session_id={spine_session_id}",
    )

    t0 = time.time()
    ok, resp, err = _post_intercept(cfg, body)
    dt_ms = int((time.time() - t0) * 1000)

    if not ok:
        _debug(cfg, f"spine request failed in {dt_ms}ms: {err}")
        if fail_closed:
            _emit_block(f"Spine unreachable (fail-closed): {err}")
            return 0
        # fail-open: allow silently
        return 0

    assert resp is not None
    allowed = bool(resp.get("allowed"))
    decision = resp.get("decision", "unknown")
    reason = resp.get("reason", "")
    drift = resp.get("drift_score")
    audit_id = resp.get("audit_event_id", "")

    _debug(
        cfg,
        f"spine decision={decision} allowed={allowed} drift={drift} audit={audit_id} dt={dt_ms}ms",
    )

    if allowed:
        return 0

    # Build a useful block reason.
    parts = [reason or f"Spine {decision}"]
    if decision == "flagged" and resp.get("approval_id"):
        parts.append(f"(approval {resp['approval_id']} — approve in Spine dashboard)")
    if drift is not None:
        parts.append(f"[session drift {float(drift):.2f}]")
    _emit_block(" ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
