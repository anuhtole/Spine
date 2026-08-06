"""One-command demo setup.

Creates everything you need to see Spine working: an org, an API key, a
registered agent, a small set of illustrative policies, and a dashboard
login. Prints the credentials at the end.

Run it inside the API container (that is what `make demo` does):

    docker compose exec api python tools/quickstart.py

Safe to re-run — it creates a fresh org each time.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.create_user import create_user  # noqa: E402

BASE_URL = os.getenv("SPINE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "change-me")
DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://spine:spine@db:5432/spine")

DEMO_EMAIL = os.getenv("SPINE_DEMO_EMAIL", "demo@spine.dev")
DEMO_PASSWORD = os.getenv("SPINE_DEMO_PASSWORD", "spine12345")
DEMO_NAME = "Demo Admin"

# Three policies chosen to show all three effects. Read the rule_config —
# that is the entire policy language, there is nothing hidden behind it.
DEMO_POLICIES = [
    {
        "name": "Allow reads under /data",
        "rule_type": "action",
        "rule_config": {
            "effect": "allow",
            "action_types": ["read"],
            "target_resource_regex": r"^/data/.*",
        },
    },
    {
        "name": "Flag shell commands for review",
        "rule_type": "action",
        "rule_config": {
            "effect": "flag",
            "action_types": ["shell"],
        },
    },
    {
        "name": "Deny writes to system paths",
        "rule_type": "action",
        "rule_config": {
            "effect": "deny",
            "action_types": ["write", "delete"],
            "target_resource_regex": r"^/(etc|usr|bin|var)/.*",
        },
    },
]


async def _wait_for_api(client: httpx.AsyncClient, *, attempts: int = 60) -> None:
    for i in range(attempts):
        try:
            res = await client.get(f"{BASE_URL}/health", timeout=2.0)
            if res.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        if i == 0:
            print("Waiting for the API to come up...")
        await asyncio.sleep(1.0)
    raise RuntimeError(f"API at {BASE_URL} never became healthy")


async def _post(client: httpx.AsyncClient, path: str, *, headers: dict, json: dict) -> dict:
    res = await client.post(f"{BASE_URL}{path}", headers=headers, json=json, timeout=15.0)
    if res.status_code >= 400:
        raise RuntimeError(f"POST {path} -> {res.status_code}: {res.text}")
    return res.json()


async def main() -> None:
    admin = {"X-API-Key": ADMIN_KEY, "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        await _wait_for_api(client)

        org = await _post(client, "/v1/orgs", headers=admin, json={"name": "demo-org", "plan": "starter"})
        org_id = str(org["id"])

        key = await _post(client, f"/v1/orgs/{org_id}/api-keys", headers=admin, json={"name": "quickstart"})
        org_key = str(key["raw_key"])
        org_headers = {"X-Org-Key": org_key, "Content-Type": "application/json"}

        agent = await _post(
            client,
            "/v1/agents/register",
            headers=org_headers,
            json={"name": "demo-agent", "framework": "generic"},
        )
        agent_id = str(agent["id"])

        for policy in DEMO_POLICIES:
            await _post(client, "/v1/policies", headers=org_headers, json={**policy, "agent_id": None})

    await create_user(
        DB_URL,
        email=DEMO_EMAIL,
        name=DEMO_NAME,
        password=DEMO_PASSWORD,
        org_id=uuid.UUID(org_id),
        role="admin",
    )

    print(
        f"""
{"=" * 68}
  Spine is ready.
{"=" * 68}

  Dashboard   http://localhost:4173
  Email       {DEMO_EMAIL}
  Password    {DEMO_PASSWORD}

  API         http://localhost:8000
  API docs    http://localhost:8000/docs

  Seeded {len(DEMO_POLICIES)} policies: allow reads under /data, flag shell
  commands for human approval, deny writes to system paths. Everything
  else is denied by default — Spine has no implicit allow.

  Try an intercept the policies allow:

    curl -sS -X POST http://localhost:8000/v1/intercept \\
      -H "Content-Type: application/json" \\
      -H "X-Org-Key: {org_key}" \\
      -d '{{"agent_id":"{agent_id}",
           "action":{{"action_type":"read","target_resource":"/data/report.csv"}}}}'

  Then try one they don't (swap the target for /etc/passwd) and watch it
  get blocked and recorded.

  Saved for later use:
    export SPINE_ORG_KEY={org_key}
    export SPINE_AGENT_ID={agent_id}
{"=" * 68}
"""
    )


if __name__ == "__main__":
    asyncio.run(main())
