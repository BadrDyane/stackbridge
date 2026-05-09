import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
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
    """
    Manually trigger a workflow run.
    Creates a run row, executes synchronously, returns the completed run.
    """
    # Verify workflow exists and belongs to user
    try:
        workflow = await workflow_service.get_workflow(db, payload.workflow_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    # Normalize trigger payload into envelope
    envelope = normalize_manual_trigger(payload.payload, str(payload.workflow_id))

    # Create run row
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

    # Execute synchronously (Phase 5 — no background task yet)
    try:
        await execute_run(run.id)
    except Exception:
        pass  # Error is persisted in run.status and run.error_message

    # Reload run with steps
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
) -> list[RunResponse]:
    """List all runs for workflows owned by the current user."""
    # Get all workflow IDs for this user
    wf_result = await db.execute(
        select(Workflow.id).where(Workflow.user_id == current_user.id)
    )
    workflow_ids = [row[0] for row in wf_result.all()]

    if not workflow_ids:
        return []

    result = await db.execute(
        select(Run)
        .where(Run.workflow_id.in_(workflow_ids))
        .order_by(Run.created_at.desc())
        .limit(50)
    )
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

    # Verify ownership via workflow
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