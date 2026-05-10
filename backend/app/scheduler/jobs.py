import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.integrations.gmail.trigger import apply_filter, get_new_messages, normalize_message
from app.models.run import Run
from app.models.system import IdempotencyKey
from app.models.workflow import TriggerConfig as TriggerConfigModel, Workflow
from app.services.integration_service import get_valid_token


async def poll_gmail_workflow(workflow_id: str) -> None:
    """
    APScheduler job: poll Gmail for new messages and execute runs.
    """
    wf_id = uuid.UUID(workflow_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workflow).where(Workflow.id == wf_id, Workflow.is_active == True)
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            return

        result = await db.execute(
            select(TriggerConfigModel).where(TriggerConfigModel.workflow_id == wf_id)
        )
        trigger_config = result.scalar_one_or_none()
        if not trigger_config or not trigger_config.integration_id:
            return

        try:
            access_token = await get_valid_token(trigger_config.integration_id, db)
        except ValueError:
            return

        history_id = trigger_config.gmail_history_id
        if not history_id:
            return

        try:
            messages, latest_history_id = await get_new_messages(access_token, history_id)
        except Exception:
            return

        run_ids: list[uuid.UUID] = []

        for raw_message in messages:
            envelope = normalize_message(raw_message)
            message_id = envelope["event_id"]

            if not apply_filter(envelope, trigger_config.gmail_query_filter):
                continue

            idempotency_key = f"gmail:{message_id}"
            result = await db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.workflow_id == wf_id,
                    IdempotencyKey.key == idempotency_key,
                )
            )
            if result.scalar_one_or_none():
                continue

            run = Run(
                workflow_id=wf_id,
                version_number=workflow.current_version,
                status="pending",
                trigger_source="gmail_polling",
                trigger_payload=envelope,
                is_dry_run=False,
                started_at=datetime.now(timezone.utc),
            )
            db.add(run)
            await db.flush()

            ik = IdempotencyKey(
                workflow_id=wf_id,
                key=idempotency_key,
                run_id=run.id,
            )
            db.add(ik)
            run_ids.append(run.id)

        trigger_config.gmail_history_id = latest_history_id
        trigger_config.last_polled_at = datetime.now(timezone.utc)
        await db.commit()

    # Execute runs outside the polling DB session
    if run_ids:
        from app.engine.executor import execute_run
        for run_id in run_ids:
            try:
                await execute_run(run_id)
            except Exception:
                pass  # Error is persisted in run.status — don't crash the scheduler