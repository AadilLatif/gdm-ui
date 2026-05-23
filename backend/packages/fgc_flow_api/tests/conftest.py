"""Shared test fixtures for fgc_flow_api."""

import sys
from pathlib import Path

CORE_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "fgc_core"
if str(CORE_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_PACKAGE_DIR))

import pytest


@pytest.fixture
def app(monkeypatch):
    """Return the FastAPI app with startup DB init disabled for tests."""

    async def _noop():
        return None

    monkeypatch.setattr("fgc_flow_api.main.init_flow_db", _noop)
    monkeypatch.setattr("fgc_flow_api.main.init_jobs_db", _noop)
    from fgc_flow_api.main import app as fastapi_app

    return fastapi_app
