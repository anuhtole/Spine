"""Show that the audit log detects tampering.

Every audit row's hash is computed from its own content plus the previous
row's hash. Change any historical row and every hash after it stops matching,
so the edit is detectable even by whoever made it.

This script writes a short chain, verifies it, edits one row directly in the
database (the thing an attacker with DB access would do), and verifies again.

    python examples/audit_tamper_detection.py

Runs against a temporary SQLite file. No Docker, no API key, no setup.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import uuid
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spine.core.audit_logger import log_event  # noqa: E402
from spine.core.audit_verify import verify_org_chain  # noqa: E402
from spine.db.base import Base  # noqa: E402
from spine.models.audit_event import AuditEvent  # noqa: E402

ACTIONS = [
    ("read", "/data/customers.csv", "allowed"),
    ("read", "/data/orders.csv", "allowed"),
    ("write", "/data/summary.md", "allowed"),
    ("shell", "rm -rf /var/log", "blocked"),
    ("read", "/data/pricing.csv", "allowed"),
]


def rule(char: str = "─") -> str:
    return char * 68


async def main() -> int:
    org_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    with tempfile.TemporaryDirectory() as tmp:
        engine = create_async_engine(f"sqlite+aiosqlite:///{Path(tmp) / 'audit.db'}")
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print(f"\n{rule('═')}\n  1. An agent takes five actions. Each one is recorded.\n{rule('═')}\n")

        async with SessionLocal() as db:
            for action_type, target, decision in ACTIONS:
                event = await log_event(
                    db,
                    agent_id=agent_id,
                    org_id=org_id,
                    action_type=action_type,
                    target_resource=target,
                    decision=decision,
                    policy_id=None,
                    metadata={"source": "demo"},
                )
                await db.commit()
                print(f"  #{event.sequence}  {decision:<8} {action_type:<6} {target:<24} hash {event.event_hash[:12]}…")

        print(f"\n{rule()}\n  2. Verify the chain.\n{rule()}\n")

        async with SessionLocal() as db:
            result = await verify_org_chain(db, org_id=org_id)
        print(f"  ok={result.ok}   rows checked={result.checked}   first bad row={result.first_bad_sequence}")
        print("\n  The chain is intact.\n")

        print(
            f"{rule()}\n  3. Tamper with it — hide the blocked `rm -rf` by rewriting\n"
            f"     row #4 directly in the database.\n{rule()}\n"
        )

        async with SessionLocal() as db:
            await db.execute(
                sa.update(AuditEvent)
                .where(AuditEvent.org_id == org_id, AuditEvent.sequence == 4)
                .values(action_type="read", target_resource="/data/notes.txt", policy_decision="allowed")
            )
            await db.commit()
        print("  Row #4 now reads:  allowed  read   /data/notes.txt")
        print("  No application code was involved — this was a direct UPDATE.\n")

        print(f"{rule()}\n  4. Verify again.\n{rule()}\n")

        async with SessionLocal() as db:
            result = await verify_org_chain(db, org_id=org_id)
        print(f"  ok={result.ok}   rows checked={result.checked}   first bad row={result.first_bad_sequence}")
        print(f"  error: {result.error}")

        await engine.dispose()

        if result.ok or result.first_bad_sequence != 4:
            print("\n  UNEXPECTED: the tampering was not caught. This is a bug.\n")
            return 1

        print(
            f"""
{rule("═")}
  The edit was caught, and the report points at row #4 — the exact row
  that was changed.

  Nothing compares against a backup here. Row #4's stored hash no longer
  matches a recomputation of its own contents, and rows #5 onward chain
  off that hash, so the damage is bounded and located rather than merely
  suspected. Rewriting row #4 convincingly would mean recomputing every
  hash after it.

  Implementation: spine/core/audit_logger.py (writer)
                  spine/core/audit_verify.py (verifier)
  Live endpoint:  GET /v1/audit/verify
{rule("═")}
"""
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
