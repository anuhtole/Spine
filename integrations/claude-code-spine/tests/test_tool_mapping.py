"""Unit tests for the Claude-Code → Spine field mapping."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the package importable from this tests/ subdirectory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tool_mapping import (  # noqa: E402
    build_intercept_body,
    normalize_action_type,
    target_from_input,
)


def test_normalize_action_type_aliases():
    assert normalize_action_type("Read") == "read"
    assert normalize_action_type("Bash") == "exec"
    assert normalize_action_type("WebFetch") == "http:GET"
    assert normalize_action_type("Glob") == "glob"
    assert normalize_action_type("Edit") == "edit"
    assert normalize_action_type("MultiEdit") == "edit"


def test_normalize_action_type_mcp_passthrough():
    assert normalize_action_type("mcp__slack__send_message") == "mcp:slack:send_message"
    assert normalize_action_type("mcp__github__create_pr") == "mcp:github:create_pr"


def test_target_from_input_path_keys():
    assert target_from_input({"file_path": "/x.ts"}) == "/x.ts"
    assert target_from_input({"path": "/y"}) == "/y"
    assert target_from_input({"url": "https://example.com"}) == "https://example.com"
    assert target_from_input({"command": "ls -la"}) == "ls -la"
    assert target_from_input({"pattern": "*.py"}) == "*.py"


def test_target_from_input_falls_back_to_json():
    out = target_from_input({"weird_key": "weird_value"})
    assert "weird_key" in out
    assert "weird_value" in out


def test_target_from_input_handles_none_and_string():
    assert target_from_input(None) is None
    assert target_from_input("just a string") == "just a string"


def test_build_intercept_body_includes_session_when_present():
    body = build_intercept_body(
        agent_id="agent-uuid",
        tool_name="Read",
        tool_input={"file_path": "/etc/secrets/.env"},
        session_id="session-uuid",
        request_id="req-1",
    )
    assert body["agent_id"] == "agent-uuid"
    assert body["action"]["action_type"] == "read"
    assert body["action"]["target_resource"] == "/etc/secrets/.env"
    assert body["session_id"] == "session-uuid"
    assert body["correlation"]["request_id"] == "req-1"
    # Metadata is bounded to the claude_code marker — no leakage of the input.
    assert body["action"]["metadata"]["claude_code"]["tool_name"] == "Read"


def test_build_intercept_body_omits_session_when_absent():
    body = build_intercept_body(
        agent_id="a",
        tool_name="Bash",
        tool_input={"command": "echo hi"},
        session_id=None,
        request_id=None,
    )
    assert "session_id" not in body
    assert "correlation" not in body
    assert body["action"]["action_type"] == "exec"
    assert body["action"]["target_resource"] == "echo hi"
