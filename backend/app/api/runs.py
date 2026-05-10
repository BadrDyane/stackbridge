import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.engine.executor import execute_run
from app.engine.trigger_normalizer import normalize_manual_trigger
from app.models.run import Run, RunStep
from app.models.user import User
from app.models.workflow import Workflow
from app.schemas.run import RunResponse, RunStepResponse, TriggerRunRequest
from app.services import workflow_service

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("/trigger", response_model=RunResponse)
async def trigger_run(
    payload: TriggerRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Manually trigger a workflow run."""
    try:
        workflow = await workflow_service.get_workflow(db, payload.workflow_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    envelope = normalize_manual_trigger(payload.payload, str(payload.workflow_id))

    run = Run(
        workflow_id=payload.workflow_id,
        version_number=workflow.current_version,
        status="pending",
        trigger_source="manual",
        trigger_payload=envelope,
        is_dry_run=payload.dry_run,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    try:
        await execute_run(run.id)
    except Exception:
        pass

    result = await db.execute(select(Run).where(Run.id == run.id))
    run = result.scalar_one()

    steps_result = await db.execute(
        select(RunStep).where(RunStep.run_id == run.id).order_by(RunStep.step_order)
    )
    steps = steps_result.scalars().all()

    run_response = RunResponse.model_validate(run)
    run_response.steps = [RunStepResponse.model_validate(s) for s in steps]
    return run_response


@router.get("", response_model=list[RunResponse])
async def list_runs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    workflow_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> list[RunResponse]:
    """List runs. Optionally filter by workflow_id."""
    wf_result = await db.execute(
        select(Workflow.id).where(Workflow.user_id == current_user.id)
    )
    user_workflow_ids = [row[0] for row in wf_result.all()]

    if not user_workflow_ids:
        return []

    query = select(Run).where(Run.workflow_id.in_(user_workflow_ids))

    if workflow_id:
        if workflow_id not in user_workflow_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        query = query.where(Run.workflow_id == workflow_id)

    query = query.order_by(Run.created_at.desc()).limit(limit)
    result = await db.execute(query)
    runs = result.scalars().all()
    return [RunResponse.model_validate(r) for r in runs]


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Get a single run with all its steps."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    wf_result = await db.execute(
        select(Workflow).where(
            Workflow.id == run.workflow_id,
            Workflow.user_id == current_user.id,
        )
    )
    if not wf_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    steps_result = await db.execute(
        select(RunStep).where(RunStep.run_id == run_id).order_by(RunStep.step_order)
    )
    steps = steps_result.scalars().all()

    run_response = RunResponse.model_validate(run)
    run_response.steps = [RunStepResponse.model_validate(s) for s in steps]
    return run_response