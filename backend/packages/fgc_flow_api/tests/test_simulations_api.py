from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("path", "solver", "runner_attr"),
    [
        ("/api/simulations/ac-opf", "ac-opf", "_run_ac_opf"),
        ("/api/simulations/dc-opf", "dc-opf", "_run_dc_opf"),
        ("/api/simulations/lindistflow", "lindistflow", "_run_lindistflow"),
    ],
)
def test_simulation_endpoints_run_in_threadpool(monkeypatch, app, path, solver, runner_attr):
    from fgc_flow_api.dependencies import get_current_user
    from fgc_flow_api.main import app as fastapi_app
    from fgc_flow_api.routers import simulations as sim_router
    from fgc_flow_api.services import solver_runner

    user = SimpleNamespace(id="user-1")
    model = SimpleNamespace(id="model-1", file_path="/tmp/model.json", user_id=user.id)
    called = {}

    async def _override_user():
        return user

    async def _override_db():
        yield SimpleNamespace()

    async def _fake_lookup(db, user_id, model_id):
        assert user_id == user.id
        assert model_id == model.id
        return model

    async def _fake_threadpool(fn, *args, **kwargs):
        called["threadpool"] = True
        return fn(*args, **kwargs)

    def _fake_runner(model_arg, body_arg):
        called["solver"] = body_arg.solver.value
        return {"solver": body_arg.solver.value, "model_id": model_arg.id, "config": body_arg.config.model_dump(mode="json"), "result": {"ok": True}}

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[sim_router.get_flow_db] = _override_db
    monkeypatch.setattr(sim_router, "get_model_for_user", _fake_lookup)
    monkeypatch.setattr(solver_runner, "run_in_threadpool", _fake_threadpool)
    monkeypatch.setattr(solver_runner, runner_attr, _fake_runner)

    with TestClient(fastapi_app) as client:
        response = client.post(
            path,
            json={
                "model_id": model.id,
                "solver": solver,
                "config": {"tolerance": 1e-6, "max_iter": 300, "verbose": False},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["solver"] == solver
    assert payload["model_id"] == model.id
    assert called["threadpool"] is True
    assert called["solver"] == solver


def test_missing_model_returns_404(monkeypatch, app):
    from fgc_flow_api.dependencies import get_current_user
    from fgc_flow_api.main import app as fastapi_app
    from fgc_flow_api.routers import simulations as sim_router

    async def _override_user():
        return SimpleNamespace(id="user-1")

    async def _override_db():
        yield SimpleNamespace()

    async def _missing_model(db, user_id, model_id):
        raise HTTPException(status_code=404, detail="Model not found")

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[sim_router.get_flow_db] = _override_db
    monkeypatch.setattr(sim_router, "get_model_for_user", _missing_model)

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/api/simulations/ac-opf",
            json={
                "model_id": "missing",
                "solver": "ac-opf",
                "config": {"tolerance": 1e-6, "max_iter": 300, "verbose": False},
            },
        )

    assert response.status_code == 404
