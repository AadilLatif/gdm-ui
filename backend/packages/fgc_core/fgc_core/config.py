import secrets
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "GDM Studio API"
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    upload_dir: Path | None = None
    database_url: str | None = None

    # Auth
    secret_key: str = secrets.token_urlsafe(32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Default admin (seeded on first startup)
    admin_username: str = "admin"
    admin_password: str = "admin"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]

    model_config = {"env_prefix": "GDM_", "env_file": base_dir / ".env"}


settings = Settings()
if settings.upload_dir is None:
    settings.upload_dir = Path("/home/aadil/Documents/gfc_files/uploads")
if settings.database_url is None:
    settings.database_url = f"sqlite+aiosqlite:///home/aadil/Documents/gfc_files/database/gdm_studio.db"
settings.upload_dir.mkdir(parents=True, exist_ok=True)
