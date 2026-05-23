from __future__ import annotations

import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


def test_run_compare_reuses_single_loaded_system(monkeypatch):
    from fgc_flow_api.schemas.simulations import SolverConfig
    from fgc_flow_api.services import solver_runner

    model = SimpleNamespace(id="model-1", file_path="/tmp/model.json")
    system = object()
    calls: list[tuple[str, object]] = []

    async def _fake_threadpool(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _fake_load_system(model_arg):
        calls.append(("load", model_arg))
        return system

    def _fake_ac(model_arg, body_arg, system_arg=None):
        assert system_arg is system
        calls.append(("ac", body_arg.solver.value))
        return {"success": True, "source_injection": {"p_w": 12.5}, "source_bus": "source"}

    def _fake_dc(model_arg, body_arg, system_arg=None):
        assert system_arg is system
        calls.append(("dc", body_arg.solver.value))
        return {"success": False, "slack_injection_w": 7.25, "source_injection": {"p_w": 0.0}, "source_bus": "source"}

    def _fake_ldf(model_arg, body_arg, system_arg=None):
        assert system_arg is system
        calls.append(("lindistflow", body_arg.solver.value))
        return {"success": True, "source_bus": "source", "source_injection": {"p_w": 0.0}, "slack_injection_w": 0.0}

    monkeypatch.setattr(solver_runner, "run_in_threadpool", _fake_threadpool)
    monkeypatch.setattr(solver_runner, "_load_system", _fake_load_system)
    monkeypatch.setattr(solver_runner, "_run_ac_opf", _fake_ac)
    monkeypatch.setattr(solver_runner, "_run_dc_opf", _fake_dc)
    monkeypatch.setattr(solver_runner, "_run_lindistflow", _fake_ldf)

    result = asyncio.run(solver_runner.run_compare(model, SolverConfig()))

    assert result["model_id"] == model.id
    assert result["ac"]["source_injection"]["p_w"] == 12.5
    assert result["dc"]["slack_injection_w"] == 7.25
    assert result["lindistflow"]["source_bus"] == "source"
    assert result["summary"] == {
        "ac_success": True,
        "dc_success": False,
        "lindistflow_success": True,
        "ac_source_p_w": 12.5,
        "dc_slack_injection_w": 7.25,
        "ldf_source_bus": "source",
    }
    assert calls[0][0] == "load"
    assert [call[0] for call in calls[1:]] == ["ac", "dc", "lindistflow"]


def test_batch_cache_key_is_canonical():
    from fgc_flow_api.services.batch_jobs import build_batch_cache_key, expand_parameter_grid

    grid_a = {"maxiter": [100, 200], "slack_cost_linear": [25.0, 50.0]}
    grid_b = {"slack_cost_linear": [25.0, 50.0], "maxiter": [100, 200]}

    assert expand_parameter_grid(grid_a) == expand_parameter_grid(grid_b)

    params_a = {
        "model_id": "model-1",
        "solver": "dc-opf",
        "config": {
            "tolerance": 1e-6,
            "max_iter": 300,
            "verbose": False,
            "ac": {"include_loads": True, "include_solar": True},
            "dc": {"maxiter": 100, "slack_cost_linear": 25.0},
            "lindistflow": {"include_loads": True},
        },
    }
    params_b = deepcopy(params_a)
    params_b["config"] = {
        "dc": {"slack_cost_linear": 25.0, "maxiter": 100},
        "lindistflow": {"include_loads": True},
        "ac": {"include_solar": True, "include_loads": True},
        "verbose": False,
        "max_iter": 300,
        "tolerance": 1e-6,
    }

    assert build_batch_cache_key("model-version-1", params_a) == build_batch_cache_key("model-version-1", params_b)


def test_create_batch_jobs_queues_every_sweep_point(monkeypatch):
    from fgc_flow_api.schemas.simulations import SimulationBatchRequest, SimulationSolverName
    from fgc_flow_api.services.batch_jobs import create_batch_jobs

    body = SimulationBatchRequest(
        model_id="model-1",
        solver=SimulationSolverName.DC_OPF,
        parameter_grid={"maxiter": [100, 200], "slack_cost_linear": [25.0, 50.0]},
    )

    class DummyDB:
        def __init__(self):
            self.added: list[object] = []
            self.commit_count = 0
            self.refresh_count = 0

        def add(self, job):
            self.added.append(job)

        async def commit(self):
            self.commit_count += 1

        async def refresh(self, job):
            self.refresh_count += 1

    db = DummyDB()
    jobs = asyncio.run(create_batch_jobs(db, "user-1", "model-version-1", body))

    assert db.commit_count == 1
    assert db.refresh_count == 4
    assert len(jobs) == 4
    assert {job.job_type for job in jobs} == {"dc-opf"}
    assert all(job.status == "PENDING" for job in jobs)
    assert {job.params["model_id"] for job in jobs} == {"model-1"}
    assert {job.params["solver"] for job in jobs} == {"dc-opf"}
    assert {job.params["config"]["dc"]["maxiter"] for job in jobs} == {100, 200}
    assert {job.params["config"]["dc"]["slack_cost_linear"] for job in jobs} == {25.0, 50.0}


def test_create_batch_jobs_rejects_invalid_sweep_before_writes():
    from fgc_flow_api.schemas.simulations import SimulationBatchRequest, SimulationSolverName
    from fgc_flow_api.services.batch_jobs import create_batch_jobs

    body = SimulationBatchRequest(
        model_id="model-1",
        solver=SimulationSolverName.AC_OPF,
        parameter_grid={"does_not_exist": [1.0]},
    )

    class DummyDB:
        def __init__(self):
            self.added = []

        def add(self, job):
            self.added.append(job)

        async def commit(self):
            raise AssertionError("commit should not run")

        async def refresh(self, job):
            raise AssertionError("refresh should not run")

    db = DummyDB()

    with pytest.raises(ValueError, match="Unknown sweep parameter"):
        asyncio.run(create_batch_jobs(db, "user-1", "model-version-1", body))

    assert db.added == []

