import uuid
from typing import Any
from pydantic import BaseModel


class TriggerRunRequest(BaseModel):
    workflow_id: uuid.UUID
    payload: dict[str, Any]
    dry_run: bool = False


class RunStepResponse(BaseModel):
    id: uuid.UUID
    step_type: str
    step_order: int
    status: str
    input_payload: dict | None
    output_payload: dict | None
    model_used: str | None
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    attempt_count: int
    error_details: dict | None
    started_at: Any
    completed_at: Any

    model_config = {"from_attributes": True}


class RunResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    version_number: int
    status: str
    trigger_source: str
    is_dry_run: bool
    error_message: str | None
    total_cost_usd: float
    total_tokens: int
    started_at: Any
    completed_at: Any
    created_at: Any
    steps: list[RunStepResponse] = []

    model_config = {"from_attributes": True}