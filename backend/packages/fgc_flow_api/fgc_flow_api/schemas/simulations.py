"""Pydantic contracts for simulation requests and responses."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class SimulationSolverName(str, Enum):
    AC_OPF = "ac-opf"
    DC_OPF = "dc-opf"
    LINDISTFLOW = "lindistflow"


class ACSolverConfig(BaseModel):
    include_loads: bool = True
    include_solar: bool = True
    include_battery: bool = False
    include_capacitor: bool = True
    include_regulator_targets: bool = True
    include_regulator_limits: bool = True
    load_scale: float = 1.0
    solar_scale: float = 1.0
    battery_scale: float = 1.0
    capacitor_scale: float = 1.0
    slack_label: list[tuple[str, str]] | None = None
    include_neutral: bool = False
    include_shunt: bool = False
    convert_geometry_to_matrix: bool = True
    vm_min_pu: float = 0.95
    vm_max_pu: float = 1.05
    voltage_reg_weight: float = 1e-3
    voltage_target_weight: float = 1.0
    mismatch_scale_floor_w: float = 1e3
    max_nfev: int = Field(300, gt=0)


class DCSolverConfig(BaseModel):
    include_solar_generators: bool = True
    include_battery_generators: bool = True
    include_loads: bool = True
    include_slack_generator: bool = True
    slack_label: list[tuple[str, str]] | None = None
    slack_cost_linear: float = 50.0
    include_neutral: bool = False
    include_shunt: bool = False
    convert_geometry_to_matrix: bool = True
    theta_min_rad: float = -1.5707963267948966
    theta_max_rad: float = 1.5707963267948966
    theta_penalty: float = 1e-6
    maxiter: int = Field(500, gt=0)


class LinDistFlowConfig(BaseModel):
    include_loads: bool = True
    include_solar: bool = True
    include_battery: bool = True
    include_capacitor: bool = True
    load_scale: float = 1.0
    solar_scale: float = 1.0
    battery_scale: float = 1.0
    capacitor_scale: float = 1.0
    include_neutral: bool = False
    include_open_switches: bool = False


class SolverConfig(BaseModel):
    tolerance: float = Field(1e-6, gt=0)
    max_iter: int = Field(300, gt=0)
    verbose: bool = False
    ac: ACSolverConfig = Field(default_factory=ACSolverConfig)
    dc: DCSolverConfig = Field(default_factory=DCSolverConfig)
    lindistflow: LinDistFlowConfig = Field(default_factory=LinDistFlowConfig)


class SimulationRequest(BaseModel):
    model_id: str = Field(..., min_length=1)
    solver: SimulationSolverName
    config: SolverConfig = Field(default_factory=SolverConfig)


class SimulationResponse(BaseModel):
    model_id: str
    solver: SimulationSolverName
    config: SolverConfig
    result: dict[str, Any]


class SimulationDispatchResponse(BaseModel):
    execution_mode: Literal["inline", "queued"]
    status: str
    model_id: str
    solver: SimulationSolverName
    config: SolverConfig
    job_id: str | None = None
    result: dict[str, Any] | None = None
    result_path: str | None = None
