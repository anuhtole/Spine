"""End-to-end tests for the hook script.

We invoke hook.py as a real subprocess, feed it canned Claude-Code-shaped
JSON on stdin, and assert what it writes back on stdout. The Spine HTTP
call is mocked by monkeypatching urllib at the top of the script via
SPINE_TEST_RESPONSE env var (see _test_hook_runner below).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parent.parent / "hook.py"


def _run_hook(
    *,
    stdin_obj: dict,
    config: dict,
    mock_response: dict | None = None,
    fail_open: bool = False,
) -> tuple[int, str, str]:
    """Run hook.py as a subprocess with a temporary config and mocked HTTP."""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "config.json"
        cfg_path.write_text(json.dumps(config))

        env = dict(os.environ)
        env["SPINE_CONFIG_PATH"] = str(cfg_path)
        if fail_open:
            env["SPINE_FAIL_OPEN"] = "true"
        if mock_response is not None:
            env["SPINE_TEST_MOCK_RESPONSE"] = json.dumps(mock_response)
        else:
            env["SPINE_TEST_MOCK_RESPONSE"] = "__FAIL__"

        # The runner: a small wrapper script that monkeypatches urllib.request
        # before invoking hook.main. This lets us avoid any real network call.
        # Mock response is passed via env var to avoid quoting/escaping issues.
        runner = """
import json, os, sys
sys.path.insert(0, %r)

raw = os.environ.get("SPINE_TEST_MOCK_RESPONSE", "")
if raw == "__FAIL__":
    import urllib.error, urllib.request
    def boom(*a, **kw):
        raise urllib.error.URLError("no network in test")
    urllib.request.urlopen = boom
elif raw:
    mock_resp = json.loads(raw)
    import urllib.request
    class _FakeResp:
        def __init__(self, body): self._body = body
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return self._body
    def fake_urlopen(req, timeout=None, **kw):
        return _FakeResp(json.dumps(mock_resp).encode())
    urllib.request.urlopen = fake_urlopen

import hook
sys.exit(hook.main())
""" % (str(HOOK_PATH.parent),)
        proc = subprocess.run(
            [sys.executable, "-c", runner],
            input=json.dumps(stdin_obj),
            text=True,
            capture_output=True,
            env=env,
            timeout=10,
        )
        return proc.returncode, proc.stdout, proc.stderr


def _base_cfg() -> dict:
    return {
        "base_url": "http://test.invalid",
        "org_key": "spine_test",
        "agent_id": "11111111-1111-1111-1111-111111111111",
        "fail_closed": True,
        "timeout_seconds": 5,
        "debug": False,
    }


def test_allowed_response_exits_silently():
    rc, out, _ = _run_hook(
        stdin_obj={
            "tool_name": "Read",
            "tool_input": {"file_path": "/src/auth/login.ts"},
            "cwd": "/tmp",
        },
        config=_base_cfg(),
        mock_response={
            "allowed": True,
            "decision": "allowed",
            "reason": "ok",
            "audit_event_id": "a-uuid",
            "request_id": "r",
        },
    )
    assert rc == 0
    assert out.strip() == ""  # silent allow


def test_blocked_response_emits_block_json():
    rc, out, _ = _run_hook(
        stdin_obj={
            "tool_name": "Read",
            "tool_input": {"file_path": "/etc/secrets/.env"},
            "cwd": "/tmp",
        },
        config=_base_cfg(),
        mock_response={
            "allowed": False,
            "decision": "blocked",
            "reason": "No matching policy",
            "audit_event_id": "a-uuid",
            "request_id": "r",
        },
    )
    assert rc == 0
    body = json.loads(out)
    assert body["decision"] == "block"
    assert "No matching policy" in body["reason"]
    # Also check the newer Claude Code hookSpecificOutput shape:
    hso = body["hookSpecificOutput"]
    assert hso["permissionDecision"] == "deny"


def test_drift_block_includes_drift_score_in_reason():
    rc, out, _ = _run_hook(
        stdin_obj={
            "tool_name": "Read",
            "tool_input": {"file_path": "/x"},
            "cwd": "/tmp",
        },
        config=_base_cfg(),
        mock_response={
            "allowed": False,
            "decision": "blocked",
            "reason": "Session drift threshold exceeded (0.72 >= 0.60)",
            "audit_event_id": "a-uuid",
            "request_id": "r",
            "drift_score": 0.72,
        },
    )
    assert rc == 0
    body = json.loads(out)
    assert "0.72" in body["reason"]


def test_fail_closed_blocks_when_spine_unreachable():
    rc, out, _ = _run_hook(
        stdin_obj={
            "tool_name": "Read",
            "tool_input": {"file_path": "/x"},
            "cwd": "/tmp",
        },
        config=_base_cfg(),
        mock_response=None,  # simulate network failure
    )
    assert rc == 0
    body = json.loads(out)
    assert body["decision"] == "block"
    assert "fail-closed" in body["reason"].lower() or "unreachable" in body["reason"].lower()


def test_fail_open_allows_when_spine_unreachable():
    cfg = _base_cfg()
    cfg["fail_closed"] = False
    rc, out, _ = _run_hook(
        stdin_obj={
            "tool_name": "Read",
            "tool_input": {"file_path": "/x"},
            "cwd": "/tmp",
        },
        config=cfg,
        mock_response=None,
        fail_open=True,
    )
    assert rc == 0
    assert out.strip() == ""


def test_missing_agent_id_blocks_in_fail_closed():
    cfg = _base_cfg()
    cfg["agent_id"] = ""
    rc, out, _ = _run_hook(
        stdin_obj={"tool_name": "Read", "tool_input": {"file_path": "/x"}},
        config=cfg,
        mock_response={"allowed": True},  # never reached
    )
    assert rc == 0
    body = json.loads(out)
    assert body["decision"] == "block"
    assert "agent_id" in body["reason"].lower()


def test_session_id_file_is_picked_up_from_cwd(tmp_path):
    sf = tmp_path / ".spine" / "session_id"
    sf.parent.mkdir()
    sid = "22222222-2222-2222-2222-222222222222"
    sf.write_text(sid)

    # We don't have a way to inspect the actual body sent, but we can confirm
    # the hook doesn't error when a valid session_id file is present.
    rc, out, _ = _run_hook(
        stdin_obj={
            "tool_name": "Read",
            "tool_input": {"file_path": "/x"},
            "cwd": str(tmp_path),
        },
        config=_base_cfg(),
        mock_response={
            "allowed": True,
            "decision": "allowed",
            "reason": "ok",
            "audit_event_id": "a",
            "request_id": "r",
            "session_id": sid,
            "drift_score": 0.0,
        },
    )
    assert rc == 0
    assert out.strip() == ""
