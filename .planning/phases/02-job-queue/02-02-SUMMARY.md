# Plan 02-02 Summary: Queue API Surface

## Objective

Added the typed queue API surface for submitting jobs and polling results.

## Deliverables

- `schemas/jobs.py` with job submit/status/result models
- `routers/jobs.py` with `POST /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/result`
- `schemas/__init__.py` exports queue schemas
- `routers/__init__.py` exports `jobs_router`
- `tests/test_jobs_api.py` locks the API contract

## Verification

- `pytest tests/test_jobs_api.py -q` passes ✓
- Queue schemas are typed and require `model_version_id` ✓
- Jobs router is exported cleanly ✓

## Next

Plan 02-03: Background worker
