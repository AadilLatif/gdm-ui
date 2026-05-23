"""Simulation endpoints for fgc_flow_api."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from fgc_flow_api.database import get_flow_db
from fgc_flow_api.dependencies import get_current_user
from fgc_flow_api.schemas.simulations import (
    SimulationDispatchResponse,
    SimulationBatchRequest,
    SimulationBatchResponse,
    SimulationCompareRequest,
    SimulationCompareResponse,
    SimulationRequest,
    SimulationResponse,
    SimulationSolverName,
)
from fgc_flow_api.services.model_service import get_model_for_user
from fgc_flow_api.services.batch_jobs import create_batch_jobs, expand_parameter_grid
from fgc_flow_api.services.solver_runner import run_compare, run_simulation_request
from fgc_flow_api.services.simulation_jobs import QUEUE_THRESHOLD_SECONDS, estimate_runtime_seconds, submit_simulation_job
from fgc_flow_api.database import get_jobs_db

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


async def _run_simulation(
    expected_solver: SimulationSolverName,
    body: SimulationRequest,
    user,
    flow_db: AsyncSession,
    jobs_db: AsyncSession,
) -> SimulationDispatchResponse:
    if body.solver != expected_solver:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solver does not match endpoint")
    model = await get_model_for_user(flow_db, user.id, body.model_id)
    if estimate_runtime_seconds(body) <= QUEUE_THRESHOLD_SECONDS:
        result = await run_simulation_request(model, body)
        return SimulationDispatchResponse(
            execution_mode="inline",
            status="SUCCESS",
            model_id=result.model_id,
            solver=result.solver,
            config=result.config,
            result=result.result,
        )
    return await submit_simulation_job(jobs_db, user.id, body)


@router.post("/compare", response_model=SimulationCompareResponse)
async def compare_simulations(
    body: SimulationCompareRequest,
    user=Depends(get_current_user),
    flow_db: AsyncSession = Depends(get_flow_db),
):
    model = await get_model_for_user(flow_db, user.id, body.model_id)
    return await run_compare(model, body.config)


@router.post("/batch", response_model=SimulationBatchResponse)
async def batch_simulations(
    body: SimulationBatchRequest,
    user=Depends(get_current_user),
    flow_db: AsyncSession = Depends(get_flow_db),
    jobs_db: AsyncSession = Depends(get_jobs_db),
):
    try:
        sweep_points = expand_parameter_grid(body.parameter_grid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    model = await get_model_for_user(flow_db, user.id, body.model_id)

    try:
        jobs = await create_batch_jobs(jobs_db, user.id, model.id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SimulationBatchResponse(
        model_id=body.model_id,
        solver=body.solver,
        queued_jobs=len(jobs),
        job_ids=[job.id for job in jobs],
        sweep_points=sweep_points,
        parameter_grid=body.parameter_grid,
    )


@router.post("/ac-opf", response_model=SimulationDispatchResponse)
async def run_ac_opf(
    body: SimulationRequest,
    user=Depends(get_current_user),
    flow_db: AsyncSession = Depends(get_flow_db),
    jobs_db: AsyncSession = Depends(get_jobs_db),
):
    return await _run_simulation(SimulationSolverName.AC_OPF, body, user, flow_db, jobs_db)


@router.post("/dc-opf", response_model=SimulationDispatchResponse)
async def run_dc_opf(
    body: SimulationRequest,
    user=Depends(get_current_user),
    flow_db: AsyncSession = Depends(get_flow_db),
    jobs_db: AsyncSession = Depends(get_jobs_db),
):
    return await _run_simulation(SimulationSolverName.DC_OPF, body, user, flow_db, jobs_db)


@router.post("/lindistflow", response_model=SimulationDispatchResponse)
async def run_lindistflow(
    body: SimulationRequest,
    user=Depends(get_current_user),
    flow_db: AsyncSession = Depends(get_flow_db),
    jobs_db: AsyncSession = Depends(get_jobs_db),
):
    return await _run_simulation(SimulationSolverName.LINDISTFLOW, body, user, flow_db, jobs_db)
