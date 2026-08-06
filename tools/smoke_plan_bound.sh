#!/usr/bin/env bash
# Spine plan-bound monitoring — full end-to-end smoke test.
#
# 1. Spins up uvicorn against a fresh SQLite DB
# 2. Seeds an org, agent, allow-policy
# 3. Registers a session
# 4. Intercepts an aligned action → expect allowed=True
# 5. Manually injects a divergent plan_evaluation row + bumps drift_score
# 6. Intercepts another action in same session → expect drift-blocked
# 7. Verifies the audit hash chain still validates
#
# Does NOT call Anthropic — the plan engine is exercised by injecting state
# directly. Real LLM calls happen when MONITOR_ENABLED + ANTHROPIC_API_KEY are
# set; see tests/test_plan_engine.py for mocked-LLM coverage of the engine.

set -euo pipefail

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"

PORT="${SMOKE_PORT:-9123}"
DB_PATH="$(mktemp -d)/smoke.db"
LOG_PATH="$(mktemp)"

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "→ booting Spine on :$PORT against $DB_PATH"

export DATABASE_URL="sqlite+aiosqlite:///$DB_PATH"
export ADMIN_API_KEY="smoke-admin"
export JWT_SECRET="smoke-jwt"
export ENVIRONMENT="local"
export MONITOR_ENABLED="false"
export SSE_ENABLED="false"
export PLAN_DRIFT_FLAG_THRESHOLD="0.4"
export PLAN_DRIFT_BLOCK_THRESHOLD="0.6"

# Create tables via Base.metadata.create_all (the production Alembic chain
# uses Postgres-only constructs in earlier migrations; the smoke test runs on
# SQLite for portability). Production deploys still apply migrations normally.
python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from spine.db.base import Base
async def go():
    e = create_async_engine('$DATABASE_URL')
    async with e.begin() as c:
        await c.run_sync(Base.metadata.create_all)
asyncio.run(go())
print('  schema created')
" >>"$LOG_PATH" 2>&1

python3 -m uvicorn spine.main:app --host 127.0.0.1 --port "$PORT" --log-level warning >>"$LOG_PATH" 2>&1 &
API_PID=$!

# Wait for healthcheck
for i in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    echo "  ✓ API ready (after ${i} × 0.25s)"
    break
  fi
  sleep 0.25
done

if ! curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "✗ API never became ready. Log:" >&2
  cat "$LOG_PATH" >&2
  exit 1
fi

BASE="http://127.0.0.1:$PORT"
ADMIN_HDR="X-API-Key: $ADMIN_API_KEY"

step() { printf "\n→ %s\n" "$*"; }

step "create org"
ORG_RESP=$(curl -sS -X POST "$BASE/v1/orgs" \
  -H "Content-Type: application/json" -H "$ADMIN_HDR" \
  -d '{"name":"smoke","plan":"starter"}')
ORG_ID=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['id'])" "$ORG_RESP")
echo "  org_id=$ORG_ID"

step "mint org key"
KEY_RESP=$(curl -sS -X POST "$BASE/v1/orgs/$ORG_ID/api-keys" \
  -H "Content-Type: application/json" -H "$ADMIN_HDR" \
  -d '{"name":"smoke-key"}')
ORG_KEY=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['raw_key'])" "$KEY_RESP")
echo "  org_key=${ORG_KEY:0:18}…"

ORG_HDR="X-Org-Key: $ORG_KEY"

step "register agent"
AGENT_RESP=$(curl -sS -X POST "$BASE/v1/agents/register" \
  -H "Content-Type: application/json" -H "$ORG_HDR" \
  -d '{"name":"smoke-agent","framework":"claude-code"}')
AGENT_ID=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['id'])" "$AGENT_RESP")
echo "  agent_id=$AGENT_ID"

step "create allow-read policy"
curl -fsS -X POST "$BASE/v1/policies" \
  -H "Content-Type: application/json" -H "$ORG_HDR" \
  -d '{
    "name": "allow-read",
    "rule_type": "action",
    "rule_config": {"effect": "allow", "action_types": ["read"]}
  }' >/dev/null
echo "  ✓ policy created"

step "register plan-bound session"
SESS_RESP=$(curl -sS -X POST "$BASE/v1/sessions" \
  -H "Content-Type: application/json" -H "$ORG_HDR" \
  -d "{
    \"agent_id\": \"$AGENT_ID\",
    \"goal\": \"Refactor auth module to use JWT instead of session cookies\",
    \"constraints\": [\"only touch /src/auth/**\", \"no schema changes\"],
    \"expected_resources\": [\"/src/auth/*.ts\"],
    \"success_criteria\": \"all auth tests pass\"
  }")
SESSION_ID=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['id'])" "$SESS_RESP")
echo "  session_id=$SESSION_ID"

step "aligned intercept: should be allowed, drift_score=0"
ALIGNED=$(curl -sS -X POST "$BASE/v1/intercept" \
  -H "Content-Type: application/json" -H "$ORG_HDR" \
  -d "{
    \"agent_id\": \"$AGENT_ID\",
    \"session_id\": \"$SESSION_ID\",
    \"action\": {\"action_type\": \"read\", \"target_resource\": \"/src/auth/login.ts\"}
  }")
echo "  response: $ALIGNED"
python3 -c "
import json,sys
r = json.loads(sys.argv[1])
assert r['allowed'] is True, r
assert r['session_id'] == sys.argv[2], r
assert r['drift_score'] == 0.0, r
print('  ✓ allowed=True session_id matches drift=0.0')
" "$ALIGNED" "$SESSION_ID"

step "simulate accumulated drift by bumping session.drift_score past block threshold"
python3 - <<PY
import sqlite3
db = sqlite3.connect("$DB_PATH")
db.execute("UPDATE sessions SET drift_score = 0.7, evaluation_count = 3 WHERE id = ?", ("$SESSION_ID",))
db.commit()
db.close()
print("  ✓ drift_score forced to 0.70 (above the 0.60 block threshold)")
PY

step "next intercept in session should be HARD-BLOCKED by drift gate"
BLOCKED=$(curl -sS -X POST "$BASE/v1/intercept" \
  -H "Content-Type: application/json" -H "$ORG_HDR" \
  -d "{
    \"agent_id\": \"$AGENT_ID\",
    \"session_id\": \"$SESSION_ID\",
    \"action\": {\"action_type\": \"read\", \"target_resource\": \"/src/auth/login.ts\"}
  }")
echo "  response: $BLOCKED"
python3 -c "
import json,sys
r = json.loads(sys.argv[1])
assert r['allowed'] is False, r
assert r['decision'] == 'blocked', r
assert 'drift' in r['reason'].lower(), r
print('  ✓ blocked by drift gate:', r['reason'])
" "$BLOCKED"

step "audit chain still verifies (session_id present + absent rows)"
VERIFY=$(curl -sS "$BASE/v1/audit/verify" -H "$ORG_HDR")
echo "  $VERIFY"
python3 -c "
import json,sys
r = json.loads(sys.argv[1])
assert r['ok'] is True, r
assert r['checked'] >= 2, r
print('  ✓ chain ok, checked=', r['checked'])
" "$VERIFY"

step "exercise hook.py against a real running Spine"
TMP_PROJECT=$(mktemp -d)
TMP_CFG=$(mktemp)
cat > "$TMP_CFG" <<JSON
{
  "base_url": "$BASE",
  "org_key": "$ORG_KEY",
  "agent_id": "$AGENT_ID",
  "fail_closed": true,
  "timeout_seconds": 10,
  "debug": false
}
JSON

# Force the hook to read this config and pretend our cwd is the project dir.
# No session file yet -> intercept will NOT carry session_id, so existing
# allow-read policy applies and we expect a silent allow (exit 0, empty stdout).
HOOK_OUT=$(SPINE_CONFIG_PATH="$TMP_CFG" python3 integrations/claude-code-spine/hook.py <<JSON
{"tool_name":"Read","tool_input":{"file_path":"/src/auth/login.ts"},"cwd":"$TMP_PROJECT"}
JSON
)
if [[ -z "$HOOK_OUT" ]]; then
  echo "  ✓ hook silently allowed an aligned-without-session intercept"
else
  echo "  ✗ expected silent allow, got: $HOOK_OUT"
  exit 1
fi

# Now write the drift-blocked session_id into the project's .spine file.
# The hook should see drift-blocked from the API and emit a block JSON.
mkdir -p "$TMP_PROJECT/.spine"
echo "$SESSION_ID" > "$TMP_PROJECT/.spine/session_id"

HOOK_OUT=$(SPINE_CONFIG_PATH="$TMP_CFG" python3 integrations/claude-code-spine/hook.py <<JSON
{"tool_name":"Read","tool_input":{"file_path":"/src/auth/login.ts"},"cwd":"$TMP_PROJECT"}
JSON
)
echo "  hook output: $HOOK_OUT"
python3 -c "
import json,sys
o = json.loads(sys.argv[1])
assert o['decision'] == 'block', o
assert 'drift' in o['reason'].lower(), o
print('  ✓ hook emitted block JSON for drift-blocked session')
" "$HOOK_OUT"

step "end session"
END=$(curl -sS -X POST "$BASE/v1/sessions/$SESSION_ID/end" \
  -H "Content-Type: application/json" -H "$ORG_HDR" \
  -d '{"status":"abandoned"}')
echo "  $END"
python3 -c "
import json,sys
r = json.loads(sys.argv[1])
assert r['status'] == 'abandoned', r
print('  ✓ session closed status=abandoned drift_score=', r['drift_score'])
" "$END"

echo
echo "════════════════════════════════════════════════════════════════"
echo "  ALL SMOKE CHECKS PASSED"
echo "════════════════════════════════════════════════════════════════"
