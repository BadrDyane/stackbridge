import uuid
from typing import Any
from pydantic import BaseModel


class IntegrationResponse(BaseModel):
    id: uuid.UUID
    platform: str
    display_name: str
    platform_account_id: str | None
    scopes: list[str]
    is_active: bool
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class AuthUrlResponse(BaseModel):
    auth_url: str
    platform: str