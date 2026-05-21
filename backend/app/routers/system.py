from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.user import User
from app.services.gdm_service import gdm_service

router = APIRouter(prefix="/api/system", tags=["system"])


async def _get_active_project(user: User, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.owner_id == user.id, Project.is_active == True)  # noqa: E712
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active project. Select a model first.")
    return project


def _ensure_loaded(project: Project) -> str:
    try:
        gdm_service.get_system(project.id)
    except KeyError:
        try:
            gdm_service.load_system(project.id, project.file_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to load model: {e}"
            )
    return project.id


@router.get("/summary")
async def system_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_active_project(user, db)
    pid = _ensure_loaded(project)
    return gdm_service.get_summary(pid)


@router.get("/components")
async def list_components(
    component_type: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    project = await _get_active_project(user, db)
    pid = _ensure_loaded(project)
    if component_type:
        return gdm_service.get_components_by_type(pid, component_type)
    return gdm_service.get_all_components(pid)


@router.get("/components/{uuid}")
async def get_component(
    uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_active_project(user, db)
    pid = _ensure_loaded(project)
    comp = gdm_service.get_component_by_uuid(pid, uuid)
    if comp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    return comp


@router.get("/export")
async def export_system(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_active_project(user, db)
    pid = _ensure_loaded(project)
    return gdm_service.export_system_json(pid)


@router.get("/download")
async def download_system(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the current system as a .zip file."""
    project = await _get_active_project(user, db)
    pid = _ensure_loaded(project)
    zip_path = gdm_service.export_system_zip(pid, project.name)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{project.name}.zip",
    )
