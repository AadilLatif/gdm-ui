"""Jobs API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fgc_flow_api.database import get_jobs_db
from fgc_flow_api.dependencies import get_current_user
from fgc_flow_api.models import Job
from fgc_flow_api.schemas.jobs import (
    JobResultResponse,
    JobStatusResponse,
    JobSubmissionRequest,
    JobSubmissionResponse,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_to_status(job: Job) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        model_version_id=job.model_version_id,
        job_type=job.job_type,
        params=job.params,
        status_events=job.status_events,
        retry_count=job.retry_count,
        next_retry_at=job.next_retry_at,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        result_path=job.result_path,
    )


@router.post("", response_model=JobSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(
    body: JobSubmissionRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_jobs_db),
):
    job = Job(
        user_id=user.id,
        job_type=body.job_type,
        model_version_id=body.model_version_id,
        status="PENDING",
        params=body.params,
        status_events=[{"status": "PENDING"}],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return JobSubmissionResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_jobs_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_to_status(job)


@router.get("/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(
    job_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_jobs_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResultResponse(job_id=job.id, result_json=None, result_path=job.result_path)
