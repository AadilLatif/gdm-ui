"""Lightweight placeholder solvers for local development."""

from typing import Any


def optimize_ac_power_flow_from_components(system: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "success": True,
        "source_injection": {"p_w": 0.0, "q_var": 0.0},
        "result": {"voltage": 1.0, "current": 0.0},
    }


def solve_dc_opf_from_components(system: Any, **kwargs: Any) -> dict[str, Any]:
    return {"success": True, "slack_injection_w": 0.0, "result": {"theta": 0.0}}


def build_lindistflow_net_injections_from_components(system: Any, **kwargs: Any) -> tuple[list[float], list[float]]:
    size = kwargs.get("include_loads", False) + kwargs.get("include_solar", False)
    return [0.0] * (size or 1), [0.0] * (size or 1)


def solve_lindistflow(system: Any, *, p_net_w: list[float], q_net_var: list[float], **_kwargs: Any) -> dict[str, Any]:
    return {"success": True, "source_bus": "source", "p_net": p_net_w, "q_net": q_net_var}
