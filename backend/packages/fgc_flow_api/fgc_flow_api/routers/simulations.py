"""Simulation endpoints for fgc_flow_api."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from fgc_flow_api.database import get_flow_db
from fgc_flow_api.dependencies import get_current_user
from fgc_flow_api.schemas.simulations import SimulationRequest, SimulationResponse, SimulationSolverName
from fgc_flow_api.services.model_service import get_model_for_user
from fgc_flow_api.services.solver_runner import run_simulation_request

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


async def _run_simulation(
    expected_solver: SimulationSolverName,
    body: SimulationRequest,
    user,
    db: AsyncSession,
) -> SimulationResponse:
    if body.solver != expected_solver:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solver does not match endpoint")
    model = await get_model_for_user(db, user.id, body.model_id)
    return await run_simulation_request(model, body)


@router.post("/ac-opf", response_model=SimulationResponse)
async def run_ac_opf(
    body: SimulationRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_flow_db),
):
    return await _run_simulation(SimulationSolverName.AC_OPF, body, user, db)


@router.post("/dc-opf", response_model=SimulationResponse)
async def run_dc_opf(
    body: SimulationRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_flow_db),
):
    return await _run_simulation(SimulationSolverName.DC_OPF, body, user, db)


@router.post("/lindistflow", response_model=SimulationResponse)
async def run_lindistflow(
    body: SimulationRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_flow_db),
):
    return await _run_simulation(SimulationSolverName.LINDISTFLOW, body, user, db)
