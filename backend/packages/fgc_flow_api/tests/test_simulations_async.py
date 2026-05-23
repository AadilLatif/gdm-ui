from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient


def _simulation_request(**overrides):
    from fgc_flow_api.schemas.simulations import ACSolverConfig, SimulationRequest, SimulationSolverName, SolverConfig

    config = SolverConfig(
        max_iter=overrides.get("max_iter", 300),
        ac=ACSolverConfig(slack_label=overrides.get("slack_label")),
    )
    return SimulationRequest(
        model_id=overrides.get("model_id", "model-1"),
        solver=overrides.get("solver", SimulationSolverName.AC_OPF),
        config=config,
    )


def test_estimate_runtime_seconds_scales_with_iterations_and_sweeps():
    from fgc_flow_api.services.simulation_jobs import QUEUE_THRESHOLD_SECONDS, estimate_runtime_seconds

    request = _simulation_request(max_iter=1200, slack_label=[("a", "b"), ("c", "d"), ("e", "f")])

    assert estimate_runtime_seconds(request) > QUEUE_THRESHOLD_SECONDS


def test_inline_simulation_dispatch_returns_payload(monkeypatch, app):
    from fgc_flow_api.dependencies import get_current_user
    from fgc_flow_api.main import app as fastapi_app
    from fgc_flow_api.routers import simulations as sim_router
    from fgc_flow_api.schemas.simulations import SimulationResponse, SimulationSolverName, SolverConfig

    user = SimpleNamespace(id="user-1")
    model = SimpleNamespace(id="model-1", file_path="/tmp/model.json", user_id=user.id)

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

    async def _fake_run(model_arg, body_arg):
        return SimulationResponse(
            model_id=model_arg.id,
            solver=body_arg.solver,
            config=body_arg.config,
            result={"status": "ok", "solver": body_arg.solver.value},
        )

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[sim_router.get_flow_db] = _override_flow_db
    app.dependency_overrides[sim_router.get_jobs_db] = _override_jobs_db
    monkeypatch.setattr(sim_router, "get_model_for_user", _fake_lookup)
    monkeypatch.setattr(sim_router, "estimate_runtime_seconds", lambda body: 4.5)
    monkeypatch.setattr(sim_router, "run_simulation_request", _fake_run)

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/api/simulations/ac-opf",
            json={
                "model_id": model.id,
                "solver": SimulationSolverName.AC_OPF.value,
                "config": SolverConfig().model_dump(mode="json"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_mode"] == "inline"
    assert payload["status"] == "SUCCESS"
    assert payload["model_id"] == model.id
    assert payload["result"]["solver"] == SimulationSolverName.AC_OPF.value


def test_queued_simulation_dispatch_returns_job_id(monkeypatch, app):
    from fgc_flow_api.dependencies import get_current_user
    from fgc_flow_api.main import app as fastapi_app
    from fgc_flow_api.routers import simulations as sim_router
    from fgc_flow_api.schemas.simulations import SimulationDispatchResponse, SimulationSolverName, SolverConfig

    user = SimpleNamespace(id="user-1")
    model = SimpleNamespace(id="model-1", file_path="/tmp/model.json", user_id=user.id)
    captured = {}

    async def _override_user():
        return user

    async def _override_flow_db():
        yield SimpleNamespace()

    async def _override_jobs_db():
        class DummyDB:
            async def add(self, obj):
                captured["job"] = obj

            async def commit(self):
                captured["committed"] = True

            async def refresh(self, obj):
                return None

        yield DummyDB()

    async def _fake_lookup(db, user_id, model_id):
        assert user_id == user.id
        assert model_id == model.id
        return model

    async def _fake_submit(db, user_id, body):
        captured["submitted"] = {
            "user_id": user_id,
            "model_id": body.model_id,
            "solver": body.solver.value,
        }
        return SimulationDispatchResponse(
            execution_mode="queued",
            status="PENDING",
            job_id="job-1",
            model_id=body.model_id,
            solver=body.solver,
            config=body.config,
        )

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[sim_router.get_flow_db] = _override_flow_db
    app.dependency_overrides[sim_router.get_jobs_db] = _override_jobs_db
    monkeypatch.setattr(sim_router, "get_model_for_user", _fake_lookup)
    monkeypatch.setattr(sim_router, "estimate_runtime_seconds", lambda body: 5.5)
    monkeypatch.setattr(sim_router, "submit_simulation_job", _fake_submit)

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/api/simulations/ac-opf",
            json={
                "model_id": model.id,
                "solver": SimulationSolverName.AC_OPF.value,
                "config": SolverConfig(max_iter=1200).model_dump(mode="json"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_mode"] == "queued"
    assert payload["status"] == "PENDING"
    assert payload["job_id"] == "job-1"
    assert captured["submitted"]["solver"] == SimulationSolverName.AC_OPF.value


def test_completed_job_polling_returns_serialized_payload(monkeypatch, app):
    from fgc_flow_api.dependencies import get_current_user
    from fgc_flow_api.main import app as fastapi_app
    from fgc_flow_api.routers import jobs as jobs_router

    user = SimpleNamespace(id="user-1")
    job = SimpleNamespace(
        id="job-1",
        user_id=user.id,
        model_version_id="model-1",
        job_type="ac-opf",
        params={"model_id": "model-1", "solver": "ac-opf", "config": {"max_iter": 300}},
        status="SUCCESS",
        status_events=[{"status": "SUCCESS"}],
        retry_count=0,
        next_retry_at=None,
        created_at=datetime(2026, 5, 22, 0, 0, 0, tzinfo=timezone.utc),
        started_at=datetime(2026, 5, 22, 0, 0, 1, tzinfo=timezone.utc),
        completed_at=datetime(2026, 5, 22, 0, 0, 2, tzinfo=timezone.utc),
        error=None,
        result_path="/tmp/result.json",
    )

    async def _override_user():
        return user

    async def _override_db():
        class DummyDB:
            async def execute(self, *args, **kwargs):
                class Result:
                    def scalar_one_or_none(self_inner):
                        return job

                return Result()

        yield DummyDB()

    async def _fake_cached_result(db, model_version_id, params):
        return SimpleNamespace(result_json={"solver": "ac-opf", "status": "ok"}, result_path="/tmp/result.json")

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[jobs_router.get_jobs_db] = _override_db
    monkeypatch.setattr(jobs_router, "get_cached_result", _fake_cached_result)

    with TestClient(fastapi_app) as client:
        response = client.get("/api/jobs/job-1/result")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-1"
    assert payload["result_json"]["status"] == "ok"
