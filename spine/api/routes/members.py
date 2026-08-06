import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import OrgAdminDep, OrgAuth, get_db
from spine.core.users import provision_org_member
from spine.models.user import Membership, User
from spine.schemas.members import MemberCreate, MemberResponse, MemberUpdate

router = APIRouter()


def _to_response(user: User, membership: Membership) -> MemberResponse:
    return MemberResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.get("", response_model=list[MemberResponse])
async def list_members(
    auth: OrgAuth = OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> list[MemberResponse]:
    result = await db.execute(
        sa.select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.org_id == auth.org_id)
        .order_by(Membership.created_at.asc())
    )
    return [_to_response(user, membership) for user, membership in result.all()]


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def create_member(
    payload: MemberCreate,
    auth: OrgAuth = OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    user, membership = await provision_org_member(
        db,
        org_id=auth.org_id,
        email=str(payload.email).lower().strip(),
        name=payload.name.strip(),
        password=payload.password,
        role=payload.role,
    )
    await db.commit()
    await db.refresh(user)
    await db.refresh(membership)
    return _to_response(user, membership)


@router.patch("/{user_id}", response_model=MemberResponse)
async def update_member(
    user_id: uuid.UUID,
    payload: MemberUpdate,
    auth: OrgAuth = OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    result = await db.execute(
        sa.select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.org_id == auth.org_id, User.id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    user, membership = row
    if membership.role == "admin" and payload.role != "admin":
        admin_count = await db.scalar(
            sa.select(sa.func.count())
            .select_from(Membership)
            .where(Membership.org_id == auth.org_id, Membership.role == "admin")
        )
        if admin_count is not None and admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last organization admin",
            )

    membership.role = payload.role
    await db.commit()
    await db.refresh(membership)
    return _to_response(user, membership)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: uuid.UUID,
    auth: OrgAuth = OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> None:
    if auth.user_id and auth.user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own membership",
        )

    result = await db.execute(
        sa.select(Membership).where(Membership.org_id == auth.org_id, Membership.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if membership.role == "admin":
        admin_count = await db.scalar(
            sa.select(sa.func.count())
            .select_from(Membership)
            .where(Membership.org_id == auth.org_id, Membership.role == "admin")
        )
        if admin_count is not None and admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last organization admin",
            )

    await db.delete(membership)
    await db.commit()
