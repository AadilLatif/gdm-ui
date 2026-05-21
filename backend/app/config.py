import secrets
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "GDM Studio API"
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    upload_dir: Path = base_dir / "uploads"
    database_url: str = f"sqlite+aiosqlite:///{base_dir / 'gdm_studio.db'}"

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

    model_config = {"env_prefix": "GDM_", "env_file": "../.env"}


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
