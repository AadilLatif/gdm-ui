"""Cached result ORM model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fgc_flow_api.database import JobsBase


class CachedResult(JobsBase):
    __tablename__ = "cached_result"
    __table_args__ = (
        UniqueConstraint("model_version_id", "params_hash", name="uq_cached_result_key"),
    )

    model_version_id: Mapped[str] = mapped_column(String, primary_key=True)
    params_hash: Mapped[str] = mapped_column(String, primary_key=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
