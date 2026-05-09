import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.engine.ai_processor import process_ai_step
from app.engine.cost_tracker import record_step_cost, update_run_totals
from app.engine.trigger_normalizer import envelope_to_input_text
from app.models.run import Run, RunStep
from app.models.workflow import Workflow, WorkflowVersion


async def _create_step(
    db: AsyncSession,
    run_id: uuid.UUID,
    step_type: str,
    step_order: int,
    input_payload: dict,
) -> RunStep:
    """Create a run step row in pending state."""
    step = RunStep(
        run_id=run_id,
        step_type=step_type,
        step_order=step_order,
        status="running",
        input_payload=input_payload,
        started_at=datetime.now(timezone.utc),
    )
    db.add(step)
    await db.flush()
    return step


async def _complete_step(
    db: AsyncSession,
    step: RunStep,
    output_payload: dict,
) -> None:
    """Mark a step as completed with its output."""
    step.status = "completed"
    step.output_payload = output_payload
    step.completed_at = datetime.now(timezone.utc)
    await db.flush()


async def _fail_step(
    db: AsyncSession,
    step: RunStep,
    error: str,
) -> None:
    """Mark a step as failed with error details."""
    step.status = "failed"
    step.error_details = {"error": error}
    step.completed_at = datetime.now(timezone.utc)
    await db.flush()


async def execute_run(run_id: uuid.UUID) -> None:
    """
    Execute a run end-to-end.
    Phase 5 scope: trigger_normalize + ai_process steps only.
    Action dispatch added in Phase 6.

    State machine:
    pending → running → (steps execute) → completed | failed
    """
    async with AsyncSessionLocal() as db:
        # Load run
        result = await db.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            return

        # Load workflow version
        result = await db.execute(
            select(WorkflowVersion).where(
                WorkflowVersion.workflow_id == run.workflow_id,
                WorkflowVersion.version_number == run.version_number,
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            run.status = "failed"
            run.error_message = "Workflow version not found"
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        definition = version.definition
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        await db.flush()

        try:
            # ── STEP 1: Trigger Normalize ─────────────────────────
            step1 = await _create_step(
                db=db,
                run_id=run_id,
                step_type="trigger_normalize",
                step_order=1,
                input_payload=run.trigger_payload,
            )

            envelope = run.trigger_payload  # Already normalized at trigger time
            input_text = envelope_to_input_text(envelope)

            await _complete_step(db, step1, {"envelope": envelope, "input_text": input_text})

            # ── STEP 2: AI Process ────────────────────────────────
            ai_step_def = definition.get("ai_step", {})
            task_type = ai_step_def.get("task_type", "classify_and_summarize")
            model = ai_step_def.get("model", "gpt-4o-mini")
            output_schema = ai_step_def.get("output_schema", {})
            few_shot_examples = ai_step_def.get("few_shot_examples")

            step2 = await _create_step(
                db=db,
                run_id=run_id,
                step_type="ai_process",
                step_order=2,
                input_payload={"input_text": input_text, "task_type": task_type},
            )

            ai_result = await process_ai_step(
                db=db,
                task_type=task_type,
                input_text=input_text,
                output_schema=output_schema,
                model=model,
                few_shot_examples=few_shot_examples,
            )

            await record_step_cost(
                db=db,
                run_step_id=step2.id,
                prompt_tokens=ai_result["prompt_tokens"],
                completion_tokens=ai_result["completion_tokens"],
                cost_usd=ai_result["cost_usd"],
                model=ai_result["model"],
            )

            await _complete_step(db, step2, {
                "ai_output": ai_result["output"],
                "attempts": ai_result["attempts"],
                "raw_response": ai_result["raw_response"],
            })

            # ── FINALIZE RUN ──────────────────────────────────────
            await update_run_totals(db, run_id)
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise