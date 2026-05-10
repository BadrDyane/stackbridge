import asyncio
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.branch_evaluator import evaluate_branch
from app.integrations.slack import action as slack_action
from app.integrations.notion import action as notion_action
from app.models.workflow import ActionConfig as ActionConfigModel
from app.services.integration_service import get_valid_token

# Registry of action executors
_ACTION_REGISTRY = {
    "slack_post": slack_action.execute,
    "notion_create_page": notion_action.execute,
}


def _resolve_action_config(
    workflow_definition: dict[str, Any],
    ai_output: dict[str, Any],
    db_action_config: ActionConfigModel | None,
) -> tuple[str, str, dict[str, Any]]:
    """
    Resolve the final action to execute.
    Handles simple actions and branching.
    Returns (action_type, integration_id, config).
    """
    action_def = workflow_definition.get("action", {})
    branching = action_def.get("branching")

    if branching:
        # Evaluate branch to get the winning action config
        resolved = evaluate_branch(branching, ai_output)
        action_type = resolved.get("type")
        integration_id = resolved.get("integration_id")
        config = resolved.get("config", {})
    else:
        action_type = action_def.get("type")
        integration_id = action_def.get("integration_id")
        config = action_def.get("config", {})

    # Override with DB action config if set (more specific than YAML)
    if db_action_config:
        action_type = db_action_config.action_type
        integration_id = str(db_action_config.integration_id)
        config = db_action_config.config

    if not action_type:
        raise ValueError("Could not resolve action_type from workflow definition")
    if not integration_id:
        raise ValueError("Could not resolve integration_id for action")

    return action_type, integration_id, config


async def dispatch_action(
    db: AsyncSession,
    workflow_definition: dict[str, Any],
    ai_output: dict[str, Any],
    workflow_id: uuid.UUID,
    run_step_id: uuid.UUID,
    is_dry_run: bool = False,
) -> dict[str, Any]:
    """
    Resolve and execute the workflow action.
    Retries up to 3 times with exponential backoff.
    In dry-run mode: logs the would-be payload without executing.
    Returns the action result dict.
    """
    # Load DB action config if available
    result = await db.execute(
        select(ActionConfigModel).where(ActionConfigModel.workflow_id == workflow_id)
    )
    db_action_config = result.scalar_one_or_none()

    action_type, integration_id_str, config = _resolve_action_config(
        workflow_definition, ai_output, db_action_config
    )

    integration_id = uuid.UUID(integration_id_str)

    # Dry-run: skip real execution
    if is_dry_run:
        from app.integrations.slack.action import _render_template
        rendered_text = _render_template(config.get("template", ""), ai_output)
        return {
            "dry_run": True,
            "would_have_sent": {
                "action_type": action_type,
                "integration_id": integration_id_str,
                "config": config,
                "rendered_output": rendered_text,
                "ai_output_used": ai_output,
            },
        }

    executor = _ACTION_REGISTRY.get(action_type)
    if not executor:
        raise ValueError(f"No executor registered for action_type: {action_type}")

    # Get valid token (handles refresh)
    access_token = await get_valid_token(integration_id, db)

    last_error: Exception | None = None

    for attempt in range(3):
        try:
            result = await executor(
                config=config,
                ai_output=ai_output,
                access_token=access_token,
                run_step_id=str(run_step_id),
            )
            return result
        except Exception as e:
            last_error = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    raise ValueError(f"Action dispatch failed after 3 attempts: {last_error}")