"""Model lookup helpers for uploaded simulation assets."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fgc_flow_api.models import Model


async def get_model_for_user(db: AsyncSession, user_id: str, model_id: str) -> Model:
    result = await db.execute(select(Model).where(Model.id == model_id, Model.user_id == user_id))
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return model
