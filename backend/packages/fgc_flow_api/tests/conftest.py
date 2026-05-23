"""Shared test fixtures for fgc_flow_api."""
import sys
from pathlib import Path

PACKAGES_DIR = Path(__file__).resolve().parents[2]
for entry in PACKAGES_DIR.iterdir():
    if entry.is_dir() and (entry / "pyproject.toml").exists():
        sys.path.insert(0, str(entry))

import pytest


@pytest.fixture
def app(monkeypatch):
    async def _noop():
        return None

    monkeypatch.setattr("fgc_flow_api.main.init_flow_db", _noop)
    monkeypatch.setattr("fgc_flow_api.main.init_jobs_db", _noop)
    from fgc_flow_api.main import app as fastapi_app

    return fastapi_app
