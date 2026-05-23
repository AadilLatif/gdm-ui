# Requirements: FGC Flow API

**Defined:** 2026-05-22
**Core Value:** Users can run power flow simulations, manage models, and export results via a well-documented REST API — authenticated through the same credentials they already have for FGC Studio.

## v1 Requirements

### Authentication (reuse fgc_core)

- [ ] **AUTH-01**: API uses same JWT auth as fgc_core (bcrypt + python-jose, access + refresh tokens)
- [ ] **AUTH-02**: Protected endpoints validated via `get_current_user` dependency from fgc_core
- [ ] **AUTH-03**: Admin-only endpoints restricted via `get_admin_user` from fgc_core

### Foundation & Scaffolding

- [ ] **FND-01**: `fgc_flow_api` FastAPI package created at `backend/packages/fgc_flow_api/` with `pyproject.toml`
- [ ] **FND-02**: Package depends on `fgc_core` (imports auth, database, config) — no code duplication
- [ ] **FND-03**: Package depends on `fgc-flow` (imports solver logic)
- [ ] **FND-04**: FastAPI app with lifespan, CORS, health check endpoint
- [ ] **FND-05**: Shared SQLite configured with WAL mode and busy timeout to prevent write contention
- [ ] **FND-06**: Separate job queue DB file (`fgc_flow_jobs.db`) — avoids locking conflicts with shared auth DB

### Job Queue & Async Execution

- [ ] **JOB-01**: DB-backed job queue with `Job` model (id, status, type, params, result_path, created_at, started_at, completed_at, error)
- [ ] **JOB-02**: Job submission endpoint returns job ID for status polling
- [ ] **JOB-03**: Job status polling endpoint (`GET /api/jobs/{id}`)
- [ ] **JOB-04**: Job results retrieval endpoint (`GET /api/jobs/{id}/result`)
- [ ] **JOB-05**: Background worker processes queued jobs using `run_in_threadpool` for NumPy/SciPy solvers
- [ ] **JOB-06**: Job retry logic (max 3 retries on failure, exponential backoff)
- [ ] **JOB-07**: `CachedResult` model keyed by SHA-256 of sorted parameters for deterministic result caching

### Core Simulation Endpoints

- [ ] **SIM-01**: `POST /api/simulations/ac-opf` — Run AC OPF on a model, return results
- [ ] **SIM-02**: `POST /api/simulations/dc-opf` — Run DC OPF on a model
- [ ] **SIM-03**: `POST /api/simulations/lindistflow` — Run LinDistFlow on a model
- [ ] **SIM-04**: `POST /api/simulations/compare` — Run all solvers and compare results
- [ ] **SIM-05**: `POST /api/simulations/batch` — Run parameter sweeps across solver configs
- [ ] **SIM-06**: Solver configuration model with sensible defaults (tolerance, max_iter, verbose)
- [ ] **SIM-07**: All simulation endpoints support both sync (fast) and async/job (long-running) modes

### Model Management

- [ ] **MOD-01**: `POST /api/models/upload` — Upload GDM distribution system model file
- [ ] **MOD-02**: `GET /api/models` — List uploaded models with metadata
- [ ] **MOD-03**: `GET /api/models/{id}` — Inspect model topology and component summary
- [ ] **MOD-04**: `GET /api/models/{id}/versions` — List model version history
- [ ] **MOD-05**: `POST /api/models/{id}/versions` — Upload new version of existing model
- [ ] **MOD-06**: Model stored in DB with write-once immutable version records
- [ ] **MOD-07**: `DELETE /api/models/{id}` — Soft-delete model

### Export & Download

- [ ] **EXP-01**: `POST /api/exports/sqlite/{job_id}` — Trigger SQLite export of job results
- [ ] **EXP-02**: `GET /api/exports/{export_id}/download` — Download exported file
- [ ] **EXP-03**: `GET /api/simulations/{job_id}/results/csv` — Export results as CSV
- [ ] **EXP-04**: `GET /api/simulations/{job_id}/results/json` — Export results as JSON
- [ ] **EXP-05**: Temp file cleanup after download (fix existing leak pattern from fgc_studio)

### API Documentation & Usability

- [ ] **DOC-01**: Auto-generated OpenAPI/Swagger docs via FastAPI
- [ ] **DOC-02**: Well-typed Pydantic response models for all endpoints
- [ ] **DOC-03**: Consistent error response format across all endpoints
- [ ] **DOC-04**: Pagination for list endpoints (models, jobs, versions)

## v2 Requirements

### Differentiators (deferred)

- **DIFF-01**: Solver comparison endpoint with side-by-side result diff
- **DIFF-02**: Voltage violation report generation
- **DIFF-03**: Y-bus matrix inspection endpoint
- **DIFF-04**: Webhook notification on job completion
- **DIFF-05**: IEEE test feeder seeding endpoint
- **DIFF-06**: Result visualization data (for frontend charts)
- **DIFF-07**: Batch parameter sweep with configurable grid search

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time simulation streaming | Not needed for power flow analysis; batch/async sufficient |
| WebSocket push notifications | Polling-based job status is adequate for v1 |
| Redis/Celery/ARQ job queue | DB-backed queue sufficient for low-frequency jobs; Huey as optional v2 upgrade |
| CIM import/export | Not part of fgc-flow's domain; GDM format only |
| Short-circuit or dynamic simulation | fgc-flow doesn't implement these |
| Multi-user collaboration features | Single-user per model for v1 |
| Frontend UI | Backend-only package; frontend integration deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | TBD | Pending |
| AUTH-02 | TBD | Pending |
| AUTH-03 | TBD | Pending |
| FND-01 | TBD | Pending |
| FND-02 | TBD | Pending |
| FND-03 | TBD | Pending |
| FND-04 | TBD | Pending |
| FND-05 | TBD | Pending |
| FND-06 | TBD | Pending |
| JOB-01 | TBD | Pending |
| JOB-02 | TBD | Pending |
| JOB-03 | TBD | Pending |
| JOB-04 | TBD | Pending |
| JOB-05 | TBD | Pending |
| JOB-06 | TBD | Pending |
| JOB-07 | TBD | Pending |
| SIM-01 | TBD | Pending |
| SIM-02 | TBD | Pending |
| SIM-03 | TBD | Pending |
| SIM-04 | TBD | Pending |
| SIM-05 | TBD | Pending |
| SIM-06 | TBD | Pending |
| SIM-07 | TBD | Pending |
| MOD-01 | TBD | Pending |
| MOD-02 | TBD | Pending |
| MOD-03 | TBD | Pending |
| MOD-04 | TBD | Pending |
| MOD-05 | TBD | Pending |
| MOD-06 | TBD | Pending |
| MOD-07 | TBD | Pending |
| EXP-01 | TBD | Pending |
| EXP-02 | TBD | Pending |
| EXP-03 | TBD | Pending |
| EXP-04 | TBD | Pending |
| EXP-05 | TBD | Pending |
| DOC-01 | TBD | Pending |
| DOC-02 | TBD | Pending |
| DOC-03 | TBD | Pending |
| DOC-04 | TBD | Pending |

**Coverage:**
- v1 requirements: 38 total
- Mapped to phases: 0
- Unmapped: 38 ⚠️

---
*Requirements defined: 2026-05-22*
*Last updated: 2026-05-22 after initial definition*
