from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_compare_endpoint_returns_side_by_side_payload(monkeypatch, app):
    from fgc_flow_api.dependencies import get_current_user
    from fgc_flow_api.main import app as fastapi_app
    from fgc_flow_api.routers import simulations as sim_router

    user = SimpleNamespace(id="user-1")
    model = SimpleNamespace(id="model-1", user_id=user.id)

    async def _override_user():
        return user

    async def _override_db():
        yield SimpleNamespace()

    async def _fake_lookup(db, user_id, model_id):
        assert user_id == user.id
        assert model_id == model.id
        return model

    async def _fake_compare(model_arg, config_arg):
        return {
            "model_id": model_arg.id,
            "ac": {"success": True, "source_injection": {"p_w": 1.0}},
            "dc": {"success": True, "slack_injection_w": 2.0},
            "lindistflow": {"success": True, "source_bus": "source"},
            "summary": {
                "ac_success": True,
                "dc_success": True,
                "lindistflow_success": True,
                "ac_source_p_w": 1.0,
                "dc_slack_injection_w": 2.0,
                "ldf_source_bus": "source",
            },
        }

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[sim_router.get_flow_db] = _override_db
    monkeypatch.setattr(sim_router, "get_model_for_user", _fake_lookup)
    monkeypatch.setattr(sim_router, "run_compare", _fake_compare)

    try:
        with TestClient(fastapi_app) as client:
            response = client.post("/api/simulations/compare", json={"model_id": model.id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_id"] == model.id
    assert payload["summary"]["ac_success"] is True
    assert set(payload) == {"model_id", "ac", "dc", "lindistflow", "summary"}


def test_batch_endpoint_returns_job_ids_and_metadata(monkeypatch, app):
    from fgc_flow_api.dependencies import get_current_user
    from fgc_flow_api.main import app as fastapi_app
    from fgc_flow_api.routers import simulations as sim_router

    user = SimpleNamespace(id="user-1")
    model = SimpleNamespace(id="model-1", user_id=user.id)

    async def _override_user():
        return user

    async def _override_flow_db():
        yield SimpleNamespace()

    async def _override_jobs_db():
        yield SimpleNamespace()

    async def _fake_lookup(db, user_id, model_id):
        assert user_id == user.id
        assert model_id == model.id
        return model

    async def _fake_create_batch_jobs(db, user_id, model_version_id, body):
        assert user_id == user.id
        assert model_version_id == model.id
        return [SimpleNamespace(id="job-1"), SimpleNamespace(id="job-2")]

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[sim_router.get_flow_db] = _override_flow_db
    app.dependency_overrides[sim_router.get_jobs_db] = _override_jobs_db
    monkeypatch.setattr(sim_router, "get_model_for_user", _fake_lookup)
    monkeypatch.setattr(sim_router, "create_batch_jobs", _fake_create_batch_jobs)

    try:
        with TestClient(fastapi_app) as client:
            response = client.post(
                "/api/simulations/batch",
                json={
                    "model_id": model.id,
                    "solver": "dc-opf",
                    "parameter_grid": {"maxiter": [100, 200]},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["queued_jobs"] == 2
    assert payload["job_ids"] == ["job-1", "job-2"]
    assert payload["solver"] == "dc-opf"
    assert payload["sweep_points"] == [{"maxiter": 100}, {"maxiter": 200}]


def test_batch_endpoint_rejects_empty_parameter_grid(monkeypatch, app):
    from fgc_flow_api.dependencies import get_current_user
    from fgc_flow_api.main import app as fastapi_app
    from fgc_flow_api.routers import simulations as sim_router

    async def _override_user():
        return SimpleNamespace(id="user-1")

    async def _override_flow_db():
        yield SimpleNamespace()

    async def _override_jobs_db():
        yield SimpleNamespace()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[sim_router.get_flow_db] = _override_flow_db
    app.dependency_overrides[sim_router.get_jobs_db] = _override_jobs_db

    try:
        with TestClient(fastapi_app) as client:
            response = client.post(
                "/api/simulations/batch",
                json={"model_id": "model-1", "solver": "dc-opf", "parameter_grid": {}},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
