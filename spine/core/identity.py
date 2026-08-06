import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from spine.models.agent import Agent


async def get_active_agent(session: AsyncSession, agent_id: uuid.UUID) -> Agent | None:
    result = await session.execute(sa.select(Agent).where(Agent.id == agent_id).where(Agent.is_active.is_(True)))
    return result.scalar_one_or_none()
