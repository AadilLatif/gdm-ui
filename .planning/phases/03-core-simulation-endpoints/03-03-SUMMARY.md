---
phase: 03-core-simulation-endpoints
plan: 03
subsystem: api
tags: [fastapi, simulations, opf, job-queue, sqlite]

# Dependency graph
requires:
  - phase: 02-job-queue
    provides: async job persistence, status tracking, result caching
provides:
  - compare endpoint for AC OPF, DC OPF, and LinDistFlow side-by-side output
  - batch sweep job fan-out through the existing SQLite-backed queue
  - deterministic sweep expansion and cache-key reuse for queued simulations
affects: [03-04, simulations, jobs, solver execution]

# Tech tracking
tech-stack:
  added: [none]
  patterns: [shared solver serialization, deterministic cartesian sweep expansion, upfront sweep validation]

key-files:
  created:
    - backend/packages/fgc_flow_api/fgc_flow_api/services/batch_jobs.py
    - backend/packages/fgc_flow_api/tests/test_simulation_compare_batch.py
    - backend/packages/fgc_flow_api/tests/test_simulation_compare_batch_api.py
  modified:
    - backend/packages/fgc_flow_api/fgc_flow_api/services/solver_runner.py
    - backend/packages/fgc_flow_api/fgc_flow_api/routers/simulations.py
    - backend/packages/fgc_flow_api/fgc_flow_api/schemas/simulations.py
    - backend/packages/fgc_flow_api/fgc_flow_api/schemas/__init__.py
    - backend/packages/fgc_flow_api/fgc_flow_api/services/__init__.py

key-decisions:
  - "Reuse the single-solver runner internals for compare so compare output cannot drift from inline solver serialization."
  - "Keep batch jobs as normal solver jobs with sweep values embedded in SimulationRequest params so the existing worker can execute them unchanged."
  - "Cap batch sweep combinations before queueing to match the threat model and avoid accidental job explosions."

patterns-established:
  - "Pattern 1: compare endpoints execute against one loaded model and return AC/DC/LinDistFlow summaries plus a compact comparison summary"
  - "Pattern 2: batch endpoints validate the full sweep grid before any queue writes and preserve canonical cache keys via stable sweep ordering"

requirements-completed: [SIM-04, SIM-05]

# Metrics
duration: 25 min
completed: 2026-05-23
---

# Phase 03: Core Simulation Endpoints Summary

**Side-by-side solver compare plus queued parameter sweeps, both wired into the existing simulation/job stack**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-23T01:20:00Z
- **Completed:** 2026-05-23T01:44:48Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Added `POST /api/simulations/compare` to run AC OPF, DC OPF, and LinDistFlow from one loaded model.
- Added `POST /api/simulations/batch` to expand solver sweeps into queued jobs using the existing jobs DB.
- Kept sweep validation and cache-key generation deterministic so repeated identical sweeps stay reusable.

## Task Commits

1. **Task 1: Extend solver runner for compare and batch fan-out** - `2367a89` (feat)
2. **Task 2: Add compare and batch endpoints** - `c057c3d` (feat)

## Files Created/Modified
- `backend/packages/fgc_flow_api/fgc_flow_api/services/batch_jobs.py` - sweep expansion, validation, and job creation helpers
- `backend/packages/fgc_flow_api/fgc_flow_api/services/solver_runner.py` - shared compare runner and reusable single-solver internals
- `backend/packages/fgc_flow_api/fgc_flow_api/routers/simulations.py` - compare and batch routes
- `backend/packages/fgc_flow_api/fgc_flow_api/schemas/simulations.py` - compare/batch request and response models
- `backend/packages/fgc_flow_api/fgc_flow_api/schemas/__init__.py` - schema exports
- `backend/packages/fgc_flow_api/fgc_flow_api/services/__init__.py` - service exports
- `backend/packages/fgc_flow_api/tests/test_simulation_compare_batch.py` - helper-level compare/batch coverage
- `backend/packages/fgc_flow_api/tests/test_simulation_compare_batch_api.py` - endpoint wiring coverage

## Decisions Made
- Reused the single-solver serialization path for compare so the REST output stays aligned with inline solver behavior.
- Batched sweeps into normal solver jobs instead of inventing a separate async executor path.
- Enforced a sweep-combination cap up front to satisfy the threat model and keep queue creation bounded.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `pytest-asyncio` was not available in the package test environment, so async test cases were wrapped with `asyncio.run(...)` to keep the suite runnable.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for 03-04: result polling / export work can build on the compare and batch simulation surface.

## Self-Check: PASSED

- SUMMARY file present on disk.
- Task commits found: `2367a89`, `c057c3d`.
- Validation suite passed: `pytest -q` → 34 passed.

---
*Phase: 03-core-simulation-endpoints*
*Completed: 2026-05-23*
