# Architecture: fgc_flow_api

**Researched:** 2026-05-22
**Domain:** Power flow simulation REST API wrapping synchronous scientific computation
**Mode:** Greenfield architecture for FastAPI backend around fgc-flow solvers
**Overall confidence:** HIGH (verified against fgc-flow source, fgc_core codebase, and established FastAPI/Celery patterns)

---

## System Overview

```text
                              ┌──────────────────────────────────────┐
                              │            HTTP Clients              │
                              │  (curl, scripts, future frontend)   │
                              └──────────────┬───────────────────────┘
                                             │ JSON over HTTPS
                                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    fgc_flow_api (FastAPI/asyncio)                       │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  Router Layer   (async def — thin controllers)                │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │     │
│  │  │Auth Router   │  │Simulation    │  │Export Router     │    │     │
│  │  │(reuse fgc_   │  │Router        │  │(SQLite, CSV,     │    │     │
│  │  │ core's)      │  │(run, status, │  │ JSON download)   │    │     │
│  │  └──────┬───────┘  │ result)      │  └────────┬─────────┘    │     │
│  │         │          └──────┬───────┘           │             │     │
│  │         └─────────────────┼───────────────────┘             │     │
│  │                           │                                  │     │
│  │  ┌────────────────────────▼──────────────────────────┐      │     │
│  │  │  Dependencies Layer (reuse fgc_core)               │      │     │
│  │  │  get_current_user, get_admin_user, get_db          │      │     │
│  │  └────────────────────────┬──────────────────────────┘      │     │
│  │                           │                                  │     │
│  │  ┌────────────────────────▼──────────────────────────┐      │     │
│  │  │  Service Layer                                      │      │     │
│  │  │  ┌────────────────┐ ┌────────────────┐ ┌─────────┐  │      │     │
│  │  │  │AuthService     │ │JobService      │ │Export   │  │      │     │
│  │  │  │(from fgc_core)  │ │(enqueue,       │ │Service  │  │      │     │
│  │  │  │                │ │ poll, retrieve) │ │         │  │      │     │
│  │  │  └────────────────┘ └────────────────┘ └─────────┘  │      │     │
│  │  └────────────────────────┬──────────────────────────┘      │     │
│  │                           │                                  │     │
│  │  ┌────────────────────────▼──────────────────────────┐      │     │
│  │  │  Data Layer (shared with fgc_core + new tables)    │      │     │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌─────────┐ │      │     │
│  │  │  │Users (shared)│  │Projects/*    │  │SimulationR│ │      │     │
│  │  │  │              │  │ (shared)     │  │un, Export │ │      │     │
│  │  │  └──────────────┘  └──────────────┘  └─────────┘ │      │     │
│  │  └────────────────────────┬──────────────────────────┘      │     │
│  └───────────────────────────┼──────────────────────────────────┘     │
│                              │ (enqueue job, poll status)              │
└──────────────────────────────┼────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 Huey Job Queue (separate SQLite DB)                     │
│                                                                        │
│  ┌────────────────┐   ┌────────────────────┐   ┌──────────────────┐   │
│  │ Job Queue DB   │   │  Huey Consumer     │   │ Result Store     │   │
│  │ (fgc_flow_     │   │  (multi-process)   │   │ (same DB or file) │   │
│  │  jobs.db)      │   │  -k process -w N   │   │                  │   │
│  └───────┬────────┘   └──────┬─────────────┘   └──────────────────┘   │
│          │                   │                                         │
│          │    ┌──────────────▼──────────────┐                         │
│          │    │  Worker Process Pool        │                         │
│          │    │  ┌────────────────────┐     │                         │
│          │    │  │ Worker 1 (CPU 0)   │     │                         │
│          │    │  │ - Load DistSystem  │     │                         │
│          │    │  │ - Call fgc-flow    │     │                         │
│          │    │  │   solver (CPU)     │     │                         │
│          │    │  │ - Store result     │     │                         │
│          │    │  └────────────────────┘     │                         │
│          │    │  ┌────────────────────┐     │                         │
│          │    │  │ Worker 2 (CPU 1)   │     │                         │
│          │    │  │ ...                │     │                         │
│          │    │  └────────────────────┘     │                         │
│          │    │  ┌────────────────────┐     │                         │
│          │    │  │ Worker N (CPU N-1) │     │                         │
│          │    │  │ ...                │     │                         │
│          │    │  └────────────────────┘     │                         │
│          │    └─────────────────────────────┘                         │
└────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    fgc_core (shared package)                            │
│                                                                        │
│  - Auth (bcrypt, JWT, OAuth2PasswordBearer)                            │
│  - DB config (async SQLAlchemy + aiosqlite)                            │
│  - User/Project models                                                  │
│  - GDMService (in-memory DistributionSystem cache)                      │
│  - Config settings (env-based with GDM_ prefix)                         │
└────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    fgc-flow (pip package, sync/CPU)                     │
│                                                                        │
│  fgc_flow.optimize_ac_power_flow(system, ...)   ← CPU-bound (scipy)   │
│  fgc_flow.solve_dc_opf(system, ...)              ← CPU-bound (scipy)   │
│  fgc_flow.solve_lindistflow(system, ...)         ← CPU-bound (linear)  │
│  fgc_flow.export_*_to_sqlite(result, path)       ← I/O, sync           │
│                                                                        │
│  All solvers take a gdm.DistributionSystem object as first argument.   │
│  All solvers return frozen dataclass result objects.                    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### API Process (FastAPI async)

| Component | Location | Responsibility | Communicates With |
|-----------|----------|----------------|-------------------|
| Simulation Router | `routers/simulations.py` | HTTP endpoints for job submission, status polling, result retrieval | Dependencies layer for auth; JobService for queue ops; ExportService for result downloads |
| Export Router | `routers/exports.py` | HTTP endpoints for triggering and downloading exports | JobService to resolve run → result; ExportService for file generation |
| JobService | `services/job_service.py` | Enqueue simulation jobs, poll Huey for status, retrieve results, manage SimulationRun records | Huey queue API; Shared DB (SimulationRun model); fgc_core DB for model resolution |
| ExportService | `services/export_service.py` | Build export files from completed simulation results | fgc-flow `sqlite_export` module; Filesystem for export files |
| Dependencies | `dependencies.py` | Auth guards (`get_current_user`, `get_admin_user`), DB session — **reimported from fgc_core** | fgc_core `dependencies` module |
| Shared DB | `models/` directory | SimulationRun, ExportJob tables; Users and Projects reimported from fgc_core | SQLAlchemy async engine (same DB file as fgc_core) |

### Worker Process (Huey consumer)

| Component | Location | Responsibility | Communicates With |
|-----------|----------|----------------|-------------------|
| Huey App | `worker/huey_app.py` | Huey queue configuration with SQLite storage backend | Redis or SQLite (we use SQLite) |
| Task Defs | `worker/tasks.py` | Function definitions decorated with `@huey.task()` — load model, call fgc-flow, store result | fgc-flow solvers; Filesystem for model JSON; Results DB |
| Huey Consumer | Started via CLI | Process pool that picks up and executes queued tasks | Job queue DB; System CPUs |

---

## Data Flow

### Single Simulation Run (Primary Path)

```
User                          FastAPI                         JobService/Huey           Worker Process           fgc-flow
 │                              │                                │                          │                       │
 │ POST /api/simulations/run    │                                │                          │                       │
 │ {solver: "ac_opf",           │                                │                          │                       │
 │  model_id: "uuid",          │                                │                          │                       │
 │  params: {...}}              │                                │                          │                       │
 │ ─────────────────────────►   │                                │                          │                       │
 │                              │  Validate JWT                  │                          │                       │
 │                              │  (get_current_user)            │                          │                       │
 │                              │                                │                          │                       │
 │                              │  Resolve model_id →            │                          │                       │
 │                              │  file_path (query fgc_core     │                          │                       │
 │                              │  projects table)               │                          │                       │
 │                              │                                │                          │                       │
 │                              │  Create SimulationRun          │                          │                       │
 │                              │  record (status="queued")      │                          │                       │
 │                              │  in shared DB                  │                          │                       │
 │                              │                                │                          │                       │
 │                              │  enqueue task ───────────────► │                          │                       │
 │                              │  (run_id, file_path, solver,   │  Store job in SQLite     │                       │
 │                              │   params, user_id)             │  queue DB                 │                       │
 │                              │                                │                          │                       │
 │  {run_id, status: "queued"}  │                                │                          │                       │
 │ ◄──────────────────────────  │                                │                          │                       │
 │                              │                                │                          │                       │
 │  (immediate response)        │                                │                          │                       │
 │                              │                                │                          │                       │
 │                              │                                │  Worker picks up job     │                       │
 │                              │                                │  ─────────────────────►  │                       │
 │                              │                                │                          │  Load Distribution    │
 │                              │                                │                          │  System from file     │
 │                              │                                │                          │                       │
 │                              │                                │                          │  Call solver          │
 │                              │                                │                          │  ──────────────────►  │
 │                              │                                │                          │                       │
 │                              │                                │                          │    ◄──────────────    │
 │                              │                                │                          │  (result object)      │
 │                              │                                │                          │                       │
 │                              │                                │                          │  Store result:        │
 │                              │                                │                          │  - Serialize to JSON  │
 │                              │                                │                          │  - Write file         │
 │                              │                                │                          │  - Update job status  │
 │                              │                                │  ◄─────────────────────  │                       │
 │                              │                                │                          │                       │
 │                              │  Polling loop sees             │                          │                       │
 │                              │  status="completed"            │                          │                       │
 │                              │                                │                          │                       │
 │ GET /api/simulations/{id}/   │                                │                          │                       │
 │  status                      │                                │                          │                       │
 │ ─────────────────────────►   │                                │                          │                       │
 │                              │  Query SimulationRun           │                          │                       │
 │                              │  from shared DB                │                          │                       │
 │  {status: "completed"}       │                                │                          │                       │
 │ ◄──────────────────────────  │                                │                          │                       │
 │                              │                                │                          │                       │
 │ GET /api/simulations/{id}/   │                                │                          │                       │
 │  result                      │                                │                          │                       │
 │ ─────────────────────────►   │                                │                          │                       │
 │                              │  Load result from storage      │                          │                       │
 │                              │  (file or DB)                  │                          │                       │
 │  {solver, params, result_    │                                │                          │                       │
 │   data, violations, ...}     │                                │                          │                       │
 │ ◄──────────────────────────  │                                │                          │                       │
```

### Batch/Comparison Run

```
User                          FastAPI                          JobService                 Worker Pool
 │                              │                                │                          │
 │ POST /api/simulations/batch  │                                │                          │
 │ {solvers: ["ac_opf",        │                                │                          │
 │  "dc_opf", "lindistflow"],  │                                │                          │
 │  model_id: "uuid"}          │                                │                          │
 │ ─────────────────────────►   │                                │                          │
 │                              │  Create BatchRun record        │                          │
 │                              │                                │                          │
 │                              │  For each solver:              │                          │
 │                              │   - Create SimulationRun       │                          │
 │                              │   - Enqueue task ────────────► │  3 tasks enqueued        │
 │                              │                                │                          │
 │  {batch_id, runs: [{         │                                │  Worker 1: AC OPF        │
 │    solver, run_id, status}]} │                                │  Worker 2: DC OPF        │
 │ ◄──────────────────────────  │                                │  Worker 3: LinDistFlow   │
 │                              │                                │  (parallel on multi-core) │
```

### Export Flow

```
User                          FastAPI                     ExportService              Filesystem
 │                              │                            │                          │
 │ POST /api/exports/{run_id}   │                            │                          │
 │ {format: "sqlite"|"csv"|     │                            │                          │
 │  "json"}                     │                            │                          │
 │ ─────────────────────────►   │                            │                          │
 │                              │  Verify run is completed   │                          │
 │                              │  Load result data          │                          │
 │                              │                            │                          │
 │                              │  Delegate to ExportService │                          │
 │                              │  ────────────────────────► │                          │
 │                              │                            │  Generate export file    │
 │                              │                            │  ───────────────────────►│
 │                              │                            │  ◄────────────────────── │
 │                              │  Create ExportJob record   │                          │
 │  {export_id, download_url}   │                            │                          │
 │ ◄──────────────────────────  │                            │                          │
 │                              │                            │                          │
 │ GET /api/exports/{id}/       │                            │                          │
 │  download                    │                            │                          │
 │ ─────────────────────────►   │                            │                          │
 │                              │  Return FileResponse       │                          │
 │  <file bytes>                │                            │                          │
 │ ◄──────────────────────────  │                            │                          │
```

---

## Key Design Decisions

### Decision 1: Separate Job Queue (Huey + SQLite) over Celery/Redis

**Chose:** Huey with SQLite storage backend, multi-process workers (`-k process -w N`)

**Why not Celery + Redis:**
- Redis is an additional infrastructure dependency the project doesn't currently have
- Celery's complexity (broker, result backend, flower monitoring) is overkill for <10 workers
- Celery's dependency chain (kombu, billiard, vine) adds ~6 indirect dependencies
- The project is single-node; distributed task routing is not needed

**Why not custom SQLite queue:**
- Huey provides retries, scheduling, result storage, priority, task expiration out of the box
- Huey's multi-process worker mode (`-k process`) runs workers as separate processes, meaning each worker has its own GIL → true parallel CPU execution for power flow solvers
- Huey has been maintained for 10+ years (since 2013) with stable API

**Why not RQ (Redis Queue):**
- Same Redis dependency issue as Celery
- No SQLite backend support

**Why not ARQ:**
- Requires Redis, async-first (but our workers are CPU-bound/sync)
- Smaller community than Huey

**Why Huey over built-in `BackgroundTasks`:**
- `BackgroundTasks` runs in the same process as the event loop → CPU-bound work blocks all requests
- No persistence — tasks lost on crash
- No status tracking or result retrieval
- Cannot survive process restart
- Cannot run tasks in parallel across CPU cores

**SQLite storage consideration:** Huey with SQLite uses the standard `sqlite3` module (sync). This must use a **separate database file** from fgc_core's async aiosqlite connection to avoid WAL locking conflicts. The job queue DB (`fgc_flow_jobs.db`) is managed exclusively by Huey.

**Worker configuration:** Start with `-k process -w N` where N = number of CPU cores (or `max(2, os.cpu_count() - 1)`). For CPU-bound power flow solvers, using process-based workers is essential — thread workers would be GIL-limited.

### Decision 2: Shared Database with fgc_core (Single SQLite File)

**Chose:** Import fgc_core's database config directly; add new tables in the same SQLite file

**Rationale:**
- Users table is shared — simulation runs need user foreign keys
- Projects table is shared — simulation runs reference uploaded models
- No cross-database joins needed; everything in one DB
- The `SimulationRun` and `ExportJob` tables are lightweight (not high-volume)
- fgc_core already provides `Base`, `engine`, `async_session`, and `get_db()`
- Import pattern: `from fgc_core.database import Base, engine, async_session, get_db`

**What the shared DB contains:**
- `User` (from fgc_core)
- `Project` (from fgc_core)
- `SimulationRun` (new — run_id, user_id, solver_type, params, model_id, status, created_at, completed_at)
- `ExportJob` (new — export_id, run_id, format, status, file_path, created_at)

**What lives in separate files:**
- `fgc_flow_jobs.db` — Huey's job queue + result store (managed by Huey internally)
- Result JSON files — stored in `upload_dir/exports/` (same base as fgc_core uploads)
- Export files (SQLite/CSV/JSON) — stored in `upload_dir/exports/`

### Decision 3: Model Resolution via File Path, Not Object Serialization

**Chose:** Workers load `DistributionSystem` from the project file path on disk

**Rationale:**
- GDM's `DistributionSystem.from_json()` loads from file path
- The file already exists on disk (uploaded via fgc_core's project upload)
- Passing a file path in the job payload is cheap (a string vs. serializing a complex object graph)
- Avoids serialization issues with GDM objects (numpy arrays, nested Pydantic models)
- The worker process has access to the same filesystem

**Flow:**
1. API resolves `model_id` → `Project.file_path` from shared DB
2. API includes `file_path` in the job payload
3. Worker loads: `system = DistributionSystem.from_json(file_path)`
4. Worker passes `system` to the fgc-flow solver

**Caveat:** If `GDMService` in fgc_core has the system loaded in memory, the worker still needs to reload from disk. This is fine — file load is I/O-bound (a few ms with `ujson`) and doesn't dominate the computation.

### Decision 4: fgc-flow as a Direct Pip Dependency

**Chose:** Install `fgc-flow` as a pip package from local path, import its functions directly in worker tasks

**Rationale:**
- The fgc-flow package exposes clean function signatures (see source analysis)
- No need for an intermediary abstraction layer — the worker task calls `fgc_flow.optimize_ac_power_flow()` directly
- fgc-flow result objects (`PowerFlowOptimizationResult`, `DCOPFResult`, `LinDistFlowResult`) are frozen dataclasses → naturally thread-safe
- The API serializes these dataclass results into Pydantic schemas for the HTTP response

**Installation in pyproject.toml:**
```toml
[project.dependencies]
fgc-flow = { path = "~/Documents/github/fgc-flow", extras = ["optimization"] }
```

### Decision 5: Separate App Lifecycle (Not Mounted Under fgc_core)

**Chose:** fgc_flow_api is a standalone FastAPI app with its own lifespan, run as a separate uvicorn process

**Rationale:**
- fgc_flow_api has different scaling requirements (more workers for CPU work vs. more workers for I/O)
- Job queue needs a separate consumer process
- Clear separation of concerns — avoids bloating the fgc_core app
- Can be developed and deployed independently
- Both apps share the same database file, so auth/user data is consistent

**Shared authentication:** Both apps use the same JWT secret key and user database, so tokens minted by fgc_core are valid for fgc_flow_api without cross-calling.

---

## Patterns to Follow

### Pattern 1: Async API + Sync Worker via Job Queue

**What:** The FastAPI endpoint is `async def` and never blocks. CPU-bound work is delegated to a separate worker process via Huey.

**When:** Any endpoint that triggers power flow computation.

```python
# router/simulations.py — async, never blocks
@router.post("/run")
async def submit_simulation(
    req: SimulationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Resolve model
    project = await db.get(Project, req.model_id)
    if not project or project.user_id != user.id:
        raise HTTPException(404, "Model not found")
    
    # 2. Create run record
    run = SimulationRun(
        user_id=user.id, solver_type=req.solver_type,
        params=req.params.model_dump(), model_id=req.model_id,
        status="queued"
    )
    db.add(run)
    await db.commit()
    
    # 3. Enqueue (sync call to Huey, but very fast — just writes to SQLite)
    job_service.enqueue_simulation(
        run_id=str(run.id),
        file_path=project.file_path,
        solver_type=req.solver_type,
        params=req.params.model_dump(),
    )
    
    return SimulationRunResponse(run_id=run.id, status="queued")
```

```python
# worker/tasks.py — sync, CPU-bound
@huey.task()
def run_simulation_task(run_id: str, file_path: str, solver_type: str, params: dict):
    """Executed in a separate process by the Huey consumer."""
    system = DistributionSystem.from_json(file_path)
    
    if solver_type == "ac_opf":
        result = optimize_ac_power_flow_from_components(system, **params)
    elif solver_type == "dc_opf":
        result = solve_dc_opf_from_components(system, **params)
    elif solver_type == "lindistflow":
        result = solve_lindistflow(system, **params)
    
    # Store result
    result_path = store_result(run_id, result, solver_type)
    update_run_status(run_id, "completed", result_path=result_path)
```

### Pattern 2: Result Serialization via Pydantic Schemas

**What:** fgc-flow's dataclass results are mapped to Pydantic models for API responses.

**When:** Returning simulation results via HTTP.

```python
# schemas/results.py
class ACOPFResultResponse(BaseModel):
    success: bool
    message: str
    iterations: int
    initial_objective: float
    final_objective: float
    nodes: list[ACOPFNodeResult]
    # ...flattened from PowerFlowOptimizationResult

class SimulationResultResponse(BaseModel):
    run_id: str
    status: str
    result: ACOPFResultResponse | DCOPFResultResponse | LinDistFlowResultResponse | None
```

### Pattern 3: Result Storage on Disk, Reference in DB

**What:** Large simulation results (>1MB JSON) are written to files on disk, not stored in SQLite columns. The DB only stores status and file path.

**When:** Any simulation result is produced.

**Rationale:** SQLite blobs degrade query performance. Power flow results can be large (10K+ bus-phase nodes × multiple fields). Filesystem storage is faster and simpler.

```python
result_dir = settings.upload_dir / "simulation_results"
result_dir.mkdir(parents=True, exist_ok=True)
result_path = result_dir / f"{run_id}.json"
result_path.write_text(serialized_result_json)

# DB only stores the path
run.result_path = str(result_path)
run.status = "completed"
```

### Pattern 4: Reuse fgc_core's Auth + DB Config, Don't Duplicate

**What:** Import and re-use fgc_core's `dependencies.py`, `database.py`, and `config.py` instead of reimplementing.

**When:** Setting up the package.

```python
# In fgc_flow_api's config.py — extend fgc_core's settings
from fgc_core.config import settings as core_settings

class FlowAPISettings(BaseSettings):
    job_queue_db_path: str = str(core_settings.upload_dir / "fgc_flow_jobs.db")
    result_dir: str = str(core_settings.upload_dir / "simulation_results")
    export_dir: str = str(core_settings.upload_dir / "exports")
    max_workers: int = 4
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Running Solver Directly in `async def` Endpoint

**What happens:**
```python
@router.post("/run")
async def submit_simulation(...):
    system = DistributionSystem.from_json(file_path)
    result = optimize_ac_power_flow(system, ...)  # BLOCKS event loop!
    return result
```

**Why bad:** The event loop is frozen for 5-30s. No other requests can be served. All users experience timeouts. The server appears dead.

**Instead:** Always delegate CPU-bound work to the job queue. The endpoint only enqueues and returns immediately.

### Anti-Pattern 2: Sharing the aiosqlite Connection Between API and Worker

**What happens:** Worker process uses Huey's sync `sqlite3` on the same DB file that the async API process uses with `aiosqlite`.

**Why bad:** SQLite has filesystem-level locking. Two processes writing to the same SQLite file concurrently causes `database is locked` errors. Even with WAL mode, mixing sync and async access patterns is unreliable.

**Instead:** Use separate SQLite files:
- `gdm_studio.db` → async aiosqlite (API process only)
- `fgc_flow_jobs.db` → sync sqlite3 (Huey only, worker processes only)

### Anti-Pattern 3: Passing `DistributionSystem` Objects Through the Queue

**What happens:**
```python
# THIS DOESN'T WORK — the object lives in the API process memory
job_service.enqueue(run_simulation_task, system=system, solver="ac_opf")
```

**Why bad:** Huey (and most job queues) serialize arguments. `DistributionSystem` objects contain numpy arrays, nested Pydantic models, and complex graph structures. Serialization is slow, fragile, and may produce huge payloads.

**Instead:** Pass the file path. Workers load from disk.

### Anti-Pattern 4: Re-creating fgc_core's Auth in fgc_flow_api

**What happens:** Copying auth code (bcrypt, JWT, OAuth2PasswordBearer) into fgc_flow_api.

**Why bad:** The project already identified this as a DRY violation (backend/app/ vs fgc_core duplication — ~3,500 lines each). Repeating it again with a third copy is worse.

**Instead:** Import from fgc_core:
```python
from fgc_core.dependencies import get_current_user, get_admin_user, get_db
from fgc_core.database import Base, engine, async_session
```

### Anti-Pattern 5: Using `async def` for Worker Tasks (Huey)

**What happens:** Defining worker task functions as `async def` and trying to `await` solver calls.

**Why bad:** fgc-flow solvers are synchronous/CPU-bound. Making a sync function `async` and `await`ing it doesn't make it non-blocking — it still blocks the event loop in the worker process. If you use Huey's thread workers (`-k thread`), async functions don't run in the event loop at all.

**Instead:** Define worker tasks as plain `def` (sync). They run in separate processes (`-k process`) where there is no event loop to block. Each process uses 100% of one CPU core for the solver.

---

## Scalability Considerations

| Concern | Single User / Dev Testing | Multi-User / Production | Notes |
|---------|--------------------------|------------------------|-------|
| **Job queue throughput** | SQLite handles 100s of jobs/s — fine | SQLite becomes bottleneck at >10 concurrent workers writing | For production, migrate Huey to Redis backend; SQLite I/O contention scales poorly with concurrent writers |
| **Simulation concurrency** | 1 job at a time (single worker) | N jobs in parallel (N workers = CPU cores) | CPU-bound solvers benefit from process-level parallelism; start with `workers=os.cpu_count()` |
| **Result storage** | Small JSON files in `upload_dir/simulation_results/` | Same pattern scales to 10K+ files | Use subdirectories by date or user_id to avoid filesystem inode limits; consider S3/compatible object store |
| **Database locking** | Single SQLite file, low write volume | Concurrent SimulationRun inserts under async API + occasional worker status updates | SQLite WAL mode handles concurrent reads + single writer; stay <10 concurrent writers; for >1M runs, migrate to PostgreSQL |
| **Memory per worker** | System loading takes ~200MB RAM for a 10K-bus network | Stacks linearly with system size | Workers are short-lived (load → solve → store → die); no memory leak risk |

### When to Add Redis

- Queue throughput exceeds SQLite's capability (>100 jobs/s sustained)
- Need for real-time job progress via pub/sub
- Multiple API server instances need to share a queue
- Existing infrastructure already has Redis running

Until then, SQLite-backed Huey is simpler and sufficient.

### Multi-Worker Considerations

Huey with `-k process` spawns N Python processes. Each process:
- Has its own GIL → true parallel execution on multi-core CPUs
- Loads the `DistributionSystem` from disk independently (memory per worker = size of model)
- Writes results to the shared filesystem (separate files, no contention)
- Updates job status in the shared Huey SQLite DB (minimal writes, one `UPDATE` per job)

**Important:** OS-level file handle limits. Each worker loads the entire model JSON. For very large models (>500MB), consider memory limits. Start with `-w 4` and monitor.

---

## Suggested Build Order

This ordering is driven by dependency chains — each phase requires the components built in prior phases.

### Phase 1: Package Scaffolding + Shared DB Models
**Dependencies:** None (greenfield)
**Components:** `pyproject.toml`, package directory, model definitions, config, dependency imports
**Deliverable:** Runnable empty FastAPI app that imports from fgc_core and responds to health check
**Key files:**
- `backend/packages/fgc_flow_api/pyproject.toml` (deps: fgc-core, fgc-flow[optimization], fastapi, huey)
- `fgc_flow_api/__init__.py`
- `fgc_flow_api/config.py` (extends fgc_core settings)
- `fgc_flow_api/database.py` (imports fgc_core's `Base`, imports engine)
- `fgc_flow_api/models/simulation_run.py`, `export_job.py`
- `fgc_flow_api/main.py` (FastAPI app with lifespan, health endpoint)

### Phase 2: Job Queue Integration
**Dependencies:** Phase 1 (package exists), Phase 1 (models exist)
**Components:** Huey app config, task definitions, JobService
**Deliverable:** Simulation jobs can be enqueued, executed by worker, and status polled
**Key files:**
- `fgc_flow_api/worker/huey_app.py`
- `fgc_flow_api/worker/tasks.py` (load model → call fgc-flow → store result)
- `fgc_flow_api/services/job_service.py`
- `fgc_flow_api/services/result_storage.py`
- Worker startup script (`huey_consumer.py fgc_flow_api.worker.huey_app -k process -w 4`)

### Phase 3: Simulation API Endpoints
**Dependencies:** Phase 2 (job queue), Phase 1 (auth)
**Components:** Simulation router, request/response schemas, result serialization
**Deliverable:** Full run/status/result API with polling-based async pattern
**Key files:**
- `fgc_flow_api/routers/simulations.py`
- `fgc_flow_api/schemas/requests.py` (SimulationRequest)
- `fgc_flow_api/schemas/results.py` (ACOPFResultResponse, DCOPFResultResponse, LinDistFlowResultResponse)

### Phase 4: Model Resolution from fgc_core Projects
**Dependencies:** Phase 1 (shared DB access)
**Components:** ModelService, model resolution in job_service
**Deliverable:** Users can select uploaded models for simulation
**Key files:**
- `fgc_flow_api/services/model_service.py`
- **No new routers** — piggybacks on fgc_core's existing project router

### Phase 5: Export Endpoints
**Dependencies:** Phase 3 (completed results), Phase 2 (result storage)
**Components:** Export router, ExportService, file generation
**Deliverable:** Users can export results as SQLite/CSV/JSON and download
**Key files:**
- `fgc_flow_api/routers/exports.py`
- `fgc_flow_api/services/export_service.py`

### Phase 6: Batch/Comparison Runs
**Dependencies:** Phase 3 (single-run simulation)
**Components:** Batch router, batch orchestration in JobService
**Deliverable:** Multi-solver batch runs with comparison results
**Key files:**
- `fgc_flow_api/routers/batch.py`
- `fgc_flow_api/services/batch_service.py`

---

## Sources

- **fgc-flow source code** (verified: `ac_opf.py`, `dc_opf.py`, `lindistflow.py`, `sqlite_export.py`) — HIGH confidence on solver APIs being sync/CPU-bound
- **fgc_core architecture** (verified: `.planning/codebase/ARCHITECTURE.md`, `database.py`, `config.py`) — HIGH confidence on shared DB pattern, auth, and DI
- **Huey documentation** (huey.readthedocs.io) — HIGH confidence on SQLite storage backend, multi-process worker mode
- **FastAPI concurrency docs** (fastapi.tiangolo.com/async/) — HIGH confidence on sync-def vs async-def thread pool behavior
- **FastAPI GitHub issue #3725** — HIGH confidence on CPU-bound code blocking the event loop
- **Stack Overflow Q&A on FastAPI background tasks** (multiple threads, 2021-2026) — HIGH confidence on pattern for offloading CPU work
- **LiteQueue / SQLite job queue patterns** (multiple 2025-2026 blog posts) — MEDIUM confidence on SQLite being adequate for <100 jobs/s
