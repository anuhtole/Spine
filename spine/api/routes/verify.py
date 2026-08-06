import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import OrgIdDep, get_db
from spine.core.audit_verify import verify_org_chain

router = APIRouter()


@router.get("/verify")
async def verify_audit_chain(
    org_id: uuid.UUID = OrgIdDep, limit: int = 50_000, db: AsyncSession = Depends(get_db)
) -> dict:
    res = await verify_org_chain(db, org_id=org_id, limit=limit)
    return {
        "ok": res.ok,
        "org_id": str(res.org_id),
        "checked": res.checked,
        "first_bad_sequence": res.first_bad_sequence,
        "error": res.error,
    }
