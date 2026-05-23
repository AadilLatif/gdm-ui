"""Model upload/list endpoints."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fgc_core.models.user import User

from fgc_flow_api.config import settings
from fgc_flow_api.database import get_flow_db
from fgc_flow_api.dependencies import get_current_user
from fgc_flow_api.models import Model
from fgc_flow_api.schemas.models import ModelListItem, ModelUploadResponse

router = APIRouter(prefix="/api/models", tags=["models"])


def _extract_model_archive(content: bytes, filename: str, user_id: str) -> str:
    user_dir = settings.upload_dir / user_id
    model_dir = user_dir / str(uuid4())
    model_dir.mkdir(parents=True, exist_ok=True)

    zip_path = model_dir / "upload.zip"
    zip_path.write_bytes(content)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.startswith("/") or ".." in Path(name).parts:
                    raise ValueError(f"Unsafe path in zip: {name}")
            zf.extractall(model_dir)
    except zipfile.BadZipFile as exc:
        shutil.rmtree(model_dir, ignore_errors=True)
        raise ValueError("Uploaded file is not a valid zip archive") from exc
    finally:
        zip_path.unlink(missing_ok=True)

    json_files = sorted(model_dir.rglob("*.json"), key=lambda path: len(path.parts))
    if not json_files:
        shutil.rmtree(model_dir, ignore_errors=True)
        raise ValueError("No JSON file found in uploaded zip")

    return str(json_files[0])


@router.post("/upload", response_model=ModelUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_model(
    file: UploadFile = File(...),
    name: str = Form(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_flow_db),
):
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .zip files are accepted")

    content = await file.read()
    try:
        json_path = _extract_model_archive(content, file.filename, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    model = Model(
        user_id=user.id,
        name=name or file.filename.rsplit(".", 1)[0],
        file_path=json_path,
        file_size=len(content),
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return ModelUploadResponse(model_id=model.id, name=model.name, file_size=model.file_size, created_at=model.created_at)


@router.post("/register", response_model=ModelUploadResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    name: str = Form(...),
    file_path: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_flow_db),
):
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File not found")
    if not file_path_obj.is_file():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is not a file")

    model = Model(
        user_id=user.id,
        name=name or file_path_obj.stem,
        file_path=str(file_path_obj),
        file_size=file_path_obj.stat().st_size,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return ModelUploadResponse(model_id=model.id, name=model.name, file_size=model.file_size, created_at=model.created_at)


@router.get("", response_model=list[ModelListItem])
async def list_models(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_flow_db),
):
    result = await db.execute(select(Model).where(Model.user_id == user.id).order_by(Model.created_at.desc()))
    return [
        ModelListItem(model_id=model.id, name=model.name, file_size=model.file_size, created_at=model.created_at)
        for model in result.scalars().all()
    ]
