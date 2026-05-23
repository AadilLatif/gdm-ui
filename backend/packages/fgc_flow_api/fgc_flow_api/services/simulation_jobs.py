"""Async simulation dispatch and result persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fgc_flow_api.config import settings
from fgc_flow_api.models import CachedResult, Job
from fgc_flow_api.schemas.simulations import (
    SimulationDispatchResponse,
    SimulationRequest,
    SimulationResponse,
    SimulationSolverName,
)
from fgc_flow_api.services.job_cache import build_cache_key

QUEUE_THRESHOLD_SECONDS = 5.0


def build_simulation_params(body: SimulationRequest) -> dict[str, Any]:
    return {
        "model_id": body.model_id,
        "solver": body.solver.value,
        "config": body.config.model_dump(mode="json"),
    }


def _solver_base_seconds(solver: SimulationSolverName) -> float:
    return {
        SimulationSolverName.AC_OPF: 1.4,
        SimulationSolverName.DC_OPF: 1.0,
        SimulationSolverName.LINDISTFLOW: 0.7,
    }[solver]


def estimate_runtime_seconds(body: SimulationRequest) -> float:
    solver_factor = _solver_base_seconds(body.solver)
    iteration_factor = body.config.max_iter / 300.0
    return round(solver_factor + iteration_factor, 3)


def _result_file_path(job_id: str) -> Path:
    result_dir = settings.upload_dir / "simulation-results" / job_id
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir / "result.json"


async def submit_simulation_job(
    db: AsyncSession,
    user_id: str,
    body: SimulationRequest,
) -> SimulationDispatchResponse:
    params = build_simulation_params(body)
    job = Job(
        user_id=user_id,
        job_type=body.solver.value,
        model_version_id=body.model_id,
        status="PENDING",
        params=params,
        status_events=[{"status": "PENDING"}],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return SimulationDispatchResponse(
        execution_mode="queued",
        status=job.status,
        job_id=job.id,
        model_id=body.model_id,
        solver=body.solver,
        config=body.config,
    )


async def store_simulation_result(
    db: AsyncSession,
    job: Job,
    payload: SimulationResponse | dict[str, Any],
) -> str:
    response = payload.model_dump(mode="json") if isinstance(payload, SimulationResponse) else payload
    canonical_params = job.params if isinstance(job.params, dict) else {}
    params_hash = build_cache_key(job.model_version_id, canonical_params)
    result_path = _result_file_path(job.id)
    result_path.write_text(json.dumps(response, indent=2, sort_keys=True, default=str))

    result = await db.execute(
        select(CachedResult).where(
            CachedResult.model_version_id == job.model_version_id,
            CachedResult.params_hash == params_hash,
        )
    )
    cached_result = result.scalar_one_or_none()
    if cached_result is None:
        cached_result = CachedResult(
            model_version_id=job.model_version_id,
            params_hash=params_hash,
            result_json=response,
            result_path=str(result_path),
        )
    else:
        cached_result.result_json = response
        cached_result.result_path = str(result_path)
    db.add(cached_result)
    job.result_path = str(result_path)
    return str(result_path)
