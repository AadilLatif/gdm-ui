---
phase: 03-core-simulation-endpoints
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, sqlite, zip-upload, pydantic, pytest]

# Dependency graph
requires:
  - phase: 02-job-queue
    provides: async SQLAlchemy/WAL patterns, shared fgc_flow_api package baseline, auth wrappers
provides:
  - flow metadata database/session helpers for uploaded models
  - Model ORM + Pydantic contracts for upload/list responses
  - authenticated `/api/models/upload` and `/api/models` endpoints
  - safe zip extraction cleanup and per-user model listing
affects: [03-core-simulation-endpoints-02, 03-core-simulation-endpoints-03, 03-core-simulation-endpoints-04, simulation execution plans]

# Tech tracking
tech-stack:
  added: [fastapi Form handling, SQLAlchemy async session helpers, zipfile path validation, pytest dependency overrides]
  patterns: [separate flow DB base, per-user model scoping, standalone router testing, cleanup-on-failure extraction]

key-files:
  created: [backend/packages/fgc_core/fgc_core/__init__.py, backend/packages/fgc_flow_api/fgc_flow_api/models/model.py, backend/packages/fgc_flow_api/fgc_flow_api/schemas/models.py, backend/packages/fgc_flow_api/fgc_flow_api/routers/models.py, backend/packages/fgc_flow_api/fgc_flow_api/services/model_service.py, backend/packages/fgc_flow_api/tests/test_model_contracts.py, backend/packages/fgc_flow_api/tests/test_model_upload_list.py, backend/packages/fgc_flow_api/sitecustomize.py]
  modified: [backend/packages/fgc_flow_api/fgc_flow_api/database.py, backend/packages/fgc_flow_api/fgc_flow_api/config.py, backend/packages/fgc_core/fgc_core/config.py, backend/packages/fgc_core/fgc_core/services/file_service.py, backend/packages/fgc_flow_api/fgc_flow_api/models/__init__.py, backend/packages/fgc_flow_api/fgc_flow_api/routers/__init__.py, backend/packages/fgc_flow_api/fgc_flow_api/schemas/__init__.py, backend/packages/fgc_flow_api/fgc_flow_api/services/__init__.py, backend/packages/fgc_flow_api/tests/conftest.py]

key-decisions:
  - "Use a dedicated flow metadata database instead of reusing the jobs DB to keep model records isolated from queue state."
  - "Expose uploads via multipart Form + file fields, with optional display name fallback to the archive stem."
  - "Clean up extracted upload directories on every archive validation failure before any DB commit."

patterns-established:
  - "Pattern 1: flow metadata models live on FlowBase and init_flow_db() creates only flow tables"
  - "Pattern 2: router/service split keeps upload validation and persistence testable without main.py wiring"
  - "Pattern 3: tests override auth + DB dependencies to exercise endpoints in isolation"

requirements-completed: [MOD-01, MOD-02]

# Metrics
duration: 1h 20m
completed: 2026-05-23
---

# Phase 03: Core Simulation Endpoints Summary

**Flow model uploads now persist safely in a dedicated metadata DB, with user-scoped listing and archive validation.**

## Performance

- **Duration:** 1h 20m
- **Started:** 2026-05-23T00:15:00Z
- **Completed:** 2026-05-23T01:35:13Z
- **Tasks:** 2
- **Files modified:** 17

## Accomplishments
- Added `FlowBase` / `init_flow_db()` for uploaded-model metadata separate from the jobs queue.
- Implemented `Model` ORM + upload/list response schemas and contract tests.
- Added authenticated upload/list endpoints with per-user filtering and safe zip cleanup.

## Task Commits

1. **Task 1: Add flow metadata DB and model contracts** - `0638dc8` (feat)
2. **Task 2: Implement safe model upload and listing** - `984be26` (feat)

## Files Created/Modified
- `backend/packages/fgc_flow_api/fgc_flow_api/database.py` - flow DB/session helpers
- `backend/packages/fgc_flow_api/fgc_flow_api/models/model.py` - uploaded model ORM
- `backend/packages/fgc_flow_api/fgc_flow_api/schemas/models.py` - upload/list contracts
- `backend/packages/fgc_flow_api/fgc_flow_api/services/model_service.py` - upload/list persistence logic
- `backend/packages/fgc_flow_api/fgc_flow_api/routers/models.py` - `/api/models` routes
- `backend/packages/fgc_core/fgc_core/services/file_service.py` - unsafe archive cleanup hardening
- `backend/packages/fgc_flow_api/tests/test_model_contracts.py` - ORM/schema contract coverage
- `backend/packages/fgc_flow_api/tests/test_model_upload_list.py` - upload/list behavior coverage

## Decisions Made
- Used a dedicated flow metadata database instead of the jobs DB.
- Kept the router standalone-testable with dependency overrides.
- Cleaned up extracted temp dirs on archive validation failure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added import-path bootstrap for workspace packages**
- **Found during:** Task 1
- **Issue:** `fgc_core` was not importable in the local test environment.
- **Fix:** Added `fgc_core` package init plus test bootstrap helpers so imports resolve without repo installation.
- **Files modified:** `backend/packages/fgc_core/fgc_core/__init__.py`, `backend/packages/fgc_flow_api/tests/conftest.py`, `backend/packages/fgc_flow_api/sitecustomize.py`, test modules
- **Verification:** `pytest -q` passes
- **Committed in:** `0638dc8`

**2. [Rule 3 - Blocking] Added settings fallbacks for missing env-loader packages**
- **Found during:** Task 1
- **Issue:** The executor environment lacked `pydantic-settings`.
- **Fix:** Added fallback `BaseSettings` imports in both config modules.
- **Files modified:** `backend/packages/fgc_flow_api/fgc_flow_api/config.py`, `backend/packages/fgc_core/fgc_core/config.py`
- **Verification:** test suite passes after dependency install
- **Committed in:** `0638dc8`

**3. [Rule 2 - Security] Hardened unsafe zip cleanup**
- **Found during:** Task 2
- **Issue:** Path-traversal rejection in zip extraction did not always remove the temp extraction directory.
- **Fix:** Cleaned the project dir before re-raising unsafe archive errors.
- **Files modified:** `backend/packages/fgc_core/fgc_core/services/file_service.py`
- **Verification:** path-traversal upload test returns 400 and leaves no row
- **Committed in:** `984be26`

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 security)
**Impact on plan:** Required for local verification and upload safety; no scope creep.

## Issues Encountered
- Local executor lacked several Python dependencies (`aiosqlite`, `pydantic-settings`, `python-jose`, `email-validator`); installed them to run the test suite.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Uploaded-model persistence is ready for later model lifecycle work.
- Simulation endpoint plans can now resolve `model_id` against stored model metadata.

---
*Phase: 03-core-simulation-endpoints*
*Completed: 2026-05-23*

## Self-Check: PASSED
- Summary file exists.
- Task commit hashes `0638dc8` and `984be26` exist in git log.
