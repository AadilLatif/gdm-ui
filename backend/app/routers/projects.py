from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectResponse, ProjectUpdate
from app.services.file_service import copy_project_files, delete_project_files, handle_zip_upload
from app.services.gdm_service import gdm_service

router = APIRouter(prefix="/api/projects", tags=["projects"])

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB


@router.post("/upload", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def upload_model(
    file: UploadFile = File(...),
    name: str = "",
    description: str = "",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .zip files are accepted")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 500MB)")

    try:
        project_dir, json_path = handle_zip_upload(content, file.filename, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    project_name = name or file.filename.rsplit(".", 1)[0]
    project = Project(
        name=project_name,
        description=description,
        file_path=json_path,
        owner_id=user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.owner_id == user.id))
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_user_project(project_id, user.id, db)
    return project


@router.post("/{project_id}/select", response_model=ProjectResponse)
async def select_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set a project as the active model and load it into memory."""
    project = await _get_user_project(project_id, user.id, db)

    # Deactivate all other projects for this user
    result = await db.execute(select(Project).where(Project.owner_id == user.id, Project.is_active == True))  # noqa: E712
    for p in result.scalars().all():
        p.is_active = False

    project.is_active = True
    await db.commit()
    await db.refresh(project)

    # Load the GDM system
    try:
        gdm_service.load_system(project.id, project.file_path)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to load model: {e}")

    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_user_project(project_id, user.id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_user_project(project_id, user.id, db)
    gdm_service.unload_system(project.id)
    delete_project_files(project.file_path)
    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/copy", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def copy_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate a project — copies files and creates a new DB record."""
    source = await _get_user_project(project_id, user.id, db)
    new_dir, new_json = copy_project_files(source.file_path, user.id)

    copy = Project(
        name=f"{source.name} (copy)",
        description=source.description,
        file_path=new_json,
        owner_id=user.id,
    )
    db.add(copy)
    await db.commit()
    await db.refresh(copy)
    return copy


async def _get_user_project(project_id: str, user_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
