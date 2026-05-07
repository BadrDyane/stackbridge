import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.workflow import (
    ActionConfig as ActionConfigModel,
    TriggerConfig as TriggerConfigModel,
    Workflow,
)
from app.schemas.trigger_config import (
    ActionConfigResponse,
    ActionConfigUpsert,
    TriggerConfigResponse,
    TriggerConfigUpsert,
)
from app.schemas.workflow import (
    ValidateResponse,
    WorkflowResponse,
    WorkflowVersionResponse,
)
from app.services import workflow_service

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    """Create a new workflow from a YAML body."""
    yaml_source = (await request.body()).decode("utf-8")
    if not yaml_source.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body is empty")
    try:
        workflow = await workflow_service.create_workflow(db, current_user.id, yaml_source)
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return workflow


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowResponse]:
    """List all workflows for the authenticated user."""
    return await workflow_service.list_workflows(db, current_user.id)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    """Get a single workflow by ID."""
    try:
        return await workflow_service.get_workflow(db, workflow_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")


@router.post("/{workflow_id}/versions", response_model=WorkflowVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    workflow_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowVersionResponse:
    """Save a new version of an existing workflow."""
    yaml_source = (await request.body()).decode("utf-8")
    if not yaml_source.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body is empty")
    try:
        version = await workflow_service.create_new_version(db, workflow_id, current_user.id, yaml_source)
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return version


@router.get("/{workflow_id}/versions", response_model=list[WorkflowVersionResponse])
async def list_versions(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowVersionResponse]:
    """List all versions for a workflow."""
    try:
        return await workflow_service.get_workflow_versions(db, workflow_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")


@router.post("/validate", response_model=ValidateResponse)
async def validate_yaml(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ValidateResponse:
    """Validate YAML without saving."""
    yaml_source = (await request.body()).decode("utf-8")
    if not yaml_source.strip():
        return ValidateResponse(valid=False, errors=["Request body is empty"])
    try:
        definition = workflow_service.parse_and_validate_yaml(yaml_source)
        return ValidateResponse(valid=True, parsed=definition.model_dump())
    except (ValueError, ValidationError) as e:
        return ValidateResponse(valid=False, errors=[str(e)])


@router.patch("/{workflow_id}/trigger-config", response_model=TriggerConfigResponse)
async def upsert_trigger_config(
    workflow_id: uuid.UUID,
    payload: TriggerConfigUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TriggerConfigResponse:
    """Create or update the trigger configuration for a workflow."""
    try:
        workflow = await workflow_service.get_workflow(db, workflow_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    result = await db.execute(
        select(TriggerConfigModel).where(TriggerConfigModel.workflow_id == workflow_id)
    )
    trigger_config = result.scalar_one_or_none()

    if trigger_config:
        trigger_config.integration_id = payload.integration_id
        trigger_config.polling_interval_s = payload.polling_interval_s
        trigger_config.gmail_query_filter = payload.gmail_query_filter
        trigger_config.schedule_cron = payload.schedule_cron
        trigger_config.extra_config = payload.extra_config
    else:
        trigger_config = TriggerConfigModel(
            workflow_id=workflow_id,
            integration_id=payload.integration_id,
            polling_interval_s=payload.polling_interval_s,
            gmail_query_filter=payload.gmail_query_filter,
            schedule_cron=payload.schedule_cron,
            extra_config=payload.extra_config,
        )
        db.add(trigger_config)

    await db.commit()
    await db.refresh(trigger_config)
    return trigger_config


@router.patch("/{workflow_id}/action-config", response_model=ActionConfigResponse)
async def upsert_action_config(
    workflow_id: uuid.UUID,
    payload: ActionConfigUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ActionConfigResponse:
    """Create or update the action configuration for a workflow."""
    try:
        await workflow_service.get_workflow(db, workflow_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    result = await db.execute(
        select(ActionConfigModel).where(ActionConfigModel.workflow_id == workflow_id)
    )
    action_config = result.scalar_one_or_none()

    if action_config:
        action_config.integration_id = payload.integration_id
        action_config.action_type = payload.action_type
        action_config.config = payload.config
    else:
        action_config = ActionConfigModel(
            workflow_id=workflow_id,
            integration_id=payload.integration_id,
            action_type=payload.action_type,
            config=payload.config,
        )
        db.add(action_config)

    await db.commit()
    await db.refresh(action_config)
    return action_config


@router.post("/{workflow_id}/activate")
async def activate_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Activate a workflow. Schedules polling job if trigger type is polling."""
    try:
        workflow = await workflow_service.get_workflow(db, workflow_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    if workflow.is_active:
        return {"status": "already_active", "workflow_id": str(workflow_id)}

    # Load trigger config to seed historyId if Gmail polling
    if workflow.trigger_type == "polling":
        result = await db.execute(
            select(TriggerConfigModel).where(TriggerConfigModel.workflow_id == workflow_id)
        )
        trigger_config = result.scalar_one_or_none()
        if not trigger_config or not trigger_config.integration_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow has no trigger config — set it first via PATCH /trigger-config",
            )

        # Seed Gmail historyId if not already set
        if not trigger_config.gmail_history_id and trigger_config.integration_id:
            from app.services.integration_service import get_valid_token
            from app.integrations.gmail.oauth import GmailOAuthProvider
            try:
                access_token = await get_valid_token(trigger_config.integration_id, db)
                provider = GmailOAuthProvider()
                account_info = await provider.get_account_info(access_token)
                trigger_config.gmail_history_id = account_info.get("history_id")
                await db.flush()
            except Exception:
                pass  # Non-fatal — polling will skip if historyId is missing

        # Schedule polling job
        from app.scheduler.setup import get_scheduler
        from app.scheduler.jobs import poll_gmail_workflow
        scheduler = get_scheduler()
        job_id = f"gmail_poll_{workflow_id}"

        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        scheduler.add_job(
            poll_gmail_workflow,
            trigger="interval",
            seconds=trigger_config.polling_interval_s or 300,
            id=job_id,
            args=[str(workflow_id)],
            replace_existing=True,
        )

    workflow.is_active = True
    await db.commit()

    return {"status": "activated", "workflow_id": str(workflow_id)}


@router.post("/{workflow_id}/deactivate")
async def deactivate_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deactivate a workflow and remove its scheduler job if any."""
    try:
        workflow = await workflow_service.get_workflow(db, workflow_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    # Remove scheduler job if exists
    from app.scheduler.setup import get_scheduler
    scheduler = get_scheduler()
    job_id = f"gmail_poll_{workflow_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    workflow.is_active = False
    await db.commit()

    return {"status": "deactivated", "workflow_id": str(workflow_id)}