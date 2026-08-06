"""CLI tool to create a user and assign them to an organization.

Usage (from project root or inside API container):

    python tools/create_user.py \
        --email alice@company.com \
        --name "Alice" \
        --org-id <uuid> \
        --role admin

If --password is omitted, the script will prompt interactively.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
import uuid
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Allow running from project root without installing as package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spine.auth.passwords import hash_password  # noqa: E402
from spine.models.organization import Organization  # noqa: E402
from spine.models.user import Membership, User  # noqa: E402


def _load_dotenv_if_present() -> None:
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


async def create_user(
    db_url: str,
    *,
    email: str,
    name: str,
    password: str,
    org_id: uuid.UUID,
    role: str,
) -> None:
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            await _do_create(session, email=email, name=name, password=password, org_id=org_id, role=role)

    await engine.dispose()


async def _do_create(
    db: AsyncSession,
    *,
    email: str,
    name: str,
    password: str,
    org_id: uuid.UUID,
    role: str,
) -> None:
    org_result = await db.execute(sa.select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        print(f"ERROR: Organization {org_id} not found.", file=sys.stderr)
        sys.exit(1)

    existing = await db.execute(sa.select(User).where(User.email == email))
    user = existing.scalar_one_or_none()

    if user:
        print(f"User {email} already exists (id={user.id}). Adding membership to org '{org.name}'...")
    else:
        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
        )
        db.add(user)
        await db.flush()
        print(f"Created user: {email} (id={user.id})")

    mem_result = await db.execute(
        sa.select(Membership).where(Membership.user_id == user.id, Membership.org_id == org_id)
    )
    if mem_result.scalar_one_or_none():
        print(f"Membership already exists for {email} -> {org.name}")
        return

    membership = Membership(user_id=user.id, org_id=org_id, role=role)
    db.add(membership)
    await db.flush()
    print(f"Added membership: {email} -> org '{org.name}' (role={role})")


def main() -> None:
    _load_dotenv_if_present()

    parser = argparse.ArgumentParser(description="Create a Spine user and assign to an org")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--name", required=True, help="Display name")
    parser.add_argument("--org-id", required=True, help="Organization UUID to assign the user to")
    parser.add_argument("--role", default="admin", choices=["admin", "member", "viewer"], help="Role in the org")
    parser.add_argument("--password", default=None, help="Password (prompted if omitted)")
    parser.add_argument("--db-url", default=None, help="DATABASE_URL override")
    args = parser.parse_args()

    db_url = args.db_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: Set DATABASE_URL or pass --db-url", file=sys.stderr)
        sys.exit(1)

    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("ERROR: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    try:
        org_uuid = uuid.UUID(args.org_id)
    except ValueError:
        print(f"ERROR: Invalid UUID: {args.org_id}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(
        create_user(
            db_url,
            email=args.email,
            name=args.name,
            password=password,
            org_id=org_uuid,
            role=args.role,
        )
    )
    print("\nDone. User can now log in at the dashboard.")


if __name__ == "__main__":
    main()
