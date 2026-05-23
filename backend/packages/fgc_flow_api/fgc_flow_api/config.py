from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FGC Flow API"
    debug: bool = False

    base_dir: Path = Path(__file__).resolve().parent.parent
    upload_dir: Path | None = None
    database_url: str | None = None
    jobs_database_url: str | None = None

    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    model_config = {"env_prefix": "FGC_FLOW_", "env_file": base_dir / ".env"}


settings = Settings()
if settings.upload_dir is None:
    settings.upload_dir = Path.home() / "Documents" / "gfc_files" / "uploads"
if settings.database_url is None:
    settings.database_url = "sqlite+aiosqlite:///" + str(
        Path.home() / "Documents" / "gfc_files" / "database" / "fgc_flow.db"
    )
if settings.jobs_database_url is None:
    settings.jobs_database_url = "sqlite+aiosqlite:///" + str(
        Path.home() / "Documents" / "gfc_files" / "database" / "fgc_flow_jobs.db"
    )
settings.upload_dir.mkdir(parents=True, exist_ok=True)
