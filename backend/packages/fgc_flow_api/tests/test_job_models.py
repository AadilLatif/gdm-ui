from __future__ import annotations

from fgc_flow_api.database import JobsBase
from fgc_flow_api.models import CachedResult, Job


def test_job_columns():
    columns = set(Job.__table__.columns.keys())
    assert {"id", "user_id", "job_type", "model_version_id", "status", "params", "status_events", "result_path", "retry_count", "next_retry_at", "created_at", "started_at", "completed_at", "error"} <= columns


def test_cached_result_columns_and_constraint():
    columns = set(CachedResult.__table__.columns.keys())
    assert {"model_version_id", "params_hash", "result_json", "result_path", "created_at"} <= columns
    unique_constraints = {c.name for c in CachedResult.__table__.constraints if getattr(c, "unique", False) or c.__class__.__name__ == "UniqueConstraint"}
    assert "uq_cached_result_key" in unique_constraints


def test_models_export_and_metadata():
    assert Job.__name__ == "Job"
    assert CachedResult.__name__ == "CachedResult"
    assert "job" in JobsBase.metadata.tables
    assert "cached_result" in JobsBase.metadata.tables
