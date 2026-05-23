---
phase: 03-core-simulation-endpoints
plan: 04
subsystem: api
tags: [fastapi, async, sqlite, pydantic, jobs]

# Dependency graph
requires:
  - phase: 02-job-queue
    provides: [job queue, cached results, worker execution]
provides:
  - async inline/queued simulation dispatch
  - cached result polling for completed simulation jobs
  - route-registration regression coverage for the Phase 3 API surface
affects: [phase-04-model-lifecycle, queued-execution, jobs-api]

# Tech tracking
tech-stack:
  added: [none]
  patterns: [dispatch-response envelope, runtime-threshold handoff, cache-backed result polling]

key-files:
  created: [backend/packages/fgc_flow_api/fgc_flow_api/services/simulation_jobs.py, backend/packages/fgc_flow_api/tests/test_simulations_async.py, backend/packages/fgc_flow_api/tests/test_main_routes.py]
  modified: [backend/packages/fgc_flow_api/fgc_flow_api/schemas/simulations.py, backend/packages/fgc_flow_api/fgc_flow_api/routers/simulations.py, backend/packages/fgc_flow_api/fgc_flow_api/routers/jobs.py, backend/packages/fgc_flow_api/fgc_flow_api/services/job_worker.py, backend/packages/fgc_flow_api/tests/test_job_worker.py]

key-decisions:
  - "Keep a single simulation response envelope that can represent inline or queued execution without changing the endpoint shape."
  - "Use a deterministic 5-second runtime estimator to decide when to queue versus execute inline."
  - "Persist completed queued payloads in SQLite cache rows and a result file path so polling returns the normalized simulation payload."

patterns-established:
  - "Pattern 1: simulation endpoints can dispatch synchronously or enqueue based on estimated runtime."
  - "Pattern 2: completed jobs read through the cache table before falling back to stored path metadata."

requirements-completed: [SIM-07, MOD-02]

# Metrics
duration: 50 min
completed: 2026-05-23
---

# Phase 03: Core Simulation Endpoints Summary

**Fast AC/DC/LinDistFlow endpoints now switch between inline execution and queued jobs, with completed job polling returning the normalized cached simulation payload.**

## Performance

- **Duration:** 50 min
- **Started:** 2026-05-23T00:54:00Z
- **Completed:** 2026-05-23T01:44:24Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Inline simulation responses now share a dispatch envelope with queued responses.
- Slower runs enqueue jobs and persist normalized payloads to SQLite cache + result files.
- Job polling now returns the serialized simulation payload for completed queued jobs.
- Route registration is locked in with regression coverage for `/health` and the Phase 3 API prefixes.

## Task Commits

1. **Task 1: async dispatch + job result plumbing** - `7eaf067` (feat)
2. **Task 2: final route registration verification** - `c6aa966` (feat)

## Files Created/Modified
- `backend/packages/fgc_flow_api/fgc_flow_api/schemas/simulations.py` - dispatch response schema.
- `backend/packages/fgc_flow_api/fgc_flow_api/routers/simulations.py` - inline/queued handoff.
- `backend/packages/fgc_flow_api/fgc_flow_api/routers/jobs.py` - cached payload polling.
- `backend/packages/fgc_flow_api/fgc_flow_api/services/simulation_jobs.py` - runtime estimator and queue helpers.
- `backend/packages/fgc_flow_api/fgc_flow_api/services/job_worker.py` - simulation job execution and cache writes.
- `backend/packages/fgc_flow_api/tests/test_simulations_async.py` - async dispatch and polling tests.
- `backend/packages/fgc_flow_api/tests/test_main_routes.py` - route-registration regression test.
- `backend/packages/fgc_flow_api/tests/test_job_worker.py` - worker coroutine warning fix.

## Decisions Made
- Kept one response model for both inline and queued simulation flows.
- Used a deterministic threshold instead of a feature flag or separate endpoint.
- Stored completed queued payloads in the cache table to keep polling responses normalized.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Worker test needed to await coroutine results**
- **Found during:** Task 1 (async dispatch plumbing)
- **Issue:** The existing worker test triggered a coroutine warning once simulation jobs used the threadpool executor path.
- **Fix:** Updated the test helper to await coroutine results returned by the executor.
- **Files modified:** `backend/packages/fgc_flow_api/tests/test_job_worker.py`
- **Verification:** Full package test suite passed.
- **Committed in:** `7eaf067`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness and clean test execution; no scope creep.

## Issues Encountered
- `main.py` already mounted the Phase 3 routers and initialized both databases, so Task 2 was captured as a regression test instead of a code edit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 simulation endpoints are wired for inline and queued execution.
- Phase 4 can build on the cached result plumbing and model lifecycle work.

---
*Phase: 03-core-simulation-endpoints*
*Completed: 2026-05-23*

## Self-Check: PASSED

- Summary file exists.
- Task commit hashes `7eaf067` and `c6aa966` exist.
- Verified created files on disk.
