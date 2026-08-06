"""Map Claude Code tool calls to Spine intercept fields.

Claude Code's PreToolUse hook sends JSON with at least `tool_name` and
`tool_input`. We translate this into Spine's (action_type, target_resource)
pair so existing policies (action_types + target_resource_regex) keep working.
"""

from __future__ import annotations

import json
from typing import Any

# Tool name aliases for policy authoring convenience. The lower-case key is the
# Claude Code tool name; the value is what we send to Spine as `action_type`.
ACTION_TYPE_ALIASES: dict[str, str] = {
    "read": "read",
    "write": "write",
    "edit": "edit",
    "multiedit": "edit",
    "bash": "exec",
    "shell": "exec",
    "run_terminal_cmd": "exec",
    "glob": "glob",
    "grep": "grep",
    "ls": "list",
    "webfetch": "http:GET",
    "websearch": "search",
    "notebookedit": "edit",
    "notebookread": "read",
    "task": "subagent",
    "todowrite": "todo",
    "exitplanmode": "plan",
}

# Param keys that commonly hold a path / URL / command (in priority order).
_TARGET_KEYS: tuple[str, ...] = (
    "file_path",
    "path",
    "filePath",
    "notebook_path",
    "url",
    "command",
    "pattern",
    "query",
    "prompt",
)


def normalize_action_type(tool_name: str) -> str:
    name = (tool_name or "").strip()
    if not name:
        return "unknown"
    if name.startswith("mcp__"):
        # Keep MCP tool calls structured: mcp:<server>:<tool>
        parts = name.split("__")
        if len(parts) >= 3:
            return f"mcp:{parts[1]}:{parts[2]}"
        return f"mcp:{name[5:]}"
    return ACTION_TYPE_ALIASES.get(name.lower(), name.lower())[:100]


def target_from_input(tool_input: Any) -> str | None:
    """Extract a single target_resource string from the tool input.

    Falls back to a stringified JSON snippet so policies can at least match
    on some structure when a tool doesn't use one of the well-known keys.
    """
    if tool_input is None:
        return None
    if isinstance(tool_input, str):
        return tool_input[:2048]
    if not isinstance(tool_input, dict):
        try:
            return json.dumps(tool_input, default=str)[:2048]
        except Exception:
            return str(tool_input)[:2048]

    for key in _TARGET_KEYS:
        if key in tool_input and tool_input[key] is not None:
            val = str(tool_input[key]).strip()
            if val:
                return val[:2048]
    # Fallback: serialize the whole input for transparency in the audit log.
    try:
        s = json.dumps(tool_input, default=str)
        return s[:2048]
    except Exception:
        return str(tool_input)[:2048]


def build_intercept_body(
    *,
    agent_id: str,
    tool_name: str,
    tool_input: Any,
    session_id: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "agent_id": agent_id,
        "action": {
            "action_type": normalize_action_type(tool_name),
            "target_resource": target_from_input(tool_input),
            "metadata": {
                "claude_code": {
                    "tool_name": str(tool_name or "")[:100],
                }
            },
        },
    }
    if session_id:
        body["session_id"] = session_id
    if request_id:
        body["correlation"] = {"request_id": request_id}
    return body
