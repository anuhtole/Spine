#!/usr/bin/env python3
"""Spine session lifecycle CLI used by the Claude Code slash commands.

Usage:
  spine-session-cli.py start "<goal>"
  spine-session-cli.py end
  spine-session-cli.py status

Reads config from ~/.spine/config.json. Reads/writes session_id at
<cwd>/.spine/session_id so the hook can pick it up automatically.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("SPINE_CONFIG_PATH", str(Path.home() / ".spine" / "config.json")))
SESSION_FILE_REL = ".spine/session_id"


def _cfg() -> dict:
    if not CONFIG_PATH.exists():
        print(
            f"error: spine config not found at {CONFIG_PATH}\nrun integrations/claude-code-spine/install.sh first",
            file=sys.stderr,
        )
        sys.exit(2)
    cfg = json.loads(CONFIG_PATH.read_text())
    if not cfg.get("base_url") or not cfg.get("org_key") or not cfg.get("agent_id"):
        print("error: spine config is missing base_url / org_key / agent_id", file=sys.stderr)
        sys.exit(2)
    return cfg


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    cfg = _cfg()
    url = cfg["base_url"].rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Org-Key": cfg["org_key"],
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", 15)) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        except Exception:
            return exc.code, {"detail": str(exc)}
    except urllib.error.URLError as exc:
        print(f"error: spine unreachable: {exc.reason}", file=sys.stderr)
        sys.exit(2)


def _session_file() -> Path:
    p = Path.cwd() / SESSION_FILE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def cmd_start(args: list[str]) -> int:
    if not args:
        print('usage: spine-session-cli.py start "<goal>"', file=sys.stderr)
        return 2
    goal = " ".join(args).strip()
    if not goal:
        print("error: empty goal", file=sys.stderr)
        return 2

    cfg = _cfg()
    body = {
        "agent_id": cfg["agent_id"],
        "goal": goal,
        # Reasonable defaults; full plan declaration UI lands in the dashboard.
        "constraints": cfg.get("default_constraints", []),
        "expected_resources": cfg.get("default_expected_resources", []),
        "success_criteria": cfg.get("default_success_criteria"),
    }
    status, resp = _request("POST", "/v1/sessions", body)
    if status >= 300:
        print(f"error: POST /v1/sessions -> {status}: {resp}", file=sys.stderr)
        return 1
    sid = resp.get("id")
    if not sid:
        print(f"error: malformed response: {resp}", file=sys.stderr)
        return 1
    _session_file().write_text(sid)
    print(f"spine session started: {sid}")
    print(f"  goal: {goal}")
    print(f"  drift threshold (flag/block): {cfg.get('flag_threshold', 0.4)} / {cfg.get('block_threshold', 0.6)}")
    print(f"  session_id written to {_session_file()}")
    return 0


def cmd_end(_args: list[str]) -> int:
    sf = _session_file()
    if not sf.exists():
        print("no active spine session in this directory")
        return 0
    sid = sf.read_text().strip()
    status, resp = _request("POST", f"/v1/sessions/{sid}/end", {"status": "completed"})
    if status >= 300:
        print(f"error: end failed -> {status}: {resp}", file=sys.stderr)
        return 1
    print(f"spine session ended: {sid}")
    print(f"  final drift_score: {resp.get('drift_score'):.3f}")
    print(f"  evaluations:     {resp.get('evaluation_count')}")
    try:
        sf.unlink()
    except Exception:
        pass
    return 0


def cmd_status(_args: list[str]) -> int:
    sf = _session_file()
    if not sf.exists():
        print("no active spine session in this directory")
        return 0
    sid = sf.read_text().strip()
    status, resp = _request("GET", f"/v1/sessions/{sid}")
    if status >= 300:
        print(f"error: get failed -> {status}: {resp}", file=sys.stderr)
        return 1
    print(f"session: {sid}")
    print(f"  goal:           {resp.get('goal')}")
    print(f"  status:         {resp.get('status')}")
    print(f"  drift_score:    {resp.get('drift_score'):.3f}")
    print(f"  evaluations:    {resp.get('evaluation_count')}")
    if resp.get("constraints"):
        print("  constraints:")
        for c in resp["constraints"]:
            print(f"    - {c}")

    # Recent evaluations
    status2, evals = _request("GET", f"/v1/sessions/{sid}/evaluations?limit=5")
    if status2 < 300 and isinstance(evals, list) and evals:
        print("  recent verdicts:")
        for e in evals[-5:]:
            print(
                f"    [{e.get('alignment'):<9}] drift+={e.get('drift_contribution'):.2f} "
                f"-> {e.get('drift_score_after'):.3f}  {e.get('reasoning', '')[:80]}"
            )
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: spine-session-cli.py {start|end|status} [...]", file=sys.stderr)
        return 2
    sub = sys.argv[1]
    rest = sys.argv[2:]
    if sub == "start":
        return cmd_start(rest)
    if sub == "end":
        return cmd_end(rest)
    if sub == "status":
        return cmd_status(rest)
    print(f"unknown subcommand: {sub}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
