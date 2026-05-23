"""SQLite-backed cache helpers for queued jobs."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fgc_flow_api.models import CachedResult


def build_cache_key(model_version_id: str, params: dict) -> str:
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(f"{model_version_id}:{canonical}".encode()).hexdigest()


async def get_cached_result(db: AsyncSession, model_version_id: str, params: dict) -> CachedResult | None:
    params_hash = build_cache_key(model_version_id, params)
    result = await db.execute(
        select(CachedResult).where(
            CachedResult.model_version_id == model_version_id,
            CachedResult.params_hash == params_hash,
        )
    )
    return result.scalar_one_or_none()
