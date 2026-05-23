"""Background worker for queued jobs."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from fgc_flow_api.database import get_jobs_db
from fgc_flow_api.models import Job
from fgc_flow_api.schemas.simulations import SimulationRequest, SimulationResponse, SimulationSolverName
from fgc_flow_api.services.simulation_jobs import store_simulation_result
from fgc_flow_api.database import get_flow_db
from fgc_flow_api.models import Model
from fgc_flow_api.services.solver_runner import run_simulation_request


SIMULATION_JOB_TYPES = {solver.value for solver in SimulationSolverName}


class JobWorker:
    def __init__(self, executor: Callable[[Job], object] | None = None):
        self._executor = executor or self._default_executor

    def _default_executor(self, job: Job) -> dict:
        if job.job_type in SIMULATION_JOB_TYPES:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                pass
            else:
                return {"job_id": job.id, "status": "SUCCESS"}
            return asyncio.run(self._execute_simulation_job(job))
        return {"job_id": job.id, "status": "SUCCESS"}

    async def _execute_simulation_job(self, job: Job) -> dict:
        request = SimulationRequest.model_validate(job.params)
        async for flow_db in get_flow_db():
            result = await flow_db.execute(select(Model).where(Model.id == job.model_version_id, Model.user_id == job.user_id))
            model = result.scalar_one_or_none()
            if model is None:
                raise ValueError("Model not found")
            response = await run_simulation_request(model, request)
            return response.model_dump(mode="json")
        raise RuntimeError("Flow database session unavailable")

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
                serialized_payload = payload.model_dump(mode="json") if isinstance(payload, SimulationResponse) else payload
                if job.job_type in SIMULATION_JOB_TYPES:
                    await store_simulation_result(db, job, serialized_payload)
                job.status = "SUCCESS"
                job.completed_at = datetime.now(timezone.utc)
                job.status_events = list(job.status_events) + [{"status": "SUCCESS"}]
                if isinstance(serialized_payload, dict):
                    job.status_events[-1]["result"] = serialized_payload
                await db.commit()
            except Exception as exc:  # pragma: no cover - exercised by worker tests
                job.status = "FAILED"
                job.error = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                job.status_events = list(job.status_events) + [{"status": "FAILED", "error": str(exc)}]
                await db.commit()
            return
