import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
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
    """Save a new version of an existing workflow from a YAML body."""
    yaml_source = (await request.body()).decode("utf-8")
    if not yaml_source.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body is empty")

    try:
        version = await workflow_service.create_new_version(db, workflow_id, current_user.id, yaml_source)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
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
    """Validate a YAML workflow definition without saving it."""
    yaml_source = (await request.body()).decode("utf-8")
    if not yaml_source.strip():
        return ValidateResponse(valid=False, errors=["Request body is empty"])

    try:
        definition = workflow_service.parse_and_validate_yaml(yaml_source)
        return ValidateResponse(valid=True, parsed=definition.model_dump())
    except (ValueError, ValidationError) as e:
        return ValidateResponse(valid=False, errors=[str(e)])