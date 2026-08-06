import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from spine.api.deps import OrgIdDep, get_db
from spine.models.agent import Agent
from spine.schemas.agent import AgentCreate, AgentResponse

router = APIRouter()


@router.post("/register", response_model=AgentResponse)
async def register_agent(
    payload: AgentCreate,
    org_id: uuid.UUID = OrgIdDep,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    agent = Agent(name=payload.name, framework=payload.framework, org_id=org_id)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse(
        id=agent.id,
        org_id=agent.org_id,
        name=agent.name,
        framework=agent.framework,
        is_active=agent.is_active,
    )


@router.get("", response_model=list[AgentResponse])
async def list_agents(org_id: uuid.UUID = OrgIdDep, db: AsyncSession = Depends(get_db)) -> list[AgentResponse]:
    result = await db.execute(sa.select(Agent).where(Agent.org_id == org_id))
    agents = list(result.scalars().all())
    return [
        AgentResponse(
            id=a.id,
            org_id=a.org_id,
            name=a.name,
            framework=a.framework,
            is_active=a.is_active,
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID, org_id: uuid.UUID = OrgIdDep, db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    result = await db.execute(sa.select(Agent).where(Agent.id == agent_id).where(Agent.org_id == org_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse(
        id=agent.id,
        org_id=agent.org_id,
        name=agent.name,
        framework=agent.framework,
        is_active=agent.is_active,
    )


@router.delete("/{agent_id}")
async def deactivate_agent(
    agent_id: uuid.UUID, org_id: uuid.UUID = OrgIdDep, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(sa.select(Agent).where(Agent.id == agent_id).where(Agent.org_id == org_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    agent.is_active = False
    await db.commit()
    return {"status": "deactivated"}
