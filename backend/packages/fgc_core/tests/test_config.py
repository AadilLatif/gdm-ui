import pytest
from pathlib import Path

from fgc_core.config import Settings


class TestSettings:
    def test_default_values(self):
        settings = Settings()

        assert settings.app_name == "GDM Studio API"
        assert settings.debug is False
        assert settings.admin_username == "admin"
        assert settings.admin_password == "admin"
        assert settings.access_token_expire_minutes == 60
        assert settings.refresh_token_expire_days == 7
        assert settings.algorithm == "HS256"

    def test_custom_values(self):
        settings = Settings(
            app_name="Custom App",
            debug=True,
            secret_key="custom-secret",
            admin_username="custom_admin",
            admin_password="custom_pass",
        )

        assert settings.app_name == "Custom App"
        assert settings.debug is True
        assert settings.secret_key == "custom-secret"
        assert settings.admin_username == "custom_admin"
        assert settings.admin_password == "custom_pass"

    def test_base_dir_is_path(self):
        settings = Settings()
        assert isinstance(settings.base_dir, Path)

    def test_upload_dir_is_path(self, tmp_path):
        settings = Settings(upload_dir=tmp_path / "uploads")
        assert isinstance(settings.upload_dir, Path)

    def test_can_create_upload_dir(self, tmp_path):
        settings = Settings(upload_dir=tmp_path / "uploads")
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        assert settings.upload_dir.exists()
        assert settings.upload_dir.is_dir()

    def test_cors_origins_default(self):
        settings = Settings()
        assert "http://localhost:5173" in settings.cors_origins
        assert "http://localhost:3000" in settings.cors_origins

    def test_cors_origins_custom(self):
        settings = Settings(
            cors_origins=["http://localhost:8080", "https://example.com"]
        )
        assert settings.cors_origins == ["http://localhost:8080", "https://example.com"]

    def test_database_url_format(self, tmp_path):
        from fgc_core.config import settings
        assert "sqlite+aiosqlite:///" in settings.database_url
        assert "gdm_studio.db" in settings.database_url

    def test_env_prefix(self):
        settings = Settings()
        assert settings.model_config["env_prefix"] == "GDM_"

    def test_secret_key_generation(self):
        settings = Settings()
        assert len(settings.secret_key) >= 32
        assert settings.secret_key.encode() is not None