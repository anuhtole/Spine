#!/usr/bin/env bash
# Install the Spine PreToolUse hook and slash commands into a user's
# Claude Code config. Idempotent. Run from anywhere.

set -euo pipefail

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SPINE_DIR="${SPINE_DIR:-$HOME/.spine}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
CLAUDE_CMDS="$CLAUDE_DIR/commands"
CLAUDE_SETTINGS="$CLAUDE_DIR/settings.json"

echo "→ installing Spine for Claude Code"
echo "  source:           $REPO_DIR"
echo "  ~/.spine:         $SPINE_DIR"
echo "  ~/.claude:        $CLAUDE_DIR"

mkdir -p "$SPINE_DIR"
mkdir -p "$CLAUDE_CMDS"

# Copy hook + tool_mapping + CLI
cp "$REPO_DIR/hook.py" "$SPINE_DIR/hook.py"
cp "$REPO_DIR/tool_mapping.py" "$SPINE_DIR/tool_mapping.py"
cp "$REPO_DIR/spine-session-cli.py" "$SPINE_DIR/spine-session-cli.py"
chmod +x "$SPINE_DIR/hook.py" "$SPINE_DIR/spine-session-cli.py"

# Copy slash commands
cp "$REPO_DIR/slash_commands/"*.md "$CLAUDE_CMDS/"

# Seed config.json if missing
CONFIG_PATH="$SPINE_DIR/config.json"
if [[ ! -f "$CONFIG_PATH" ]]; then
  cat > "$CONFIG_PATH" <<'JSON'
{
  "base_url": "https://api.demo.spinelayer.com",
  "org_key": "REPLACE_WITH_YOUR_ORG_KEY",
  "agent_id": "REPLACE_WITH_YOUR_AGENT_ID",
  "fail_closed": true,
  "timeout_seconds": 10,
  "debug": false,
  "default_constraints": [],
  "default_expected_resources": []
}
JSON
  echo "  wrote default $CONFIG_PATH (edit org_key and agent_id)"
else
  echo "  preserved existing $CONFIG_PATH"
fi

# Patch settings.json — append PreToolUse hook if not already present
python3 - "$CLAUDE_SETTINGS" "$SPINE_DIR/hook.py" <<'PY'
import json, os, sys
settings_path, hook_path = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(settings_path), exist_ok=True)
try:
    with open(settings_path) as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})
pre = hooks.setdefault("PreToolUse", [])
command = f"python3 {hook_path}"
already = any(
    any(h.get("command") == command for h in entry.get("hooks", []))
    for entry in pre
)
if not already:
    pre.append({"matcher": "*", "hooks": [{"type": "command", "command": command}]})
    with open(settings_path, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"  patched {settings_path} with PreToolUse hook")
else:
    print(f"  {settings_path} already references the Spine hook")
PY

cat <<'EOF'

✓ Spine for Claude Code installed.

Next steps:
  1. Edit ~/.spine/config.json — set "org_key" and "agent_id".
  2. In any Claude Code session, run:
         /spine-session-start "what you're trying to do"
  3. Every subsequent tool call goes through Spine.
  4. When done:    /spine-session-end       (or /spine-session-status to peek)

Tip: set "debug": true in config.json to log every intercept to stderr.
EOF
