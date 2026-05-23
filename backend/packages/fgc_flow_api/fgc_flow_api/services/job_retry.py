"""Retry policy helpers for queued jobs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fgc_flow_api.models import Job


MAX_RETRIES = 3


def should_retry(job: Job) -> bool:
    return job.retry_count < MAX_RETRIES


def schedule_retry(job: Job) -> datetime | None:
    if not should_retry(job):
        return None
    delay_seconds = 2 ** job.retry_count
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
