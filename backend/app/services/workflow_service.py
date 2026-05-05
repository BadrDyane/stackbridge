import uuid
from typing import Any

import yaml
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowVersion
from app.schemas.workflow import WorkflowDefinition


def parse_and_validate_yaml(yaml_source: str) -> WorkflowDefinition:
    """
    Parse a YAML string and validate it against the WorkflowDefinition schema.
    Raises ValueError on YAML parse failure or ValidationError on schema failure.
    """
    try:
        raw = yaml.safe_load(yaml_source)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax: {e}")

    if not isinstance(raw, dict):
        raise ValueError("Workflow YAML must be a mapping (dict), not a scalar or list")

    return WorkflowDefinition(**raw)


async def create_workflow(
    db: AsyncSession,
    user_id: uuid.UUID,
    yaml_source: str,
) -> Workflow:
    """
    Parse YAML, validate, create workflow + first version row.
    Returns the created Workflow ORM object.
    """
    definition = parse_and_validate_yaml(yaml_source)

    workflow = Workflow(
        user_id=user_id,
        name=definition.name,
        description=definition.description,
        trigger_type=definition.trigger.type,
        trigger_platform=definition.trigger.platform,
        current_version=1,
        is_active=False,
    )
    db.add(workflow)
    await db.flush()  # Get workflow.id before creating version

    version = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=1,
        definition=definition.model_dump(),
        yaml_source=yaml_source,
        created_by=user_id,
    )
    db.add(version)
    await db.commit()
    await db.refresh(workflow)
    return workflow


async def create_new_version(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    user_id: uuid.UUID,
    yaml_source: str,
) -> WorkflowVersion:
    """
    Validate new YAML and create a new version for an existing workflow.
    Updates workflow.current_version and metadata.
    """
    definition = parse_and_validate_yaml(yaml_source)

    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.user_id == user_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise ValueError("Workflow not found")

    next_version = workflow.current_version + 1

    version = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=next_version,
        definition=definition.model_dump(),
        yaml_source=yaml_source,
        created_by=user_id,
    )
    db.add(version)

    workflow.current_version = next_version
    workflow.name = definition.name
    workflow.description = definition.description
    workflow.trigger_type = definition.trigger.type
    workflow.trigger_platform = definition.trigger.platform

    await db.commit()
    await db.refresh(version)
    return version


async def list_workflows(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[Workflow]:
    """Return all workflows owned by the user, newest first."""
    result = await db.execute(
        select(Workflow)
        .where(Workflow.user_id == user_id)
        .order_by(Workflow.created_at.desc())
    )
    return list(result.scalars().all())


async def get_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Workflow:
    """Return a single workflow, enforcing ownership."""
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.user_id == user_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise ValueError("Workflow not found")
    return workflow


async def get_workflow_versions(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[WorkflowVersion]:
    """Return all versions for a workflow, enforcing ownership."""
    # Verify ownership first
    await get_workflow(db, workflow_id, user_id)

    result = await db.execute(
        select(WorkflowVersion)
        .where(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version_number.desc())
    )
    return list(result.scalars().all())


async def get_current_version(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    user_id: uuid.UUID,
) -> WorkflowVersion:
    """Return the current active version of a workflow."""
    workflow = await get_workflow(db, workflow_id, user_id)

    result = await db.execute(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version_number == workflow.current_version,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise ValueError("Current version not found — data integrity issue")
    return version