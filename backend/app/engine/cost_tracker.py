import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import Run, RunStep


async def record_step_cost(
    db: AsyncSession,
    run_step_id: uuid.UUID,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    model: str,
) -> None:
    """Update a run step with token usage and cost."""
    result = await db.execute(select(RunStep).where(RunStep.id == run_step_id))
    step = result.scalar_one_or_none()
    if not step:
        return

    step.prompt_tokens = prompt_tokens
    step.completion_tokens = completion_tokens
    step.cost_usd = cost_usd
    step.model_used = model
    await db.flush()


async def update_run_totals(db: AsyncSession, run_id: uuid.UUID) -> None:
    """Recalculate and update run-level token/cost totals from all steps."""
    result = await db.execute(select(RunStep).where(RunStep.run_id == run_id))
    steps = result.scalars().all()

    total_tokens = sum((s.prompt_tokens or 0) + (s.completion_tokens or 0) for s in steps)
    total_cost = sum(float(s.cost_usd or 0) for s in steps)

    run_result = await db.execute(select(Run).where(Run.id == run_id))
    run = run_result.scalar_one_or_none()
    if run:
        run.total_tokens = total_tokens
        run.total_cost_usd = total_cost
    await db.flush()