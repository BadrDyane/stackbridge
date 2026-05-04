import uuid
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class Run(Base):
    """Top-level workflow execution record."""

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    trigger_source: Mapped[str] = mapped_column(String, nullable=False)
    trigger_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RunStep(Base):
    """One step within a run execution."""

    __tablename__ = "run_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    step_type: Mapped[str] = mapped_column(String, nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    input_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)