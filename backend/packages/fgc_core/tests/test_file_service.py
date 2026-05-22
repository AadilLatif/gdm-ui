import io
import pytest
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

from fgc_core.services.file_service import (
    handle_zip_upload,
    delete_project_files,
    copy_project_files,
)


class TestHandleZipUpload:
    def test_valid_zip_extraction(self, sample_zip_content, tmp_path):
        with patch("fgc_core.services.file_service.settings") as mock_settings:
            mock_settings.upload_dir = tmp_path

            user_id = "test-user-123"
            filename = "test_system.zip"

            project_dir, json_path = handle_zip_upload(
                sample_zip_content, filename, user_id
            )

            assert Path(project_dir).exists()
            assert Path(json_path).exists()
            assert json_path.endswith(".json")

    def test_invalid_zip_raises_error(self, tmp_path):
        with patch("fgc_core.services.file_service.settings") as mock_settings:
            mock_settings.upload_dir = tmp_path

            with pytest.raises(ValueError, match="not a valid zip"):
                handle_zip_upload(b"not a zip file", "test.zip", "user123")

    def test_zip_with_traversal_path_rejected(self, tmp_path):
        with patch("fgc_core.services.file_service.settings") as mock_settings:
            mock_settings.upload_dir = tmp_path

            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("../evil.json", '{"name": "evil"}')
            buffer.seek(0)

            with pytest.raises(ValueError, match="Unsafe path"):
                handle_zip_upload(buffer.read(), "test.zip", "user123")

    def test_zip_with_absolute_path_rejected(self, tmp_path):
        with patch("fgc_core.services.file_service.settings") as mock_settings:
            mock_settings.upload_dir = tmp_path

            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("/etc/passwd", '{"name": "evil"}')
            buffer.seek(0)

            with pytest.raises(ValueError, match="Unsafe path"):
                handle_zip_upload(buffer.read(), "test.zip", "user123")

    def test_zip_without_json_raises_error(self, tmp_path):
        with patch("fgc_core.services.file_service.settings") as mock_settings:
            mock_settings.upload_dir = tmp_path

            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("readme.txt", "Hello World")
            buffer.seek(0)

            with pytest.raises(ValueError, match="No JSON file found"):
                handle_zip_upload(buffer.read(), "test.zip", "user123")

    def test_prefers_shallow_json(self, tmp_path):
        with patch("fgc_core.services.file_service.settings") as mock_settings:
            mock_settings.upload_dir = tmp_path

            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("system.json", '{"name": "root"}')
                zf.writestr("subdir/system.json", '{"name": "nested"}')
            buffer.seek(0)

            project_dir, json_path = handle_zip_upload(
                buffer.read(), "test.zip", "user123"
            )

            assert Path(json_path).name == "system.json"
            parts = Path(json_path).relative_to(project_dir).parts
            assert len(parts) == 1


class TestDeleteProjectFiles:
    def test_deletes_project_directory(self, tmp_path):
        project_dir = tmp_path / "project-123"
        project_dir.mkdir()
        (project_dir / "file.json").write_text("{}")

        delete_project_files(str(project_dir / "file.json"))

        assert not project_dir.exists()

    def test_handles_nonexistent_path(self, tmp_path):
        nonexistent = tmp_path / "nonexistent" / "file.json"
        delete_project_files(str(nonexistent))
        assert True

    def test_deletes_parent_if_file_not_in_subdir(self, tmp_path):
        project_dir = tmp_path / "project-456"
        project_dir.mkdir()
        (project_dir / "model.json").write_text("{}")

        delete_project_files(str(project_dir / "model.json"))

        assert not project_dir.exists()


class TestCopyProjectFiles:
    def test_copies_entire_directory(self, tmp_path):
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "model.json").write_text('{"name": "test"}')
        (source_dir / "data.csv").write_text("col1,col2\n1,2")

        new_dir, new_json = copy_project_files(
            str(source_dir / "model.json"), "new-user-id"
        )

        assert Path(new_dir).exists()
        assert Path(new_json).exists()
        assert Path(new_json).name == "model.json"

        source_files = set(f.name for f in source_dir.iterdir())
        new_files = set(f.name for f in Path(new_dir).iterdir())
        assert source_files == new_files

    def test_creates_unique_copy_for_different_users(self, tmp_path):
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "model.json").write_text("{}")

        copy1_dir, copy1_json = copy_project_files(
            str(source_dir / "model.json"), "user1"
        )
        copy2_dir, copy2_json = copy_project_files(
            str(source_dir / "model.json"), "user2"
        )

        assert copy1_dir != copy2_dir
        assert Path(copy1_dir).exists()
        assert Path(copy2_dir).exists()