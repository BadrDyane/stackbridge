import uuid
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class Workflow(Base):
    """Live canonical workflow record."""

    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    trigger_type: Mapped[str] = mapped_column(String, nullable=False)
    trigger_platform: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorkflowVersion(Base):
    """Immutable snapshot of a workflow definition."""

    __tablename__ = "workflow_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    yaml_source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class TriggerConfig(Base):
    """Trigger-specific configuration per workflow."""

    __tablename__ = "trigger_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, unique=True)
    integration_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("integrations.id"), nullable=True)
    polling_interval_s: Mapped[int | None] = mapped_column(Integer, nullable=True, default=300)
    last_polled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gmail_query_filter: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_history_id: Mapped[str | None] = mapped_column(String, nullable=True)
    webhook_path: Mapped[str | None] = mapped_column(String, nullable=True)
    schedule_cron: Mapped[str | None] = mapped_column(String, nullable=True)
    extra_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ActionConfig(Base):
    """Action configuration per workflow."""

    __tablename__ = "action_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    integration_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("integrations.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)