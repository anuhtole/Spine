# Spine for Claude Code

Plan-bound policy enforcement and audit for **Claude Code**, via a `PreToolUse`
hook. Every tool call (Read, Write, Edit, Bash, WebFetch, MCP, …) is sent to
Spine before it runs. If the action is off-plan or violates a policy, the tool
is blocked.

> **The moat:** Spine's plan reviewer is context-isolated. It only sees the
> plan you declare, the action being attempted, and structural alignment
> verdicts on prior actions in this session. It never reads file contents,
> tool outputs, or your Claude Code prompts. A prompt injection sitting in a
> PDF the agent just read cannot reach the reviewer — the reviewer doesn't
> read the attack surface.

---

## Install (90 seconds)

```bash
cd integrations/claude-code-spine
./install.sh
```

This copies `hook.py`, `tool_mapping.py`, and `spine-session-cli.py` to
`~/.spine/`, the slash commands to `~/.claude/commands/`, and adds the
`PreToolUse` hook to `~/.claude/settings.json`.

Then edit `~/.spine/config.json` and set:

| Field | Value |
|------|-------|
| `base_url` | `https://api.demo.spinelayer.com` (or your local `http://localhost:8000`) |
| `org_key`  | `spine_...` — mint in Spine dashboard → Settings → API keys |
| `agent_id` | UUID — register in Spine dashboard → Agents |

Restart Claude Code (or just start a new session) and you're done.

---

## Usage

In any project where you want plan-bound oversight:

```
/spine-session-start "Refactor the auth module to use JWT instead of cookies. Only touch /src/auth/**."
```

The session ID is written to `<project>/.spine/session_id`. Every subsequent
tool call by Claude Code is intercepted, evaluated by the plan reviewer, and
contributes to the session's drift score.

```
/spine-session-status    # see drift score, last verdicts, goal
/spine-session-end       # close the session, print final drift_score
```

If a single action is judged **divergent**, an approval ticket opens. If
accumulated drift crosses `PLAN_DRIFT_BLOCK_THRESHOLD` (default 0.6), every
subsequent tool call in the session is blocked synchronously — you have to
start a new session.

---

## What gets sent to Spine

For each tool call, the hook POSTs to `/v1/intercept` with:

| Spine field | Source |
|------|------|
| `agent_id` | from `~/.spine/config.json` |
| `session_id` | from `<cwd>/.spine/session_id` if present |
| `action.action_type` | tool name normalized (`Read`→`read`, `Bash`→`exec`, `WebFetch`→`http:GET`, `mcp__slack__send_message`→`mcp:slack:send_message`, …) |
| `action.target_resource` | `file_path` / `path` / `url` / `command` / `pattern` / `query` from the tool input |
| `action.metadata.claude_code.tool_name` | the original tool name for debugging |

It does **not** send: file contents, tool outputs, your Claude Code prompts,
or any other content from Claude Code's context window. That is the
structural isolation that makes the reviewer injection-resistant.

---

## Fail-closed vs fail-open

Default: **fail-closed**. If Spine is unreachable, every tool is blocked
with a clear reason. This is the right default for production.

For dev only:

```jsonc
// ~/.spine/config.json
{
  "fail_closed": false,
  …
}
```

Or set `SPINE_FAIL_OPEN=true` in the env for one session.

---

## Debug

```jsonc
{
  "debug": true,
  …
}
```

Then `tail` your Claude Code stderr (or run with `--verbose`). You'll see one
line per intercept:

```
[spine-hook] intercept tool_name='Read' action_type='read' target='/src/auth/login.ts' session_id=…
[spine-hook] spine decision=allowed allowed=True drift=0.12 audit=… dt=18ms
```

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Tool runs but no audit row | Hook not installed, or `python3` not on PATH. Check `~/.claude/settings.json` `hooks.PreToolUse`. |
| Every tool blocked with "Spine unreachable" | `base_url` wrong, network blocked, or Spine API down. |
| 404 on session_id | The file at `<cwd>/.spine/session_id` is stale — run `/spine-session-end` then start fresh. |
| Audit shows blocked but Claude still answered | The model answered from memory without calling the tool. Look at the audit timestamp — is there a `read` row at that moment? If not, no tool ran. |
| `agent_id not configured` | Edit `~/.spine/config.json`. |

---

## Files

```
~/.spine/
├── config.json           # base_url, org_key, agent_id, flags
├── hook.py               # PreToolUse hook
├── tool_mapping.py       # tool_name → action_type translation
└── spine-session-cli.py  # start/end/status commands

~/.claude/
├── settings.json         # patched to include the PreToolUse hook
└── commands/
    ├── spine-session-start.md
    ├── spine-session-end.md
    └── spine-session-status.md
```
