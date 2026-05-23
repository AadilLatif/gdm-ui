from __future__ import annotations

from fastapi.testclient import TestClient


def test_main_exposes_phase_three_routes_and_structured_404(app):
    from fgc_flow_api.main import app as fastapi_app

    paths = set(fastapi_app.openapi()["paths"].keys())

    assert "/health" in paths
    assert any(path.startswith("/api/auth/") for path in paths)
    assert any(path.startswith("/api/jobs/") or path == "/api/jobs" for path in paths)
    assert any(path.startswith("/api/models/") or path == "/api/models" for path in paths)
    assert any(path.startswith("/api/simulations/") for path in paths)

    with TestClient(fastapi_app) as client:
        response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error_code"] == "not-found"
    assert payload["detail"] == "The requested resource was not found"
