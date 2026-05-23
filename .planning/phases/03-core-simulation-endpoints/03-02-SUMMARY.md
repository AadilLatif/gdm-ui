---
phase: 03-core-simulation-endpoints
plan: 02
subsystem: api
tags: [fastapi, pydantic, gdm, fgc-flow]

# Dependency graph
requires:
  - phase: 03-core-simulation-endpoints/03-01
    provides: uploaded-model metadata, user-scoped model lookup, and upload/list persistence
provides:
  - typed AC/DC/LinDistFlow simulation contracts
  - inline single-solver execution helpers with JSON-safe serialization
  - dedicated simulation routes under `/api/simulations/*`
affects: [03-core-simulation-endpoints/03-03, 03-core-simulation-endpoints/03-04]

# Tech tracking
tech-stack:
  added: [fastapi.concurrency, pydantic enums, gdm distribution system loading]
  patterns: [explicit solver enum routing, threaded solver execution, ownership-checked model resolution]

key-files:
  created:
    - backend/packages/fgc_flow_api/fgc_flow_api/schemas/simulations.py
    - backend/packages/fgc_flow_api/fgc_flow_api/routers/simulations.py
    - backend/packages/fgc_flow_api/fgc_flow_api/services/solver_runner.py
    - backend/packages/fgc_flow_api/tests/test_simulation_contracts.py
    - backend/packages/fgc_flow_api/tests/test_simulations_api.py
  modified:
    - backend/packages/fgc_flow_api/fgc_flow_api/main.py

key-decisions:
  - "Use an explicit SimulationSolverName enum so request validation rejects unsupported solver strings before execution."
  - "Serialize solver dataclasses into plain JSON-compatible envelopes instead of returning raw solver objects."

patterns-established:
  - "Pattern 1: Every simulation request is resolved through the authenticated user before any solver work begins."
  - "Pattern 2: Fast solver paths run inline via run_in_threadpool and return a normalized response envelope."

requirements-completed: [SIM-01, SIM-02, SIM-03, SIM-06]

# Metrics
duration: 1h 5m
completed: 2026-05-23
---

# Phase 03: Core Simulation Endpoints Summary

Typed AC/DC/LinDistFlow endpoints now resolve the caller's model ownership, execute one solver inline, and return JSON-safe solver payloads.

## Performance

- **Duration:** 1h 5m
- **Started:** 2026-05-23T00:00:00Z
- **Completed:** 2026-05-23T01:05:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added request/response contracts for single-solver simulations with explicit solver names.
- Wired `/api/simulations/ac-opf`, `/dc-opf`, and `/lindistflow` through a shared inline runner.
- Validated model ownership before solver execution and covered 404/threading behavior in tests.

## Task Commits

1. **Task 1: Define simulation request and response contracts** - `af2096f` (feat)
2. **Task 2: Implement single-solver execution and endpoints** - `e57d616` (feat)

## Files Created/Modified
- `backend/packages/fgc_flow_api/fgc_flow_api/schemas/simulations.py` - simulation request/response contracts
- `backend/packages/fgc_flow_api/fgc_flow_api/routers/simulations.py` - simulation endpoints
- `backend/packages/fgc_flow_api/fgc_flow_api/services/solver_runner.py` - inline solver execution + serialization
- `backend/packages/fgc_flow_api/fgc_flow_api/main.py` - mounts simulation routes and initializes flow DB
- `backend/packages/fgc_flow_api/tests/test_simulation_contracts.py` - contract validation tests
- `backend/packages/fgc_flow_api/tests/test_simulations_api.py` - endpoint behavior tests

## Decisions Made
- Use explicit solver enums instead of free-form strings.
- Keep fast solver runs synchronous from the API perspective and thread the CPU work.
- Return serialized solver results in a normalized envelope for all three endpoints.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for batch/comparison simulation routing in 03-03.
- Ready for async job handoff/status polling in 03-04.

---
*Phase: 03-core-simulation-endpoints*
*Completed: 2026-05-23*

## Self-Check: PASSED
