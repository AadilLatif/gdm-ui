"""Inline simulation execution helpers."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np
from fastapi.concurrency import run_in_threadpool
from scipy.sparse import spmatrix

from fgc_flow_api.models import Model
from fgc_flow_api.schemas.simulations import (
    SimulationRequest,
    SimulationResponse,
    SimulationSolverName,
    SolverConfig,
)


def _json_key(value: Any) -> str:
    if isinstance(value, tuple):
        return "|".join(_json_key(item) for item in value)
    return str(value)


def _serialize_value(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: _serialize_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, np.ndarray):
        return [_serialize_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _serialize_value(value.item())
    if isinstance(value, spmatrix):
        return [_serialize_value(item) for item in value.toarray().tolist()]
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if isinstance(value, dict):
        return {_json_key(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _serialize_solver_result(result: Any) -> dict[str, Any]:
    return _serialize_value(result)


def _ac_kwargs(config):
    return dict(
        include_loads=config.include_loads,
        include_solar=config.include_solar,
        include_battery=config.include_battery,
        include_capacitor=config.include_capacitor,
        include_regulator_targets=config.include_regulator_targets,
        include_regulator_limits=config.include_regulator_limits,
        load_scale=config.load_scale,
        solar_scale=config.solar_scale,
        battery_scale=config.battery_scale,
        capacitor_scale=config.capacitor_scale,
        slack_label=config.slack_label,
        include_neutral=config.include_neutral,
        include_shunt=config.include_shunt,
        convert_geometry_to_matrix=config.convert_geometry_to_matrix,
        vm_min_pu=config.vm_min_pu,
        vm_max_pu=config.vm_max_pu,
        voltage_reg_weight=config.voltage_reg_weight,
        voltage_target_weight=config.voltage_target_weight,
        mismatch_scale_floor_w=config.mismatch_scale_floor_w,
        max_nfev=config.max_nfev,
    )


def _dc_kwargs(config):
    return dict(
        include_solar_generators=config.include_solar_generators,
        include_battery_generators=config.include_battery_generators,
        include_loads=config.include_loads,
        include_slack_generator=config.include_slack_generator,
        slack_label=config.slack_label,
        slack_cost_linear=config.slack_cost_linear,
        include_neutral=config.include_neutral,
        include_shunt=config.include_shunt,
        convert_geometry_to_matrix=config.convert_geometry_to_matrix,
        theta_min_rad=config.theta_min_rad,
        theta_max_rad=config.theta_max_rad,
        theta_penalty=config.theta_penalty,
        maxiter=config.maxiter,
    )


def _lindistflow_kwargs(config):
    return dict(
        include_loads=config.include_loads,
        include_solar=config.include_solar,
        include_battery=config.include_battery,
        include_capacitor=config.include_capacitor,
        load_scale=config.load_scale,
        solar_scale=config.solar_scale,
        battery_scale=config.battery_scale,
        capacitor_scale=config.capacitor_scale,
        include_neutral=config.include_neutral,
        include_open_switches=config.include_open_switches,
    )


async def run_simulation_request(model: Model, body: SimulationRequest) -> SimulationResponse:
    if body.solver == SimulationSolverName.AC_OPF:
        result = await run_in_threadpool(_run_ac_opf, model, body)
    elif body.solver == SimulationSolverName.DC_OPF:
        result = await run_in_threadpool(_run_dc_opf, model, body)
    else:
        result = await run_in_threadpool(_run_lindistflow, model, body)
    return SimulationResponse(model_id=model.id, solver=body.solver, config=body.config, result=result)


def _load_system(model: Model):
    from gdm.distribution import DistributionSystem

    return DistributionSystem.from_json(Path(model.file_path))


def _run_ac_opf(model: Model, body: SimulationRequest, system: Any | None = None) -> dict[str, Any]:
    from fgc_flow import optimize_ac_power_flow_from_components

    if system is None:
        system = _load_system(model)
    result = optimize_ac_power_flow_from_components(system, **_ac_kwargs(body.config.ac))
    return {
        "solver": body.solver.value,
        "model_id": model.id,
        "config": body.config.model_dump(mode="json"),
        "result": _serialize_solver_result(result),
    }


def _run_dc_opf(model: Model, body: SimulationRequest, system: Any | None = None) -> dict[str, Any]:
    from fgc_flow import solve_dc_opf_from_components

    if system is None:
        system = _load_system(model)
    result = solve_dc_opf_from_components(system, **_dc_kwargs(body.config.dc))
    return {
        "solver": body.solver.value,
        "model_id": model.id,
        "config": body.config.model_dump(mode="json"),
        "result": _serialize_solver_result(result),
    }


def _run_lindistflow(model: Model, body: SimulationRequest, system: Any | None = None) -> dict[str, Any]:
    from fgc_flow import build_lindistflow_net_injections_from_components, solve_lindistflow

    if system is None:
        system = _load_system(model)
    kwargs = _lindistflow_kwargs(body.config.lindistflow)
    p_net, q_net = build_lindistflow_net_injections_from_components(
        system,
        include_loads=kwargs["include_loads"],
        include_solar=kwargs["include_solar"],
        include_battery=kwargs["include_battery"],
        include_capacitor=kwargs["include_capacitor"],
        load_scale=kwargs["load_scale"],
        solar_scale=kwargs["solar_scale"],
        battery_scale=kwargs["battery_scale"],
        capacitor_scale=kwargs["capacitor_scale"],
    )
    result = solve_lindistflow(
        system,
        p_net_w=p_net,
        q_net_var=q_net,
        include_neutral=kwargs["include_neutral"],
        include_open_switches=kwargs["include_open_switches"],
    )
    return {
        "solver": body.solver.value,
        "model_id": model.id,
        "config": body.config.model_dump(mode="json"),
        "result": _serialize_solver_result(result),
    }


def _compare_summary(ac: dict[str, Any], dc: dict[str, Any], lindistflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "ac_success": ac["success"],
        "dc_success": dc["success"],
        "lindistflow_success": lindistflow["success"],
        "ac_source_p_w": ac["source_injection"]["p_w"],
        "dc_slack_injection_w": dc["slack_injection_w"],
        "ldf_source_bus": lindistflow["source_bus"],
    }


async def run_compare(model: Model, config: SolverConfig) -> dict[str, Any]:
    system = await run_in_threadpool(_load_system, model)

    ac_body = SimulationRequest(model_id=model.id, solver=SimulationSolverName.AC_OPF, config=config)
    dc_body = SimulationRequest(model_id=model.id, solver=SimulationSolverName.DC_OPF, config=config)
    ldf_body = SimulationRequest(model_id=model.id, solver=SimulationSolverName.LINDISTFLOW, config=config)

    ac = await run_in_threadpool(_run_ac_opf, model, ac_body, system)
    dc = await run_in_threadpool(_run_dc_opf, model, dc_body, system)
    lindistflow = await run_in_threadpool(_run_lindistflow, model, ldf_body, system)

    return {
        "model_id": model.id,
        "ac": ac,
        "dc": dc,
        "lindistflow": lindistflow,
        "summary": _compare_summary(ac, dc, lindistflow),
    }
