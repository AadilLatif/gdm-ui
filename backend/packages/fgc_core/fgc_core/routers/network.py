from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fgc_core.database import get_db
from fgc_core.dependencies import get_current_user
from fgc_core.models.project import Project
from fgc_core.models.user import User
from fgc_core.services.gdm_service import gdm_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/network", tags=["network"])


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


@router.get("/topology")
async def get_topology(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    pid = await _get_active_project_id(user, db)
    return gdm_service.get_topology(pid)


@router.get("/buses")
async def get_buses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    pid = await _get_active_project_id(user, db)
    return gdm_service.get_buses(pid)
