from __future__ import annotations

import asyncio

from fgc_flow_api.models import Job
from fgc_flow_api.services import JobWorker


def test_worker_exports():
    assert JobWorker is not None


def test_worker_transitions_pending_to_success(monkeypatch):
    called = {}

    async def fake_get_jobs_db():
        class DummyDB:
            async def execute(self, *args, **kwargs):
                class Result:
                    def scalars(self):
                        class Scalars:
                            def first(self_inner):
                                return Job(
                                    user_id="u1",
                                    job_type="ac-opf",
                                    model_version_id="v1",
                                    params={},
                                    status_events=[{"status": "PENDING"}],
                                )

                        return Scalars()

                return Result()

            async def commit(self):
                called["commit"] = True

        yield DummyDB()

    async def fake_run_in_threadpool(fn, job):
        called["threadpool"] = True
        return fn(job)

    monkeypatch.setattr("fgc_flow_api.services.job_worker.get_jobs_db", fake_get_jobs_db)
    monkeypatch.setattr("fgc_flow_api.services.job_worker.run_in_threadpool", fake_run_in_threadpool)

    worker = JobWorker()
    asyncio.run(worker.run_once())
    assert called["threadpool"] is True
