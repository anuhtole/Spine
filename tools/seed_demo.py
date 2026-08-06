import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass(frozen=True)
class SeedResult:
    org_id: str
    org_key: str
    agent_id: str
    policy_id: str


def _env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    if val is None:
        return default
    val = val.strip()
    return val if val else default


def _env_any(*names: str, default: str | None = None) -> str | None:
    for n in names:
        v = _env(n)
        if v:
            return v
    return default


def _load_dotenv_if_present() -> None:
    """
    Best-effort local .env loading for developer convenience.
    This script is often run on the host (not inside the API container),
    so it should pick up ADMIN_API_KEY and friends from ./.env.
    """
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


async def _request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json: Any | None = None,
) -> Any:
    res = await client.request(method, url, headers=headers, json=json)
    if res.status_code >= 400:
        detail = res.text
        raise RuntimeError(f"{method} {url} -> {res.status_code}: {detail}")
    if not res.content:
        return None
    return res.json()


async def seed_demo() -> SeedResult:
    base = (_env_any("SPINE_BASE_URL", "GUTS_BASE_URL", default="http://127.0.0.1:8000") or "").rstrip("/")
    admin_key = _env_any("ADMIN_API_KEY", "SPINE_ADMIN_API_KEY", "GUTS_ADMIN_API_KEY") or "change-me"

    org_name = _env_any("SPINE_SEED_ORG_NAME", "GUTS_SEED_ORG_NAME", default="demo-org") or "demo-org"
    org_plan = _env_any("SPINE_SEED_ORG_PLAN", "GUTS_SEED_ORG_PLAN", default="starter") or "starter"
    api_key_name = _env_any("SPINE_SEED_ORG_KEY_NAME", "GUTS_SEED_ORG_KEY_NAME", default="local-dev") or "local-dev"
    agent_name = _env_any("SPINE_SEED_AGENT_NAME", "GUTS_SEED_AGENT_NAME", default="demo-agent") or "demo-agent"
    agent_framework = (
        _env_any("SPINE_SEED_AGENT_FRAMEWORK", "GUTS_SEED_AGENT_FRAMEWORK", default="generic") or "generic"
    )

    policy_name = (
        _env_any("SPINE_SEED_POLICY_NAME", "GUTS_SEED_POLICY_NAME", default="Allow patient record reads")
        or "Allow patient record reads"
    )
    policy_rule_type = (
        _env_any("SPINE_SEED_POLICY_RULE_TYPE", "GUTS_SEED_POLICY_RULE_TYPE", default="action") or "action"
    )
    policy_target_regex = (
        _env_any("SPINE_SEED_POLICY_TARGET_REGEX", "GUTS_SEED_POLICY_TARGET_REGEX", default=r"^/patient-records/.*")
        or r"^/patient-records/.*"
    )

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        org = await _request(
            client,
            "POST",
            f"{base}/v1/orgs",
            headers={"X-API-Key": admin_key, "Content-Type": "application/json"},
            json={"name": org_name, "plan": org_plan},
        )
        org_id = str(org["id"])

        key = await _request(
            client,
            "POST",
            f"{base}/v1/orgs/{org_id}/api-keys",
            headers={"X-API-Key": admin_key, "Content-Type": "application/json"},
            json={"name": api_key_name},
        )
        org_key = str(key["raw_key"])

        agent = await _request(
            client,
            "POST",
            f"{base}/v1/agents/register",
            headers={"X-Org-Key": org_key, "Content-Type": "application/json"},
            json={"name": agent_name, "framework": agent_framework},
        )
        agent_id = str(agent["id"])

        policy = await _request(
            client,
            "POST",
            f"{base}/v1/policies",
            headers={"X-Org-Key": org_key, "Content-Type": "application/json"},
            json={
                "name": policy_name,
                "rule_type": policy_rule_type,
                "agent_id": None,
                "rule_config": {
                    "effect": "allow",
                    "action_types": ["read"],
                    "target_resource_regex": policy_target_regex,
                },
            },
        )
        policy_id = str(policy["id"])

    return SeedResult(org_id=org_id, org_key=org_key, agent_id=agent_id, policy_id=policy_id)


def main() -> None:
    _load_dotenv_if_present()
    enabled = (_env_any("SPINE_SEED_DEMO", "GUTS_SEED_DEMO", default="true") or "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if not enabled:
        print("SPINE_SEED_DEMO=false; skipping seed.")
        return

    res = asyncio.run(seed_demo())
    print("\nSeeded demo data:")
    print(f"- org_id: {res.org_id}")
    print(f"- agent_id: {res.agent_id}")
    print(f"- policy_id: {res.policy_id}")
    print("\nNext: create a dashboard user with:")
    print(
        f'  python tools/create_user.py --email you@company.com --name "Your Name" --org-id {res.org_id} --role admin'
    )
    print("\nFor the SDK, set the org API key in env (shown once above):")
    print(f"- SPINE_ORG_KEY={res.org_key}")


if __name__ == "__main__":
    main()
