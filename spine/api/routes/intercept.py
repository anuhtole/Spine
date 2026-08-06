import time
import uuid

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import OrgIdDep, get_db
from spine.core.idempotency import get_cached_json, save_json
from spine.core.intercept_service import run_intercept
from spine.observability.metrics import spine_intercept_duration_seconds
from spine.schemas.intercept import InterceptRequest, InterceptResponse

router = APIRouter()


@router.post("/intercept", response_model=InterceptResponse)
async def intercept(
    response: Response,
    payload: InterceptRequest,
    org_id: uuid.UUID = OrgIdDep,
    x_request_id: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
) -> InterceptResponse:
    t0 = time.perf_counter()
    try:
        request_id = (x_request_id or "").strip() or str(uuid.uuid4())
        if idempotency_key:
            req_obj = payload.model_dump(mode="json")
            cached = await get_cached_json(
                db,
                org_id=org_id,
                idempotency_key=idempotency_key,
                request_obj=req_obj,
            )
            if cached:
                return InterceptResponse.model_validate(cached)

        out = await run_intercept(db, org_id=org_id, request_id=request_id, payload=payload)
        if idempotency_key:
            await save_json(
                db,
                org_id=org_id,
                idempotency_key=idempotency_key,
                request_obj=payload.model_dump(mode="json"),
                response_obj=out.model_dump(mode="json"),
            )
        response.headers["X-Request-ID"] = out.request_id
        return out
    finally:
        spine_intercept_duration_seconds.observe(time.perf_counter() - t0)
