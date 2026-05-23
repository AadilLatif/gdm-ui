# Phase 2 Context: Job Queue Infrastructure

## Locked Decisions

| Decision | Why it matters |
|----------|----------------|
| Always queue simulation jobs | Keep execution behavior uniform; no inline/sync shortcut for fast runs. |
| SQLite DB records are the source of truth | Job state, retries, and result pointers live in SQLite, not memory. |
| Retry policy is fixed at 3 attempts | Downstream planning can assume bounded retry behavior. |
| Results are stored in SQLite records with file pointers as needed | DB is authoritative; files are secondary payload storage. |
| Uploaded models are immutable version records | Every upload creates a new version, preserving reproducibility. |
| Jobs reference model version IDs | Simulations are pinned to a specific upload for reproducibility. |

## Phase Boundary Notes

- Phase 2 builds the queue and result tracking layer only.
- Inline simulation responses are out of scope for Phase 2.
- Model management beyond immutable versioning remains for later phases.

## Reusable Assets

- `backend/packages/fgc_flow_api/fgc_flow_api/database.py` already provides a separate jobs DB and `JobsBase`.
- `backend/packages/fgc_flow_api/fgc_flow_api/main.py` already initializes the jobs DB in lifespan.
- `fgc_flow/sqlite_export.py` already defines SQLite schemas and export patterns that later phases can reuse.

## Deferred Ideas

- Adaptive sync/async thresholds for fast runs — deferred; Phase 2 will treat all jobs as queued.
- User-configurable retry policy — deferred; keep fixed 3-retry behavior for v1.
- Mutable model replacement — rejected; versioned uploads are the chosen contract.

## Research/Planning Guidance

- Research should focus on durable queue mechanics that fit SQLite-backed state.
- Planning should assume model version IDs are required inputs to jobs.
- Planning should not reopen the inline-vs-async debate.

---
*Last updated: 2026-05-22 after Phase 2 discussion*
