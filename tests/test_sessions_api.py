"""Sessions CRUD: create, list, get, evaluations, end, ownership."""

import uuid

from tests._session_fixture import client, seed_org_and_agent  # noqa: F401


def test_create_and_list_session(client):
    _, agent_id, key = seed_org_and_agent(client)

    r = client.post(
        "/v1/sessions",
        headers={"X-Org-Key": key},
        json={
            "agent_id": str(agent_id),
            "goal": "Refactor auth to JWT",
            "constraints": ["only touch /src/auth/**", "no schema changes"],
            "expected_resources": ["/src/auth/*.ts"],
            "success_criteria": "all auth tests pass",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "active"
    assert body["drift_score"] == 0.0
    assert body["evaluation_count"] == 0
    assert body["goal"] == "Refactor auth to JWT"

    sid = body["id"]

    r2 = client.get("/v1/sessions", headers={"X-Org-Key": key})
    assert r2.status_code == 200
    rows = r2.json()
    assert any(s["id"] == sid for s in rows)

    r3 = client.get(f"/v1/sessions/{sid}", headers={"X-Org-Key": key})
    assert r3.status_code == 200
    assert r3.json()["id"] == sid


def test_create_session_rejects_foreign_agent(client):
    _, _, key = seed_org_and_agent(client)
    bogus = str(uuid.uuid4())
    r = client.post(
        "/v1/sessions",
        headers={"X-Org-Key": key},
        json={"agent_id": bogus, "goal": "x"},
    )
    assert r.status_code == 404


def test_end_session(client):
    _, agent_id, key = seed_org_and_agent(client)
    r = client.post(
        "/v1/sessions",
        headers={"X-Org-Key": key},
        json={"agent_id": str(agent_id), "goal": "g"},
    )
    sid = r.json()["id"]

    r2 = client.post(
        f"/v1/sessions/{sid}/end",
        headers={"X-Org-Key": key},
        json={"status": "completed"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"

    # Subsequent end is a no-op (idempotent-ish)
    r3 = client.get(f"/v1/sessions/{sid}", headers={"X-Org-Key": key})
    assert r3.json()["status"] == "completed"


def test_cross_org_access_denied(client):
    _, agent_id, key1 = seed_org_and_agent(client)
    r = client.post(
        "/v1/sessions",
        headers={"X-Org-Key": key1},
        json={"agent_id": str(agent_id), "goal": "g"},
    )
    sid = r.json()["id"]

    _, _, key2 = seed_org_and_agent(client)
    r2 = client.get(f"/v1/sessions/{sid}", headers={"X-Org-Key": key2})
    assert r2.status_code == 404


def test_evaluations_list_empty_for_new_session(client):
    _, agent_id, key = seed_org_and_agent(client)
    r = client.post(
        "/v1/sessions",
        headers={"X-Org-Key": key},
        json={"agent_id": str(agent_id), "goal": "g"},
    )
    sid = r.json()["id"]
    r2 = client.get(f"/v1/sessions/{sid}/evaluations", headers={"X-Org-Key": key})
    assert r2.status_code == 200
    assert r2.json() == []
