import secrets
from pathlib import Path

try:
    from pydantic_settings import BaseSettings as PydanticBaseSettings
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal test envs
    from pydantic import BaseModel

    class PydanticBaseSettings(BaseModel):
        model_config = {"extra": "ignore"}


class FGCBaseSettings(PydanticBaseSettings):
    app_name: str = "FGC API"
    debug: bool = False

    base_dir: Path = Path(__file__).resolve().parent.parent
    upload_dir: Path | None = None
    database_url: str | None = None

    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ]


class Settings(FGCBaseSettings):
    app_name: str = "GDM Studio API"

    secret_key: str = secrets.token_urlsafe(32)
    algorithm: str = "HS256"

    admin_username: str = "admin"
    admin_password: str = "admin"

    model_config = {
        "env_prefix": "GDM_",
        "env_file": Path(__file__).resolve().parent.parent / ".env",
    }


settings = Settings()
if settings.upload_dir is None:
    settings.upload_dir = Path("/home/aadil/Documents/gfc_files/uploads")
if settings.database_url is None:
    settings.database_url = "sqlite+aiosqlite:///home/aadil/Documents/gfc_files/database/gdm_studio.db"
settings.upload_dir.mkdir(parents=True, exist_ok=True)
