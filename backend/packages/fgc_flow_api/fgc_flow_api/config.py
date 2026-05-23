from pathlib import Path

from fgc_core.config import FGCBaseSettings


class Settings(FGCBaseSettings):
    app_name: str = "FGC Flow API"

    jobs_database_url: str | None = None

    model_config = {
        "env_prefix": "FGC_FLOW_",
        "env_file": Path(__file__).resolve().parent.parent / ".env",
    }


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
