from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Any
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.system import DeadLetterQueue

router = APIRouter(prefix="/dlq", tags=["dlq"])


class DLQResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    workflow_id: uuid.UUID
    failure_stage: str
    last_error: str
    retry_count: int
    resolved: bool
    created_at: Any

    model_config = {"from_attributes": True}


@router.get("", response_model=list[DLQResponse])
async def list_dlq(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DLQResponse]:
    """List all dead letter queue entries."""
    result = await db.execute(
        select(DeadLetterQueue)
        .where(DeadLetterQueue.resolved == False)
        .order_by(DeadLetterQueue.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/{dlq_id}/resolve", response_model=DLQResponse)
async def resolve_dlq(
    dlq_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DLQResponse:
    """Mark a DLQ entry as resolved."""
    from datetime import datetime, timezone
    result = await db.execute(
        select(DeadLetterQueue).where(DeadLetterQueue.id == dlq_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")

    entry.resolved = True
    entry.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(entry)
    return entry