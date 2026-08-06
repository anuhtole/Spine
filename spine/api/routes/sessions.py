import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import OrgIdDep, get_db
from spine.models.agent import Agent
from spine.models.plan_evaluation import PlanEvaluation
from spine.models.session import Session as SessionModel
from spine.schemas.session import (
    PlanEvaluationResponse,
    SessionCreate,
    SessionEndRequest,
    SessionEndResponse,
    SessionResponse,
)

router = APIRouter()


def _to_response(s: SessionModel) -> SessionResponse:
    return SessionResponse(
        id=s.id,
        org_id=s.org_id,
        agent_id=s.agent_id,
        goal=s.goal,
        constraints=list(s.constraints or []),
        expected_resources=list(s.expected_resources or []),
        success_criteria=s.success_criteria,
        status=s.status,
        drift_score=s.drift_score,
        evaluation_count=s.evaluation_count,
        created_at=s.created_at,
        ended_at=s.ended_at,
    )


def _eval_to_response(e: PlanEvaluation) -> PlanEvaluationResponse:
    return PlanEvaluationResponse(
        id=e.id,
        session_id=e.session_id,
        audit_event_id=e.audit_event_id,
        agent_id=e.agent_id,
        org_id=e.org_id,
        alignment=e.alignment,
        confidence=e.confidence,
        reasoning=e.reasoning,
        drift_contribution=e.drift_contribution,
        drift_score_after=e.drift_score_after,
        model_id=e.model_id,
        approval_id=e.approval_id,
        created_at=e.created_at,
    )


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    org_id: uuid.UUID = OrgIdDep,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    # Verify agent belongs to this org and is active.
    agent = await db.get(Agent, payload.agent_id)
    if agent is None or agent.org_id != org_id or not agent.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    sess = SessionModel(
        org_id=org_id,
        agent_id=payload.agent_id,
        goal=payload.goal,
        constraints=list(payload.constraints or []),
        expected_resources=list(payload.expected_resources or []),
        success_criteria=payload.success_criteria,
        status="active",
        drift_score=0.0,
        evaluation_count=0,
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return _to_response(sess)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    agent_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    org_id: uuid.UUID = OrgIdDep,
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    limit = max(1, min(limit, 500))
    stmt = (
        sa.select(SessionModel)
        .where(SessionModel.org_id == org_id)
        .order_by(SessionModel.created_at.desc())
        .limit(limit)
    )
    if agent_id is not None:
        stmt = stmt.where(SessionModel.agent_id == agent_id)
    if status_filter:
        stmt = stmt.where(SessionModel.status == status_filter)
    result = await db.execute(stmt)
    return [_to_response(s) for s in result.scalars().all()]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    org_id: uuid.UUID = OrgIdDep,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    result = await db.execute(
        sa.select(SessionModel).where(SessionModel.id == session_id).where(SessionModel.org_id == org_id)
    )
    sess = result.scalar_one_or_none()
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _to_response(sess)


@router.get("/{session_id}/evaluations", response_model=list[PlanEvaluationResponse])
async def list_session_evaluations(
    session_id: uuid.UUID,
    limit: int = 200,
    org_id: uuid.UUID = OrgIdDep,
    db: AsyncSession = Depends(get_db),
) -> list[PlanEvaluationResponse]:
    # First confirm the session belongs to caller's org.
    sess_result = await db.execute(
        sa.select(SessionModel.id).where(SessionModel.id == session_id).where(SessionModel.org_id == org_id)
    )
    if sess_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    limit = max(1, min(limit, 1000))
    result = await db.execute(
        sa.select(PlanEvaluation)
        .where(PlanEvaluation.session_id == session_id)
        .order_by(PlanEvaluation.created_at.asc())
        .limit(limit)
    )
    return [_eval_to_response(e) for e in result.scalars().all()]


@router.post("/{session_id}/end", response_model=SessionEndResponse)
async def end_session(
    session_id: uuid.UUID,
    payload: SessionEndRequest,
    org_id: uuid.UUID = OrgIdDep,
    db: AsyncSession = Depends(get_db),
) -> SessionEndResponse:
    result = await db.execute(
        sa.select(SessionModel).where(SessionModel.id == session_id).where(SessionModel.org_id == org_id)
    )
    sess = result.scalar_one_or_none()
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if sess.status == "active":
        sess.status = payload.status
        sess.ended_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(sess)

    return SessionEndResponse(
        id=sess.id,
        status=sess.status,
        drift_score=sess.drift_score,
        evaluation_count=sess.evaluation_count,
        ended_at=sess.ended_at or datetime.now(timezone.utc),
    )
