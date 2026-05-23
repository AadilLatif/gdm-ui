"""Job queue ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from fgc_flow_api.database import JobsBase


class Job(JobsBase):
    __tablename__ = "job"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_version_id: Mapped[str] = mapped_column(String, ForeignKey("cached_result.model_version_id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING", index=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    status_events: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    result_path: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
