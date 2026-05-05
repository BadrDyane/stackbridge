import re
import uuid
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────
# TRIGGER SCHEMAS
# ─────────────────────────────────────────────

class TriggerConfig(BaseModel):
    type: Literal["polling", "manual", "scheduled", "webhook"]
    platform: str | None = None
    integration_id: str | None = None
    filter: str | None = None
    interval_seconds: int = 300
    cron: str | None = None

    @model_validator(mode="after")
    def validate_trigger_fields(self) -> "TriggerConfig":
        """Enforce required fields per trigger type."""
        if self.type == "polling":
            if not self.platform:
                raise ValueError("trigger.platform is required when type is 'polling'")
            if not self.integration_id:
                raise ValueError("trigger.integration_id is required when type is 'polling'")
        if self.type == "scheduled":
            if not self.cron:
                raise ValueError("trigger.cron is required when type is 'scheduled'")
            parts = self.cron.strip().split()
            if len(parts) != 5:
                raise ValueError("trigger.cron must be a valid 5-field cron expression")
        return self


# ─────────────────────────────────────────────
# AI STEP SCHEMAS
# ─────────────────────────────────────────────

class OutputFieldSpec(BaseModel):
    type: Literal["string", "integer", "boolean", "array"]
    enum: list[str] | None = None
    description: str | None = None


class FewShotExample(BaseModel):
    input: str
    output: dict[str, Any]


class AIStepConfig(BaseModel):
    task_type: Literal["classify_and_summarize", "extract_fields", "generate_content"]
    model: str = "gpt-4o-mini"
    output_schema: dict[str, OutputFieldSpec]
    few_shot_examples: list[FewShotExample] | None = None

    @field_validator("output_schema")
    @classmethod
    def validate_output_schema(cls, v: dict[str, OutputFieldSpec]) -> dict[str, OutputFieldSpec]:
        """Enforce at least one field and valid Python identifiers as keys."""
        if not v:
            raise ValueError("ai_step.output_schema must define at least one field")
        identifier_pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
        for field_name in v:
            if not identifier_pattern.match(field_name):
                raise ValueError(
                    f"output_schema field name '{field_name}' must be a valid Python identifier"
                )
        return v


# ─────────────────────────────────────────────
# ACTION SCHEMAS
# ─────────────────────────────────────────────

class SlackPostConfig(BaseModel):
    channel: str
    template: str


class NotionCreatePageConfig(BaseModel):
    parent_page_id: str
    title_template: str
    body_template: str


class GmailSendConfig(BaseModel):
    to_template: str
    subject_template: str
    body_template: str


class SimpleAction(BaseModel):
    type: Literal["slack_post", "notion_create_page", "gmail_send"]
    integration_id: str
    config: dict[str, Any]

    @model_validator(mode="after")
    def validate_config_for_type(self) -> "SimpleAction":
        """Validate config fields based on action type."""
        if self.type == "slack_post":
            SlackPostConfig(**self.config)
        elif self.type == "notion_create_page":
            NotionCreatePageConfig(**self.config)
        elif self.type == "gmail_send":
            GmailSendConfig(**self.config)
        return self


class BranchCase(BaseModel):
    when: str | int | bool
    action: SimpleAction


class BranchingAction(BaseModel):
    condition_field: str
    branches: list[BranchCase]
    default_action: SimpleAction | None = None


class ActionConfig(BaseModel):
    """Either a simple action or a branching action — not both."""
    type: Literal["slack_post", "notion_create_page", "gmail_send"] | None = None
    integration_id: str | None = None
    config: dict[str, Any] | None = None
    branching: BranchingAction | None = None

    @model_validator(mode="after")
    def validate_action_structure(self) -> "ActionConfig":
        """Either simple action fields or branching must be present."""
        has_simple = self.type is not None
        has_branching = self.branching is not None
        if not has_simple and not has_branching:
            raise ValueError("action must define either 'type' (simple action) or 'branching'")
        if has_simple and has_branching:
            raise ValueError("action cannot define both 'type' and 'branching'")
        if has_simple:
            if not self.integration_id:
                raise ValueError("action.integration_id is required for simple actions")
            if self.config is None:
                raise ValueError("action.config is required for simple actions")
            # Validate config shape
            if self.type == "slack_post":
                SlackPostConfig(**self.config)
            elif self.type == "notion_create_page":
                NotionCreatePageConfig(**self.config)
            elif self.type == "gmail_send":
                GmailSendConfig(**self.config)
        return self


# ─────────────────────────────────────────────
# TOP-LEVEL WORKFLOW DEFINITION
# ─────────────────────────────────────────────

class WorkflowDefinition(BaseModel):
    """The parsed and validated YAML workflow definition."""
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    version: str | None = None
    trigger: TriggerConfig
    ai_step: AIStepConfig
    action: ActionConfig

    @field_validator("name")
    @classmethod
    def name_no_newlines(cls, v: str) -> str:
        if "\n" in v:
            raise ValueError("name must not contain newlines")
        return v


# ─────────────────────────────────────────────
# REQUEST / RESPONSE SCHEMAS
# ─────────────────────────────────────────────

class WorkflowCreateRequest(BaseModel):
    yaml_source: str


class WorkflowResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    current_version: int
    trigger_type: str
    trigger_platform: str | None
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class WorkflowVersionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    version_number: int
    yaml_source: str
    definition: dict
    created_at: Any

    model_config = {"from_attributes": True}


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str] | None = None
    parsed: dict | None = None