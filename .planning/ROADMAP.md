# Roadmap: FGC Flow API

## Overview

Build a FastAPI backend package (`fgc_flow_api`) that provides RESTful access to power flow simulation (AC OPF, DC OPF, LinDistFlow) via the existing `fgc-flow` library. The API reuses `fgc_core` for authentication (bcrypt + JWT, shared SQLite user database), uses a DB-backed job queue for async execution of CPU-bound solvers, and supports GDM model management with multi-format result export. Four phases deliver the full v1: foundation scaffolding → job queue infrastructure → core simulation endpoints (with basic model upload) → full model lifecycle and export.

## Phases

- [ ] **Phase 1: Foundation & Scaffolding** - Package setup, auth from fgc_core, database with WAL armor, health check, error format
- [ ] **Phase 2: Job Queue Infrastructure** - DB-backed async queue with status tracking, retry logic, and result caching
- [ ] **Phase 3: Core Simulation Endpoints** - AC OPF/DC OPF/LinDistFlow, compare, batch, solver config, plus basic model upload
- [ ] **Phase 4: Model Management & Export** - Full model lifecycle (versions, delete, inspect) and result export (CSV/JSON/SQLite)

## Phase Details

### Phase 1: Foundation & Scaffolding
**Goal**: Runnable FastAPI app that imports auth from fgc_core, has proper SQLite configuration with WAL armor, and responds to health checks with consistent error formatting
**Depends on**: Nothing (first phase)
**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06, AUTH-01, AUTH-02, AUTH-03, DOC-01, DOC-03
**Success Criteria** (what must be TRUE):
  1. User can start the server and hit `GET /health` — returns `{"status": "ok"}`
  2. User can register and login via API using email/password (reuses fgc_core auth tables and bcrypt)
  3. User receives JWT access + refresh tokens on login and can access protected endpoints via `Authorization: Bearer <token>`
  4. User gets consistent JSON error responses (`{"detail": "...", "error_code": "..."}`) on auth failures, validation errors, and 404s
  5. SQLite DB runs with WAL mode + busy_timeout=5000 — no "database is locked" errors under concurrent requests
**Plans**: 4 plans

Plans:
- [ ] 01-01: Package scaffolding — `pyproject.toml`, directory structure (`backend/packages/fgc_flow_api/`), dependencies on `fgc_core` and `fgc-flow`
- [ ] 01-02: Database setup — async SQLAlchemy engine with WAL armor PRAGMAs, session factory, separate jobs DB (`fgc_flow_jobs.db`)
- [ ] 01-03: Auth integration — import `get_current_user`, `get_admin_user`, `create_access_token`, `verify_password` from fgc_core; wire OAuth2PasswordBearer; configure JWT settings
- [ ] 01-04: FastAPI app — lifespan, CORS, health check endpoint, global exception handlers for consistent error format, OpenAPI metadata

### Phase 2: Job Queue Infrastructure
**Goal**: Background job execution with status tracking (PENDING → RUNNING → SUCCESS/FAILED), polling API, retry logic, and deterministic result caching
**Depends on**: Phase 1
**Requirements**: JOB-01, JOB-02, JOB-03, JOB-04, JOB-05, JOB-06, JOB-07, DOC-02
**Success Criteria** (what must be TRUE):
  1. User can submit a job and immediately receive a `{"job_id": "uuid"}` — response in under 100ms
  2. User can poll job status via `GET /api/jobs/{id}` and see transitions: PENDING → RUNNING → SUCCESS or FAILED with timestamps
  3. User can retrieve results from a completed job via `GET /api/jobs/{id}/result`
  4. Failed jobs are automatically retried up to 3 times with exponential backoff (visible in status history)
  5. Identical job submissions (same params SHA-256 hash) return cached results instead of re-executing
**Plans**: 4 plans

Plans:
- [ ] 02-01: Job persistence contracts — `Job`/`CachedResult` SQLite models with immutable `model_version_id` references and cache-key constraints
- [ ] 02-02: Queue API surface — typed submit/status/result schemas and `/api/jobs` router endpoints
- [ ] 02-03: Background worker — `run_in_threadpool` dequeuer that advances jobs through SQLite-backed lifecycle states
- [ ] 02-04: Retry + cache wiring — fixed 3-attempt backoff, SHA-256 cache reuse, and FastAPI lifespan bootstrap

### Phase 3: Core Simulation Endpoints
**Goal**: Users can upload GDM models, run AC OPF/DC OPF/LinDistFlow simulations individually or in compare/batch modes, with sync response for fast runs and job queue for long runs
**Depends on**: Phase 2
**Requirements**: SIM-01, SIM-02, SIM-03, SIM-04, SIM-05, SIM-06, SIM-07, MOD-01, MOD-02
**Success Criteria** (what must be TRUE):
  1. User can upload a GDM model file via `POST /api/models/upload` and receive a `{"model_id": "uuid"}` with metadata
  2. User can list uploaded models via `GET /api/models` with name, date, ID, and file size
  3. User can run AC OPF, DC OPF, and LinDistFlow on an uploaded model — each with their own endpoint returning structured results
  4. User can configure solver parameters (tolerance, max_iter, verbose) per simulation via request body
  5. User can run all three solvers simultaneously via `POST /api/simulations/compare` and see side-by-side results
  6. User can run batch parameter sweeps via `POST /api/simulations/batch` across solver configurations
  7. Simulations completing in <5s return synchronously with results inline; longer simulations return a job ID for polling
**Plans**: 4 plans

Plans:
- [ ] 03-01: Basic model upload + list endpoints — file upload to disk, store metadata in DB, list with basic fields
- [ ] 03-02: Single solver endpoints — `POST /api/simulations/ac-opf`, `/dc-opf`, `/lindistflow` with configurable `SolverConfig` schema, sync mode using `run_in_threadpool`
- [ ] 03-03: Compare + batch endpoints — orchestrate multiple solver runs, collect results into comparison response; batch uses job queue for each sweep point
- [ ] 03-04: Async mode integration — wire simulation endpoints to job queue for long-running solvers (>5s threshold); unify result format between sync and async paths

### Phase 4: Model Management & Export
**Goal**: Full model lifecycle (version history, soft-delete, topology inspection) and result export in CSV, JSON, and SQLite formats with proper temp file cleanup
**Depends on**: Phase 3
**Requirements**: MOD-03, MOD-04, MOD-05, MOD-06, MOD-07, EXP-01, EXP-02, EXP-03, EXP-04, EXP-05, DOC-04
**Success Criteria** (what must be TRUE):
  1. User can inspect a model's topology via `GET /api/models/{id}` — bus count, branch count, load totals, component summary
  2. User can upload a new version of an existing model; all versions are immutable (write-once) with timestamps
  3. User can browse model version history via `GET /api/models/{id}/versions`
  4. User can soft-delete a model via `DELETE /api/models/{id}` — model is hidden but versions preserved
  5. User can export simulation results as CSV (`GET /api/simulations/{job_id}/results/csv`) and JSON (`/results/json`)
  6. User can trigger a SQLite database export via `POST /api/exports/sqlite/{job_id}` and download the file
  7. Temp export files are cleaned up after download — no orphaned files accumulate on disk
  8. List endpoints (models, jobs, versions) support pagination with `page` and `limit` query parameters
**Plans**: 5 plans

Plans:
- [ ] 04-01: Model detail + topology inspection endpoint — load GDM from file, extract summary stats
- [ ] 04-02: Model version management — new version upload, version history listing, immutable version records
- [ ] 04-03: Model soft-delete — set `deleted_at` timestamp, exclude from list queries, preserve versions
- [ ] 04-04: CSV + JSON export endpoints — read simulation result from disk, serialize in requested format, return as downloadable file
- [ ] 04-05: SQLite export + download + temp cleanup + pagination — build SQLite DB from results, stream download, schedule temp file deletion with BackgroundTask, add pagination to all list endpoints

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Scaffolding | 0/4 | Not started | - |
| 2. Job Queue Infrastructure | 0/4 | Not started | - |
| 3. Core Simulation Endpoints | 0/4 | Not started | - |
| 4. Model Management & Export | 0/5 | Not started | - |
