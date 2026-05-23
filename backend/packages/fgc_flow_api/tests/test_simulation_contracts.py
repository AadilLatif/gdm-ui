from __future__ import annotations

from fgc_flow_api.schemas.simulations import SimulationRequest, SimulationSolverName, SolverConfig


def test_solver_config_exports_and_fields():
    fields = SolverConfig.model_fields
    assert {"tolerance", "max_iter", "verbose", "ac", "dc", "lindistflow"} <= set(fields)
    assert fields["max_iter"].default == 300
    assert fields["ac"].default_factory is not None


def test_solver_name_rejects_unknown_values():
    assert SimulationSolverName("ac-opf") == SimulationSolverName.AC_OPF
    try:
        SimulationSolverName("invalid-solver")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid solver name should fail validation")


def test_simulation_request_rejects_negative_iterations():
    try:
        SimulationRequest.model_validate(
            {
                "model_id": "model-1",
                "solver": "ac-opf",
                "config": {"tolerance": 1e-6, "max_iter": -1},
            }
        )
    except Exception:
        pass
    else:
        raise AssertionError("negative max_iter should fail validation")
