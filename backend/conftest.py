import sys
from pathlib import Path

PACKAGES_DIR = Path(__file__).resolve().parent / "packages"
for entry in PACKAGES_DIR.iterdir():
    if entry.is_dir() and (entry / "pyproject.toml").exists():
        sys.path.insert(0, str(entry))

import pytest


@pytest.fixture
def app(monkeypatch):
    import fgc_flow_api.main  # defer until path setup is done

    async def _noop():
        return None

    monkeypatch.setattr(fgc_flow_api.main, "init_flow_db", _noop)
    monkeypatch.setattr(fgc_flow_api.main, "init_jobs_db", _noop)
    return fgc_flow_api.main.app
