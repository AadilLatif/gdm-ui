from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.user import User
from app.services.gdm_service import gdm_service

router = APIRouter(prefix="/api/equipment", tags=["equipment"])

# Equipment type categories matching the UI mockup
EQUIPMENT_CATEGORIES: dict[str, list[str]] = {
    "conductors": ["BareConductorEquipment", "ConcentricCableEquipment"],
    "transformers": ["WindingEquipment", "DistributionTransformerEquipment"],
    "loads": ["PhaseLoadEquipment", "LoadEquipment"],
    "capacitors": ["PhaseCapacitorEquipment", "CapacitorEquipment"],
    "generation": ["SolarEquipment", "BatteryEquipment", "InverterEquipment"],
    "sources": ["PhaseVoltageSourceEquipment", "VoltageSourceEquipment"],
    "branches": [
        "MatrixImpedanceBranchEquipment",
        "SequenceImpedanceBranchEquipment",
        "GeometryBranchEquipment",
    ],
    "protection": [
        "MatrixImpedanceFuseEquipment",
        "MatrixImpedanceRecloserEquipment",
        "MatrixImpedanceSwitchEquipment",
        "RecloserControllerEquipment",
    ],
}


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


@router.get("/categories")
async def list_categories() -> dict[str, list[str]]:
    return EQUIPMENT_CATEGORIES


@router.get("/")
async def list_equipment(
    category: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    pid = await _get_active_project_id(user, db)

    if category:
        types = EQUIPMENT_CATEGORIES.get(category)
        if not types:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown category: {category}")
        results = []
        for t in types:
            results.extend(gdm_service.get_components_by_type(pid, t))
        return results

    # All equipment types
    results = []
    for types in EQUIPMENT_CATEGORIES.values():
        for t in types:
            results.extend(gdm_service.get_components_by_type(pid, t))
    return results


@router.get("/{uuid}")
async def get_equipment_item(
    uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    pid = await _get_active_project_id(user, db)
    comp = gdm_service.get_component_by_uuid(pid, uuid)
    if comp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return comp


class AddEquipmentRequest(BaseModel):
    type: str
    data: dict[str, Any]


class UpdateEquipmentRequest(BaseModel):
    data: dict[str, Any]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_equipment(
    body: AddEquipmentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    pid = await _get_active_project_id(user, db)
    try:
        return gdm_service.add_component(pid, body.type, body.data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.patch("/{uuid}")
async def update_equipment(
    uuid: str,
    body: UpdateEquipmentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    pid = await _get_active_project_id(user, db)
    try:
        return gdm_service.update_component(pid, uuid, body.data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    pid = await _get_active_project_id(user, db)
    try:
        gdm_service.delete_component(pid, uuid)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
