"""Service for handling file uploads (zip extraction, validation)."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from fgc_core.config import settings


def handle_zip_upload(file_content: bytes, original_filename: str, user_id: str) -> tuple[str, str]:
    """Extract uploaded zip, find the GDM JSON file, and return (project_dir, json_path).

    Expected zip structure: contains a .json file and optionally a *_time_series/ directory.
    """
    user_dir = settings.upload_dir / user_id
    project_dir = user_dir / str(uuid4())
    project_dir.mkdir(parents=True, exist_ok=True)

    zip_path = project_dir / "upload.zip"
    zip_path.write_bytes(file_content)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Security: reject entries with absolute paths or path traversal
            for name in zf.namelist():
                if name.startswith("/") or ".." in name:
                    raise ValueError(f"Unsafe path in zip: {name}")
            zf.extractall(project_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(project_dir)
        raise ValueError("Uploaded file is not a valid zip archive")
    finally:
        zip_path.unlink(missing_ok=True)

    # Find the GDM system JSON file (look for top-level .json files)
    json_files = list(project_dir.rglob("*.json"))
    if not json_files:
        shutil.rmtree(project_dir)
        raise ValueError("No JSON file found in uploaded zip")

    # Prefer a JSON file at the shallowest level
    json_files.sort(key=lambda p: len(p.parts))
    system_json = json_files[0]

    return str(project_dir), str(system_json)


def delete_project_files(file_path: str):
    """Delete all files for a project."""
    path = Path(file_path)
    # Walk up to find the project directory (UUID-named parent)
    project_dir = path.parent if path.is_file() else path
    if project_dir.exists():
        shutil.rmtree(project_dir)


def copy_project_files(source_json_path: str, user_id: str) -> tuple[str, str]:
    """Copy a project's files to a new directory. Returns (new_project_dir, new_json_path)."""
    src_json = Path(source_json_path)
    src_dir = src_json.parent

    user_dir = settings.upload_dir / user_id
    new_dir = user_dir / str(uuid4())
    shutil.copytree(src_dir, new_dir)

    # Find the corresponding JSON in the new directory
    rel = src_json.relative_to(src_dir)
    new_json = new_dir / rel
    return str(new_dir), str(new_json)
