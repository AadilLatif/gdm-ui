import shutil
import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.user import User
from app.services.gdm_service import gdm_service

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB


async def _get_active_project_id(user: User, db: AsyncSession) -> str:
    result = await db.execute(
        select(Project).where(Project.owner_id == user.id, Project.is_active == True)  # noqa: E712
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active project")
    try:
        gdm_service.get_system(project.id)
    except KeyError:
        gdm_service.load_system(project.id, project.file_path)
    return project.id


@router.get("/")
async def list_scenarios(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all loaded scenario files with their scenario names."""
    pid = await _get_active_project_id(user, db)
    return gdm_service.list_scenario_files(pid)


@router.post("/upload")
async def upload_scenario(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload a scenario zip file (contains scenarios.json + optional time_series/)."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .zip files are accepted")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 500MB)")

    pid = await _get_active_project_id(user, db)

    # Extract zip to a temp directory under uploads
    scenario_dir = settings.upload_dir / user.id / "scenarios" / str(uuid4())
    scenario_dir.mkdir(parents=True, exist_ok=True)

    zip_path = scenario_dir / "upload.zip"
    zip_path.write_bytes(content)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.startswith("/") or ".." in name:
                    raise ValueError(f"Unsafe path in zip: {name}")
            zf.extractall(scenario_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(scenario_dir)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid zip archive")
    except ValueError as e:
        shutil.rmtree(scenario_dir)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        zip_path.unlink(missing_ok=True)

    # Find JSON file
    json_files = list(scenario_dir.rglob("*.json"))
    # Exclude __MACOSX
    json_files = [f for f in json_files if "__MACOSX" not in str(f)]
    if not json_files:
        shutil.rmtree(scenario_dir)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No JSON file found in zip")

    json_files.sort(key=lambda p: len(p.parts))
    scenario_json = str(json_files[0])

    try:
        result = gdm_service.load_scenario_catalog(pid, scenario_json, file.filename)
    except Exception as e:
        shutil.rmtree(scenario_dir)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to load scenario: {e}")

    return result


from pydantic import BaseModel


class CreateScenarioRequest(BaseModel):
    scenario_name: str
    ops: list[dict]


@router.post("/create")
async def create_scenario(
    body: CreateScenarioRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a scenario from tracked operations on the network page."""
    pid = await _get_active_project_id(user, db)
    try:
        return gdm_service.create_scenario_from_ops(pid, body.scenario_name, body.ops)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/timeline")
async def get_timeline(
    filename: str,
    scenario_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the resolved timeline for a specific scenario."""
    pid = await _get_active_project_id(user, db)
    try:
        return gdm_service.get_scenario_timeline(pid, filename, scenario_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{filename}")
async def remove_scenario(
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Remove a loaded scenario catalog."""
    pid = await _get_active_project_id(user, db)
    gdm_service.remove_scenario_catalog(pid, filename)
    return {"detail": "Scenario removed"}


@router.get("/download")
async def download_scenario_model(
    filename: str,
    scenario_name: str,
    timestamp: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the base model with scenario changes applied as a zip file."""
    pid = await _get_active_project_id(user, db)
    try:
        safe_name = scenario_name.replace(" ", "_").replace("/", "_")
        zip_path = gdm_service.export_scenario_zip(
            pid, filename, scenario_name, timestamp=timestamp, name=safe_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{safe_name}.zip",
    )


@router.post("/save-as-project")
async def save_scenario_as_project(
    filename: str,
    scenario_name: str,
    timestamp: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply scenario to base model and save as a new project."""
    pid = await _get_active_project_id(user, db)

    # Get the active project for naming
    result = await db.execute(
        select(Project).where(Project.id == pid)
    )
    source = result.scalar_one()

    dest_dir = settings.upload_dir / user.id / str(uuid4())
    try:
        json_path = gdm_service.save_scenario_as_project(
            pid, filename, scenario_name, timestamp=timestamp, dest_dir=str(dest_dir),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    new_project = Project(
        name=f"{source.name} + {scenario_name}",
        description=f"Scenario '{scenario_name}' applied to {source.name}",
        file_path=json_path,
        owner_id=user.id,
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return {
        "id": new_project.id,
        "name": new_project.name,
        "detail": "Scenario model saved as new project",
    }
