# Project Research Summary

**Project:** FGC Flow API — REST API for power flow simulation (AC OPF, DC OPF, LinDistFlow)
**Domain:** Power flow / distribution system simulation REST API wrapping synchronous scientific computation (scipy/numpy)
**Researched:** 2026-05-22
**Confidence:** HIGH

## Executive Summary

The FGC Flow API wraps the existing `fgc-flow` Python solver library (AC OPF, DC OPF, LinDistFlow) into a FastAPI REST service. The core challenge is architectural: async HTTP framework wrapping synchronous, CPU-bound scientific computation. The recommended approach uses a DB-backed job queue (not Celery/Redis), async API endpoints that never block, and reuse of fgc_core's auth/database infrastructure.

**Key recommendation:** Start simple — a DB-backed job queue using SQLAlchemy models directly (zero new infrastructure) for v1, with an upgrade path to Huey or Taskiq+Redis if throughput demands it. Avoid Celery entirely — its operational complexity is not justified for this workload profile.

**Key risks:** (1) Running CPU-bound solvers directly in async endpoints blocks the event loop and freezes the server — solvers must be delegated to workers via `run_in_threadpool` or a job queue. (2) The existing codebase has a 3,500-line duplication between `backend/app/` and `fgc_core`; the new package must NOT create a third copy — import from `fgc_core` strictly. (3) SQLite write contention under concurrent simulation + auth operations requires WAL mode + busy_timeout from day 1.

**Mitigations:** SQLite WAL armor (PRAGMA configuration), strict import discipline from fgc_core, Claim Check pattern for passing data through queue (never serialize solver objects), streaming file uploads (never `await file.read()`), and immutable model versioning for reproducibility.

## Key Findings

### Recommended Stack

The technology stack is largely locked by fgc_core compatibility (FastAPI ≥0.115, SQLAlchemy 2.0 async, aiosqlite, Pydantic v2, bcrypt, python-jose). The key new decisions are around job queuing, caching, and testing.

**Core technologies:**
- **FastAPI ≥0.115**: Web framework — async-native, auto OpenAPI 3.1, Pydantic v2 integration
- **SQLAlchemy ≥2.0 async**: ORM/database — already in fgc_core; async sessions prevent event loop blocking
- **aiosqlite ≥0.20**: Async SQLite driver — locked by fgc_core; use for shared app database
- **pytest + pytest-asyncio + httpx**: Testing stack — `httpx.AsyncClient` with ASGI transport tests full stack without server

**Job queue (v1): DB-backed SQLAlchemy Job model** — zero new infrastructure; power flow workload is low-frequency (minutes between jobs); polling at 2s intervals is sufficient. Upgrade to Taskiq+Redis only if throughput exceeds ~50 concurrent jobs.

**Result caching:** Content-addressed SHA-256 hash cache in SQLite — deterministic inputs produce deterministic results; no TTL needed; keeps Redis out of v1.

**Testing:** `httpx.AsyncClient` with ASGI transport + in-memory SQLite + dependency overrides for full-stack integration tests without a running server.

See `.planning/research/STACK.md` for full details.

### Expected Features

The API wraps existing `fgc-flow` solver functions (~80% existing library code) with REST endpoints, auth, persistence, and async infrastructure (~20% new code).

**Must have (table stakes):**
- Simulation endpoints: Run AC OPF, DC OPF, LinDistFlow with configurable solver parameters (existing in fgc-flow, need thin REST wrapper)
- Model management: Upload/list/inspect/download/delete GDM JSON models
- Auth: Register/login via JWT (reuse fgc_core entirely)
- Job basics: Submit long-running simulation, poll status, list jobs
- Export: Download results as JSON/CSV, trigger SQLite export
- API usability: OpenAPI/Swagger docs (auto-generated), consistent error format, pagination

**Should have (differentiators):**
- Solver comparison (run all 3 solvers on one model, return side-by-side) — MCP tool already exists
- Voltage violation reports and line overload reports — simple post-processing on existing solver output
- Y-bus matrix inspection — fgc-flow already has `calculate_ybus`
- Model summary statistics (bus/branch counts, load totals)
- Webhook on job completion (eliminates polling)
- IEEE test feeder seeding (preload IEEE 13/34/37/123-bus models)

**Defer (v2+):**
- Batch model sweep (same solver against N models)
- Parameter sweep (vary one parameter across a range)
- Result diff between solvers (RMSE, error locations)
- API key access (alternative to JWT)
- cURL/Postman collections in docs

**Anti-features (deliberately NOT building):**
- Real-time streaming simulation (steady-state only)
- WebSocket push (polling + webhooks sufficient)
- Multi-user real-time collaboration
- CIM/CGMES import/export (GDM JSON only)
- Time-series / quasi-static simulation (different product)
- Short-circuit / fault analysis (different solver)
- Dynamic simulation / transient stability

See `.planning/research/FEATURES.md` for full feature tables and dependency graph.

### Architecture Approach

The architecture follows an **async API + sync worker** pattern via a job queue. FastAPI endpoints are `async def` and never block — they validate, enqueue, and return immediately. CPU-bound solver execution happens in separate workers (in-process thread pool for v1, separate processes later).

**Major components:**
1. **Simulation Router** (`routers/simulations.py`) — HTTP endpoints for job submission, status polling, result retrieval; thin controllers that delegate to services
2. **JobService** (`services/job_service.py`) — Enqueue jobs, poll status, retrieve results; wraps the queue abstraction so the router doesn't care if the backing is DB polling or Huey
3. **ExportService** (`services/export_service.py`) — Build export files (JSON/CSV/SQLite) from completed simulation results
4. **Worker Tasks** (`worker/tasks.py`) — Load model from disk, call fgc-flow solver, store result; sync functions running in thread pool or separate process
5. **Shared DB** (`models/`) — New `SimulationRun` and `ExportJob` tables alongside fgc_core's `User`/`Project` tables in the same SQLite file
6. **Dependencies** — Auth guards (`get_current_user`) imported from fgc_core, not reimplemented

**Key design decisions:**
- **Separate app lifecycle** — fgc_flow_api is a standalone FastAPI app (separate uvicorn process), not mounted under fgc_core; shares same database file and JWT secret
- **Model resolution via file path** — workers load DistributionSystem from file on disk; avoids serializing complex GDM objects through the queue (Claim Check pattern)
- **Result storage on disk**, not in DB — simulation results are large (>1MB JSON); DB stores only status and file path
- **Direct fgc-flow import** — workers call `fgc_flow.optimize_ac_power_flow()` directly; no intermediary abstraction layer

See `.planning/research/ARCHITECTURE.md` for data flow diagrams, component boundaries, and anti-patterns.

### Critical Pitfalls

The full pitfalls file (`.planning/research/PITFALLS.md`) identifies 13 pitfalls (6 critical, 4 moderate, 3 minor). The top 5 for roadmap planning:

1. **CPU-bound solver blocking async endpoints** — Running fgc-flow solvers directly in `async def` route handlers freezes the event loop (5-60s). Server goes unresponsive. **Prevention:** Never call solvers in async routes. Use `run_in_threadpool` for scipy/numpy-based solvers (they release the GIL during BLAS operations). Use `ProcessPoolExecutor` for pure-Python solver code. Offload anything >5s to job queue.

2. **Wrong job queue complexity** — Two failure modes: over-engineering (Celery+Redis before any users) or under-engineering (BackgroundTasks that lose tasks on crash). **Prevention:** Tiered approach — start with DB-backed SQLAlchemy Job model + polling loop (zero new infra). The queue abstraction must support retries, persistence, and status tracking from day 1, even if the backing implementation is simple.

3. **SQLite write contention** — Two processes (fgc_core API + fgc_flow_api) sharing the same SQLite file without WAL mode. Writes collide: "database is locked" errors cascade. **Prevention:** Apply WAL mode, busy_timeout=5000, synchronous=NORMAL as PRAGMA armor from day 1. Keep write transactions short. Never hold DB connections during computation. Consider separate Huey SQLite DB for job queue to avoid contention with app DB.

4. **No model/result versioning** — Models mutated in-place; no audit trail. Scientific results not reproducible. **Prevention:** Immutable model versions (write-once storage, new version on edit). Stamp every simulation result with model_version + solver_version + parameter hash. Write-once for results too.

5. **Duplicating fgc_core auth code** — Creating a third copy of auth logic when import is the correct path. **Prevention:** Strict rule: fgc_flow_api imports from fgc_core, never duplicates. Enforce in code review. Add new auth patterns (e.g., API keys) to fgc_core's dependencies.py, not a local copy.

See `.planning/research/PITFALLS.md` for comprehensive treatment (all 13 pitfalls with prevention, warning signs, and phase mapping).

## Implications for Roadmap

Based on combined research, the following phase structure is recommended:

### Phase 1: Foundation & Scaffolding
**Rationale:** Every other phase depends on package structure, DB access, config, and auth. Get these right first — mistakes here (SQLite config, import architecture, lazy loading) cascade into every subsequent phase.
**Delivers:** Runnable FastAPI app that imports from fgc_core, responds to health checks, has proper SQLite WAL armor, and passes tests.
**Addresses:** FEATURES items 12-14 (auth, reuse from fgc_core), 21-23 (API docs, error format, pagination)
**Avoids:** PITFALLS P5 (SQLite contention — set WAL/busy_timeout day 1), P6 (code duplication — enforce import rule), P8 (sync DB drivers — verify async engine), P10 (module-level heavy imports — lazy solver imports)
**Key files:** `pyproject.toml`, `config.py`, `database.py`, `models/simulation_run.py`, `models/export_job.py`, `main.py`, `dependencies.py` (re-exports from fgc_core)
**Research flag:** Well-documented patterns (standard FastAPI scaffolding). Skip deeper research; start coding.

### Phase 2: Job Queue Infrastructure
**Rationale:** The queue is the architectural backbone — every simulation endpoint depends on it. Build it early even if initially unused. Start with the simplest viable approach.
**Delivers:** Background job execution with status tracking (PENDING → RUNNING → SUCCESS/FAILED), polling API, result storage on disk.
**Addresses:** FEATURES items 15-17 (job submission, polling, listing)
**Avoids:** PITFALLS P1 (blocking event loop — queue prevents this by design), P2 (wrong complexity — start simple with DB-backed), P7 (pickle serialization — use Claim Check pattern)
**Implementation note:** Use the simplest viable approach from STACK.md (SQLAlchemy Job model + background coroutine polling loop). Do NOT add Huey or Taskiq in this phase. The abstraction boundary (`JobService.enqueue()`) should make migration to a proper task queue transparent.
**Research flag:** The exact polling interval (2s recommended), retry strategy (exponential backoff with max 3 retries), and cleanup policy need prototyping, not research. Low risk.

### Phase 3: Core Simulation Endpoints
**Rationale:** The primary value of the API — wrapping fgc-flow solvers. Phases 1-2 are prerequisites.
**Delivers:** `POST /simulations/ac-opf`, `POST /simulations/dc-opf`, `POST /simulations/lindistflow` with sync (inline for <5s) and async (job queue for >5s) modes. Solver parameter configuration. Synchronous return for small models.
**Addresses:** FEATURES items 1-6 (all simulation endpoints)
**Avoids:** PITFALLS P1 (blocking — use `run_in_threadpool` for inline execution or delegate to queue), P4 (versioning — stamp results with model + solver version)
**Key files:** `routers/simulations.py`, `schemas/requests.py`, `schemas/results.py`, `services/job_service.py`, `worker/tasks.py`
**Research flag:** fgc-flow solver function signatures are well-documented in the library source; the REST wrapper pattern is standard FastAPI. No deeper research needed.

### Phase 3b: Result Caching (Additive)
**Rationale:** Can be added independently during or after Phase 3. No dependency changes.
**Delivers:** Automatic cache-hit detection for identical simulation inputs. Instant response for repeated runs.
**Addresses:** Performance optimization (reduces solver re-execution)
**Implementation:** SHA-256 hash of sorted JSON params + solver type. Check cache before enqueue. Store in `simulation_cache` table.

### Phase 4: Model Management & Export
**Rationale:** Users need to upload models (Phase 4a) before they can run simulations on them (Phase 3). Exports (Phase 4b) require completed simulation results. These can proceed in parallel with Phase 3 if models are managed via fgc_core's existing project system.
**Delivers:** Model upload/list/inspect/download/delete. Result export as JSON/CSV/SQLite. File download with proper cleanup.
**Addresses:** FEATURES items 7-11 (model management), 18-20 (export basics), D11-D13 (export enhancements)
**Avoids:** PITFALLS P3 (loading files into memory — stream uploads to disk), P9 (temp file leaks — use BackgroundTask cleanup)
**Research flag:** File upload streaming patterns are well-documented for FastAPI. No deeper research needed.

### Phase 5: Differentiators
**Rationale:** These features are additive to the core simulation API. They leverage existing fgc-flow logic and the queue infrastructure built in Phases 2-3.
**Delivers:** Solver comparison, voltage/overload violation reports, Y-bus inspection, model stats, webhook on completion, IEEE test feeder seeding, model version history.
**Addresses:** FEATURES items D1 (compare solvers), D4-D6 (rich results, violations, overloads), D8-D10 (Y-bus, stats, versions), D14-D16 (dev experience), D17 (webhooks)
**Avoids:** PITFALLS P11 (polling intervals — rate-limit status checks), P12 (rate limiting — apply per-user quotas), P13 (solver version drift — pin and stamp versions)
**Research flag:** Batch parameter sweeps (D3) and webhook delivery (D17) are more complex than they appear. These may need a `/gsd-research-phase` during planning if the team hasn't built these patterns before.

### Phase Ordering Rationale

- **Foundation first:** Package scaffolding and DB config are prerequisites for everything. Getting SQLite WAL armor wrong in Phase 1 means data corruption in Phase 4.
- **Queue before simulation endpoints:** The queue abstraction must exist before the first simulation endpoint is wired. This prevents the anti-pattern of calling solvers directly in async handlers.
- **Model management before or concurrent with simulation:** Simulations need uploaded models. If fgc_core's project system already manages models, simulation can start sooner. If new model endpoints are needed, they must precede or parallel core simulation.
- **Differentiators last:** These add business value but don't block v1 launch. The core loop (upload model → run simulation → get results → export) must work first.
- **Caching is additive:** Can be slipped into any phase after Phase 3 without architectural changes.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 5 (Differentiators):** Batch parameter sweep (D3) is genuinely complex — needs careful design for efficient solver orchestration. Webhook delivery reliability (D17) needs retry/at-least-once semantics. Both may benefit from a `/gsd-research-phase` during planning.
- **Phase 2 (Job Queue):** If the team evaluates Huey or Taskiq as alternatives to the bare DB-backed approach, a quick `/gsd-research-phase` can validate the choice against actual workload expectations.

Phases with standard patterns (skip deeper research):
- **Phase 1 (Foundation):** Standard FastAPI package setup with fgc_core integration. Well-documented patterns.
- **Phase 3 (Core Simulation):** Thin REST wrappers over existing fgc-flow functions. The FastAPI + Pydantic pattern is textbook.
- **Phase 4 (Model Management/Export):** Standard file upload/download streaming. FastAPI docs cover this thoroughly.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | fgc_core compatibility locks most choices; job queue recommendation verified against multiple sources and benchmarks; all libraries actively maintained |
| Features | HIGH | Feature list drawn from existing fgc-flow source code, existing fgc-studio backend, and industry API comparisons (OpenDSS, GridAPPS-D, PyDSS) |
| Architecture | HIGH | Verified against fgc-flow source (solver APIs are sync/CPU-bound), fgc_core codebase (shared DB/auth patterns), and established FastAPI/Celery reference architectures |
| Pitfalls | HIGH | Every critical pitfall verified against official documentation or directly observed in existing codebase (CONCERNS.md); serialization concerns verified against Celery/kombu issue tracker |

**Overall confidence:** HIGH — all recommendations are backed by either existing codebase audit, official documentation, or multiple independent sources. The domain (scientific computation REST API) is well-understood with established patterns.

### Gaps to Address

- **Actual job queue throughput requirements are unknown** — the DB-backed approach is sufficient for v1 regardless, but the migration trigger to Huey/Taskiq/Redis needs real-world measurement.
- **fgc_core database migration schema** — the new `SimulationRun` and `ExportJob` tables need Alembic migrations or manual CREATE TABLE in the shared SQLite file. The approach depends on whether fgc_core already uses Alembic.
- **fgc_core project upload endpoint integration** — the exact API contract between fgc_flow_api and fgc_core for model resolution needs validation: does fgc_core expose `GET /projects/{id}` or does fgc_flow_api query the DB directly?
- **Batch parameter sweep design** (Phase 5 differentiator) — this is the most complex feature and needs dedicated design work. The current research identifies it as "high complexity" but doesn't resolve the architecture (e.g., incremental result streaming vs. full collection before response).

## Sources

### Primary (HIGH confidence)
- **fgc-flow source code** (`~/Documents/github/fgc-flow/src/fgc_flow/`) — solver function signatures, return types, parameter schemas
- **fgc_core architecture** (`.planning/codebase/ARCHITECTURE.md`, `database.py`, `config.py`) — shared DB pattern, auth DI, settings
- **CONCERNS.md** (`.planning/codebase/CONCERNS.md`) — existing code duplication (3,500 lines), temp file leaks, no rate limiting
- **FastAPI official docs** — async endpoints, testing, file uploads, OpenAPI config, background tasks
- **SQLite WAL mode docs** (`sqlite.org/wal.html`) — concurrency armor configuration
- **Celery FAQ + kombu issue tracker** — pickle serialization risks, Claim Check pattern
- **Huey documentation** (`huey.readthedocs.io`) — SQLite storage backend, multi-process worker mode

### Secondary (MEDIUM confidence)
- **Taskiq GitHub** (v0.12.3, 2.1K stars) — upgrade path for DB-backed queue; asyncio-native
- **ARQ GitHub** (maintenance-only mode) — confirmed not suitable for new projects
- **fastapi-taskflow** / **nano-queue** libraries — in-process persistent queue options for Phase 2
- **OmniBioAI model registry**, Determined AI model registry — model versioning patterns
- **Python task queue benchmarks** (Steven Yue, 2024-2025) — relative performance of ARQ, Taskiq, Celery
- **fedirz/fastapi-file-upload-benchmark** — UploadFile vs request.stream() throughput data
- **Industry API references** — OpenDSS wrapper, GridAPPS-D, PyDSS for feature validation

### Tertiary (LOW confidence — single source or marketing)
- **Siemens PSS/E 2000+ API surface** — only marketing page; used for general API capability signals
- **PowerWorld/ETAP API features** — limited public documentation; used as feature existence checks

---
*Research completed: 2026-05-22*
*Ready for roadmap: yes*
