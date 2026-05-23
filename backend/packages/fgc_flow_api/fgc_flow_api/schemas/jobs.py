"""Queue API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobSubmissionRequest(BaseModel):
    model_version_id: str = Field(..., min_length=1)
    job_type: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class JobSubmissionResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    model_version_id: str
    job_type: str
    params: dict[str, Any]
    status_events: list[dict[str, Any]]
    retry_count: int
    next_retry_at: datetime | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result_path: str | None = None


class JobResultResponse(BaseModel):
    job_id: str
    result_json: dict[str, Any] | None = None
    result_path: str | None = None
