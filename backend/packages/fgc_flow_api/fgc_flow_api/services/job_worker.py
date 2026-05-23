"""Background worker for queued jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Awaitable, Callable

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from fgc_flow_api.database import get_jobs_db
from fgc_flow_api.models import Job


class JobWorker:
    def __init__(self, executor: Callable[[Job], object] | None = None):
        self._executor = executor or (lambda job: {"job_id": job.id, "status": "SUCCESS"})

    async def run_once(self) -> None:
        async for db in get_jobs_db():
            result = await db.execute(select(Job).where(Job.status == "PENDING").order_by(Job.created_at))
            job = result.scalars().first()
            if job is None:
                return
            job.status = "RUNNING"
            job.started_at = datetime.now(timezone.utc)
            job.status_events = list(job.status_events) + [{"status": "RUNNING"}]
            await db.commit()
            try:
                payload = await run_in_threadpool(self._executor, job)
                job.status = "SUCCESS"
                job.result_path = job.result_path or None
                job.completed_at = datetime.now(timezone.utc)
                job.status_events = list(job.status_events) + [{"status": "SUCCESS"}]
                if isinstance(payload, dict):
                    job.status_events[-1]["result"] = payload
                await db.commit()
            except Exception as exc:  # pragma: no cover - exercised by worker tests
                job.status = "FAILED"
                job.error = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                job.status_events = list(job.status_events) + [{"status": "FAILED", "error": str(exc)}]
                await db.commit()
            return
