import uuid
from typing import Any
from pydantic import BaseModel


class TriggerConfigUpsert(BaseModel):
    integration_id: uuid.UUID | None = None
    polling_interval_s: int = 300
    gmail_query_filter: str | None = None
    schedule_cron: str | None = None
    extra_config: dict | None = None


class TriggerConfigResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    integration_id: uuid.UUID | None
    polling_interval_s: int | None
    last_polled_at: Any
    gmail_query_filter: str | None
    gmail_history_id: str | None
    schedule_cron: str | None

    model_config = {"from_attributes": True}


class ActionConfigUpsert(BaseModel):
    integration_id: uuid.UUID
    action_type: str
    config: dict


class ActionConfigResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    integration_id: uuid.UUID
    action_type: str
    config: dict

    model_config = {"from_attributes": True}