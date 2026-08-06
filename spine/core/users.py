import uuid

import sqlalchemy as sa
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.auth.passwords import hash_password
from spine.models.organization import Organization
from spine.models.user import Membership, User


async def provision_org_member(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    email: str,
    name: str,
    password: str,
    role: str,
) -> tuple[User, Membership]:
    org_result = await db.execute(sa.select(Organization).where(Organization.id == org_id))
    if not org_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    existing = await db.execute(sa.select(User).where(User.email == email))
    user = existing.scalar_one_or_none()
    if not user:
        user = User(email=email, name=name, password_hash=hash_password(password))
        db.add(user)
        await db.flush()
    elif user.name != name:
        user.name = name

    mem_result = await db.execute(
        sa.select(Membership).where(Membership.user_id == user.id, Membership.org_id == org_id)
    )
    if mem_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization",
        )

    membership = Membership(user_id=user.id, org_id=org_id, role=role)
    db.add(membership)
    await db.flush()
    return user, membership
