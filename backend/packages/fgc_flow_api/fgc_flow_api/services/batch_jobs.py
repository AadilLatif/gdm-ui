"""Batch sweep helpers for simulation jobs."""

from __future__ import annotations

from itertools import product
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from fgc_flow_api.models import Job
from fgc_flow_api.schemas.simulations import SimulationBatchRequest, SimulationRequest, SimulationSolverName
from fgc_flow_api.services.job_cache import build_cache_key

MAX_BATCH_COMBINATIONS = 100

_SOLVER_CONFIG_SECTION = {
    SimulationSolverName.AC_OPF: "ac",
    SimulationSolverName.DC_OPF: "dc",
    SimulationSolverName.LINDISTFLOW: "lindistflow",
}


def build_batch_cache_key(model_version_id: str, params: dict) -> str:
    return build_cache_key(model_version_id, params)


def expand_parameter_grid(parameter_grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not parameter_grid:
        raise ValueError("parameter_grid must contain at least one sweep dimension")

    keys = sorted(parameter_grid)
    values: list[list[Any]] = []
    for key in keys:
        options = list(parameter_grid[key])
        if not options:
            raise ValueError(f"parameter_grid[{key!r}] must contain at least one value")
        values.append(options)

    total = 1
    for options in values:
        total *= len(options)
    if total > MAX_BATCH_COMBINATIONS:
        raise ValueError(
            f"parameter_grid expands to {total} combinations; limit is {MAX_BATCH_COMBINATIONS}"
        )

    return [dict(zip(keys, combo, strict=True)) for combo in product(*values)]


def _solver_section_name(solver: SimulationSolverName) -> str:
    return _SOLVER_CONFIG_SECTION[solver]


def _build_sweep_request(body: SimulationBatchRequest, sweep_values: dict[str, Any]) -> SimulationRequest:
    payload = body.model_dump(mode="json")
    section_name = _solver_section_name(body.solver)
    solver_config = dict(payload["config"][section_name])

    for key, value in sweep_values.items():
        if key not in solver_config:
            raise ValueError(f"Unknown sweep parameter for {body.solver.value}: {key}")
        solver_config[key] = value

    payload["config"][section_name] = solver_config
    payload.pop("parameter_grid", None)
    return SimulationRequest.model_validate(payload)


def prepare_batch_requests(body: SimulationBatchRequest) -> list[tuple[dict[str, Any], SimulationRequest]]:
    requests: list[tuple[dict[str, Any], SimulationRequest]] = []
    for sweep_values in expand_parameter_grid(body.parameter_grid):
        request = _build_sweep_request(body, sweep_values)
        requests.append((sweep_values, request))
    return requests


async def create_batch_jobs(
    db: AsyncSession,
    user_id: str,
    model_version_id: str,
    body: SimulationBatchRequest,
) -> list[Job]:
    prepared = prepare_batch_requests(body)
    jobs: list[Job] = []

    for _sweep_values, request in prepared:
        params = request.model_dump(mode="json")
        job = Job(
            user_id=user_id,
            job_type=body.solver.value,
            model_version_id=model_version_id,
            status="PENDING",
            params=params,
            status_events=[{"status": "PENDING"}],
        )
        db.add(job)
        jobs.append(job)

    await db.commit()
    for job in jobs:
        await db.refresh(job)
    return jobs
