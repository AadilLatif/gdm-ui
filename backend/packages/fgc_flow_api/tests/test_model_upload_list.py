from __future__ import annotations

import asyncio
import io
import zipfile
import sys
from pathlib import Path
from types import SimpleNamespace

CORE_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "fgc_core"
if str(CORE_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_PACKAGE_DIR))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from fgc_flow_api.database import FlowBase, get_flow_db
from fgc_flow_api.dependencies import get_current_user
from fgc_flow_api.models import Model
from fgc_flow_api.routers.models import router as models_router


def _make_zip_bytes(*members: tuple[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in members:
            zf.writestr(name, content)
    return buffer.getvalue()


@pytest.fixture()
def flow_app(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'flow.db'}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def _init_db():
        async with engine.begin() as conn:
            await conn.run_sync(FlowBase.metadata.create_all)

    asyncio.run(_init_db())

    app = FastAPI()
    app.include_router(models_router)

    async def _override_flow_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_flow_db] = _override_flow_db
    return app, sessionmaker


def test_upload_and_list_models_are_user_scoped(monkeypatch, tmp_path: Path, flow_app):
    app, sessionmaker = flow_app
    monkeypatch.setattr("fgc_flow_api.config.settings.upload_dir", tmp_path / "uploads", raising=False)

    user_a = SimpleNamespace(id="user-a")
    user_b = SimpleNamespace(id="user-b")

    def make_user_override(user):
        async def _override():
            return user

        return _override

    client = TestClient(app)

    app.dependency_overrides[get_current_user] = make_user_override(user_a)
    response = client.post(
        "/api/models/upload",
        files={
            "file": ("grid.zip", _make_zip_bytes(("system.json", b"{}")), "application/zip"),
            "name": (None, "Alpha Model"),
        },
    )
    assert response.status_code == 201
    first_model_id = response.json()["model_id"]
    assert response.json()["name"] == "Alpha Model"

    app.dependency_overrides[get_current_user] = make_user_override(user_b)
    response = client.post(
        "/api/models/upload",
        files={"file": ("grid.zip", _make_zip_bytes(("system.json", b"{}")), "application/zip")},
        data={"name": "Beta Model"},
    )
    assert response.status_code == 201

    app.dependency_overrides[get_current_user] = make_user_override(user_a)
    response = client.get("/api/models")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["model_id"] == first_model_id
    assert items[0]["name"] == "Alpha Model"
    assert items[0]["file_size"] > 0

    async def _count_rows():
        async with sessionmaker() as session:
            result = await session.execute(select(Model))
            return len(result.scalars().all())

    assert asyncio.run(_count_rows()) == 2


def test_upload_rejects_path_traversal_without_persisting_row(monkeypatch, tmp_path: Path, flow_app):
    app, sessionmaker = flow_app
    monkeypatch.setattr("fgc_flow_api.config.settings.upload_dir", tmp_path / "uploads", raising=False)

    app.dependency_overrides[get_current_user] = (lambda: SimpleNamespace(id="user-a"))

    client = TestClient(app)
    response = client.post(
        "/api/models/upload",
        files={"file": ("grid.zip", _make_zip_bytes(("../evil.json", b"{}")), "application/zip")},
    )
    assert response.status_code == 400

    async def _count_rows():
        async with sessionmaker() as session:
            result = await session.execute(select(Model))
            return len(result.scalars().all())

    assert asyncio.run(_count_rows()) == 0
