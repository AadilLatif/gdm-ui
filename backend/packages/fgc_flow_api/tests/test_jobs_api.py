from __future__ import annotations

from fgc_flow_api.schemas import JobResultResponse, JobStatusResponse, JobSubmissionResponse


def test_jobs_schemas_export():
    assert JobSubmissionResponse.model_fields["job_id"].is_required()
    assert JobStatusResponse.model_fields["model_version_id"].is_required()
    assert JobResultResponse.model_fields["job_id"].is_required()


def test_no_sync_toggle_present():
    from fgc_flow_api.schemas.jobs import JobSubmissionRequest

    assert "sync" not in JobSubmissionRequest.model_fields
