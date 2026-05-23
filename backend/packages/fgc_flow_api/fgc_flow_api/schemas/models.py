"""Pydantic contracts for uploaded model metadata."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ModelUploadRequest(BaseModel):
    name: str = Field(..., min_length=1)


class ModelUploadResponse(BaseModel):
    model_id: str
    name: str
    file_size: int
    created_at: datetime


class ModelListItem(ModelUploadResponse):
    pass


ModelResponse = ModelUploadResponse
ModelListResponse = list[ModelListItem]
