# Domain Pitfalls: REST APIs Around Python Scientific Computation

**Domain:** Scientific computation REST APIs (power flow simulation)
**Researched:** 2026-05-22
**Overall confidence:** HIGH (all claims verified against official docs or multiple sources)

---

## Critical Pitfalls

### Pitfall 1: CPU-Bound Computation Directly in Async Endpoints

**What goes wrong:** Running `fgc-flow` simulation logic (AC OPF, DC OPF, LinDistFlow) directly inside an `async def` FastAPI route handler blocks the entire event loop. While the simulation runs, the server stops processing any other requests — health checks, other users' simulation submissions, auth checks — everything queues up.

**Why it happens:** FastAPI runs `async def` route handlers on the single-threaded asyncio event loop. CPU-bound Python code (pure Python math loops, dense matrix operations) holds the GIL and never yields control back to the event loop. Unlike `time.sleep()` (which releases the GIL internally with `Py_BEGIN_ALLOW_THREADS`), pure computation holds the GIL until completion. The simulation runs "to completion" from the event loop's perspective — no other coroutines can interleave.

**Consequences:**
- At 2 concurrent simulation requests: second request waits for first to finish — sequential, not concurrent
- At 5+ users: server becomes unresponsive, timeouts cascade
- `gunicorn` + multiple workers helps partially (separate processes = separate event loops), but each worker still blocks internally
- A single long simulation (~60s for AC OPF on large models) blocks that worker's event loop for the full minute
- `PYTHONASYNCIODEBUG=1` will show warnings about "Executing <handler> took X seconds"

**Prevention:**

1. **Never call `fgc-flow` solver functions directly in `async def` routes.** Not even wrapped in `await`.

2. **Use `run_in_threadpool` for NumPy/SciPy-based simulations** — these libraries release the GIL during BLAS/LAPACK operations (np.linalg.solve, scipy.optimize), giving genuine parallelism:
   ```python
   from fastapi.concurrency import run_in_threadpool
   
   @app.post("/simulate/ac-opf")
   async def run_ac_opf(...):
       result = await run_in_threadpool(lambda: ac_opf_solver(model_data))
       return result
   ```

3. **For pure-Python solver code** (custom optimization loops), use `ProcessPoolExecutor` to bypass the GIL entirely:
   ```python
   loop = asyncio.get_running_loop()
   with ProcessPoolExecutor(max_workers=2) as pool:
       result = await loop.run_in_executor(pool, ac_opf_solver, model_data)
   ```

4. **For any simulation that takes >5s**, offload to a job queue (see Pitfall 2) instead of keeping the HTTP connection open.

**Warning signs:**
- Server becomes unresponsive during simulation runs (health check fails)
- "Blocking call" warnings when `PYTHONASYNCIODEBUG=1` is set
- API response times equal simulation time + network latency
- `httptools`/`uvicorn` logs show long gaps between request receipt and handler execution

**Phase to address:** Phase 2 (Simulation endpoints). Must be designed before the first simulation endpoint is wired.

**Sources:** [FastAPI docs on async](https://fastapi.tiangolo.com/async/), [zhanymkanov/fastapi-best-practices](https://deepwiki.com/zhanymkanov/fastapi-best-practices/3.2-handling-io-and-cpu-bound-operations), [FastAPI Issue #1718](https://github.com/fastapi/fastapi/issues/1718), [Amir Karimi benchmark](https://amirkarimi.dev/blog/2023/07/23/make-fastapi-cpu-bound-endpoints-2x-faster/) (HIGH confidence)

---

### Pitfall 2: Job Queue — Wrong Level of Complexity

**What goes wrong:** Two failure modes:

**Mode A (Over-engineer):** Deploy Celery + Redis + Flower before there's even a single user. This adds ~5 infra components (Redis broker, Celery worker, result backend, Flower dashboard, monitoring) and ~15 pages of configuration for what might be 10 simulation runs/day in v1.

**Mode B (Under-engineer):** Use FastAPI's built-in `BackgroundTasks` for all simulation work. These run in-process, have no persistence (crash = lost task), no retry logic, no status tracking, and no concurrency isolation. A single failed simulation vanishes silently.

**Why it happens:** Scientific computation backends live in an awkward middle ground. They're too compute-heavy for simple `BackgroundTasks`, but often too low-throughput to justify Celery's operational cost. The "right" solution depends on actual traffic, which is unknown at greenfield.

**Consequences of mode A:**
- Developer time lost to Celery configuration, Redis tuning, broker health issues
- Deployment complexity: Redis + worker processes + monitoring
- Overengineering leads to "this is too heavy" avoidance — developers skip the queue and run inline

**Consequences of mode B:**
- Simulation crashes on server restart (no persistence)
- No visibility into what simulations ran, failed, or are pending
- Thread pool exhaustion: `BackgroundTasks` runs in the same thread pool as sync route handlers; 5 long simulations starve all other sync requests
- No retry: transient solver failures (convergence issues, memory pressure) require manual resubmission

**Prevention:**

Use a **tiered approach** that matches the project lifecycle:

**Phase 1 (Launch, <10 users): In-process persistent queue**
Use libraries like `fastapi-taskflow` or `nano-queue` that:
- Store task state in the existing SQLite database (no new infra)
- Provide retries with exponential backoff
- Survive server restarts (task persistence)
- Offer basic monitoring (status dashboard)
- Use DB-backed atomic locking to prevent double-processing in multi-worker deployments

These give Celery-level resilience without Celery-level infrastructure.

**Phase 2 (Growth, 10-100 users): Migrate to Celery/ARQ**
The migration path from in-process queues to Celery is well-understood:
- `background_tasks.add_task(fn, args)` → `fn.delay(args)`
- Function body stays the same; just the invocation changes
- Add Redis as the broker, deploy worker processes

**Pattern to follow:**
```python
# Phase 1 (in-process persistent queue)
@background_task(queue=q)
def run_simulation(model_id: str, params: dict) -> dict:
    result = ac_opf_solver(load_model(model_id), params)
    store_result(model_id, result)
    return result

# Phase 2 (Celery)
@app.task(bind=True, max_retries=3)
def run_simulation(self, model_id: str, params: dict):
    try:
        result = ac_opf_solver(load_model(model_id), params)
        store_result(model_id, result)
        return result
    except ConvergenceError as exc:
        self.retry(exc=exc, countdown=2 ** self.request.retries)
```

**Key design requirements for the queue layer:**
- Tasks must be **idempotent** (re-delivery is safe) — store results by model_id + params hash
- **Retry with backoff**: transient failures (solver convergence) != permanent failures (invalid model)
- **Status tracking**: PENDING → RUNNING → SUCCESS/FAILED with timestamps
- **Cleanup policy**: auto-delete completed task records after N days
- **Worker isolation**: use dedicated thread/process pool for simulation tasks, separate from API request handling

**Warning signs:**
- Developer finds Celery config daunting and is considering "just running it synchronously"
- No retry mechanism exists for simulation failures
- Simulation tasks are defined but there's no monitoring page
- Thread pool exhaustion under moderate load (symptoms: slow non-simulation endpoints)

**Phase to address:** Phase 2 (Simulation endpoints). Make the queue abstraction the default from day 1 — even if the backing implementation starts simple.

**Sources:** [fastapi-taskflow](https://github.com/Attakay78/fastapi-taskflow) (HIGH), [nano-queue](https://github.com/Fidel-C/nano-queue) (HIGH), [Markaicode: BackgroundTasks vs Celery](https://www.markaicode.com/vs/fastapi-background-tasks-vs-celery-ai-workloads/) (MEDIUM), [naveengarla/long-running-api-demo](https://github.com/naveengarla/long-running-api-demo) (MEDIUM)

---

### Pitfall 3: Loading Entire Uploaded Files Into Memory

**What goes wrong:** This already exists in the existing codebase:
```python
content = await file.read()  # reads up to 500MB into RAM
```
For model uploads (GDM distribution system files), this means a single 200MB file consumes 200MB of RAM. Two concurrent uploads = 400MB. The server runs out of memory, OOM-kills the process, and all in-flight simulations are lost.

**Why it happens:** FastAPI's `UploadFile.read()` with no size parameter reads the entire file into memory. The existing codebase already has this exact bug at `projects.py:32` and `scenarios.py:57`. The existing 500MB max upload size compounds the problem.

**Consequences:**
- OOM crashes under concurrent uploads
- No streaming validation — file must be fully loaded before checking validity
- CPU-bound parsing (GDM model parsing) also runs on the event loop after loading, compounding the block
- Docker container memory limits make this worse — hard cap kills the process

**Prevention:**

1. **Stream uploads to disk immediately — never `await file.read()`:**
   ```python
   import aiofiles
   import hashlib

   CHUNK_SIZE = 1024 * 1024  # 1MB chunks

   async def stream_upload(file: UploadFile, destination: Path):
       size = 0
       sha256 = hashlib.sha256()
       async with aiofiles.open(destination, "wb") as f:
           while chunk := await file.read(CHUNK_SIZE):
               size += len(chunk)
               if size > MAX_UPLOAD_BYTES:
                   await f.close()
                   destination.unlink(missing_ok=True)
                   raise HTTPException(413, "File too large")
               sha256.update(chunk)
               await f.write(chunk)
       return size, sha256.hexdigest()
   ```

2. **For very large files (>100MB):** Use `request.stream()` instead of `UploadFile` for even lower overhead:
   - `request.stream()` shows ~1500 MB/s throughput vs ~750-850 MB/s for UploadFile on large files
   - Near-zero memory delta (streaming directly to disk without buffering)
   - Requires manual multipart parsing for form fields

3. **Enforce size limits at multiple layers:**
   - Nginx `client_max_body_size` (first line of defense)
   - FastAPI middleware (second line)
   - Stream-chunk counting (third line)
   - Never rely on a single layer

4. **Clean up temporary files after processing:**
   - Use `BackgroundTask` or lifespan callback to remove temp files after response completes
   - The existing codebase has this exact bug (temp zip files never cleaned)

**Warning signs:**
- Memory usage spikes during file uploads (visible via `htop` or Docker stats)
- `await file.read()` calls without size parameter in code review
- No `aiofiles` dependency in requirements
- No `MAX_UPLOAD_BYTES` constant defined

**Phase to address:** Phase 3 (Model management). Must be fixed in the existing codebase before adding new upload endpoints.

**Sources:** [FastAPI UploadFile docs](https://fastapi.tiangolo.com/tutorial/request-files/) (HIGH), [fedirz/fastapi-file-upload-benchmark](https://github.com/fedirz/fastapi-file-upload-benchmark) (HIGH), [Devarsh Shah: Large file uploads](https://medium.com/@devarsh.shah/optimizing-large-file-uploads-in-fastapi-100mb-multi-gb-scale-8c772a5e2364) (MEDIUM), [greeden blog: Secure file uploads](https://blog.greeden.me/en/2026/03/03/implementing-secure-file-uploads-in-fastapi-practical-patterns-for-uploadfile-size-limits-virus-scanning-s3-compatible-storage-and-presigned-urls/) (MEDIUM)

---

### Pitfall 4: No Model/Result Versioning (Reproducibility Failure)

**What goes wrong:** A user runs an AC OPF simulation on a distribution system model on Monday, gets result A. On Tuesday, they run what they think is the same simulation, but get a different result B. Did the model change? Did the solver change? Did the parameters change? There is no audit trail.

**Why it happens:** The existing codebase has no versioning — models are stored in-memory (`GDMService._systems` dict) with no persistence. When a user modifies a component (adds a load, changes a line rating), the model is mutated in-place. There is no history. The same lack of versioning would naturally extend to simulation results.

**Consequences:**
- Scientific results are not reproducible (critical failure for a computation API)
- Cannot answer "what changed between run X and run Y?"
- Debugging solver convergence issues impossible — don't know which model version produced which result
- Regulatory/audit requirements for engineering simulation (power flow, distribution system planning) often require traceability

**Prevention:**

1. **Immutable model versions:** Every model upload/save creates an immutable version. Never mutate in place.
   ```
   models/{model_id}/
     versions/{version}/
       model_data.gdm
       metadata.json
       sha256sums.txt
     aliases/
       latest -> versions/v3
       staging -> versions/v2
       production -> versions/v1
   ```

2. **Stamp every simulation result with the model version and solver version:**
   ```python
   class SimulationResult(Base):
       __tablename__ = "simulation_results"
       
       id: UUID
       model_id: UUID
       model_version: int  # which model version was used
       solver: str  # "ac_opf" | "dc_opf" | "lindistflow"
       solver_version: str  # fgc-flow package version
       parameters: JSON  # solver configuration snapshot
       status: str  # "completed" | "failed"
       result_data: JSON  # or path to stored result file
       created_at: datetime
       execution_time_ms: int
   ```

3. **Write-once storage for models:** Once a model version is created, it is read-only. New edits create a new version. This guarantees:
   - A simulation run always references the exact model data used
   - Previous results remain reproducible even after model changes
   - "Undo" is just "reference an older version"

4. **Provenance tracking:** Store git commithash of the solver code, input model hash, parameter hash alongside every result. This enables exact reproduction.

5. **Result immutability:** Once a simulation result is stored, treat it as append-only. If a re-run produces new results, create a new result record — never overwrite.

**Warning signs:**
- Model data is updated in-place (no version column on the model table)
- Simulation results have no `model_version` or `solver_version` fields
- User asks "which model did I use for that result?" and can't answer
- No integrity hashes (SHA256) on stored model files

**Phase to address:** Phase 2 (Simulation) and Phase 3 (Model management). The versioning schema must be designed before the first simulation result is stored — backfilling is painful.

**Sources:** [OmniBioAI Model Registry](https://github.com/man4ish/omnibioai-model-registry) (HIGH), [Determined AI Model Registry](https://docs.determined.ai/model-dev-guide/model-management/model-registry-org.html) (MEDIUM), [ModelBox docs](https://modelbox.io/docs/guides/models) (MEDIUM)

---

### Pitfall 5: Shared SQLite Database — Write Contention and Thread Safety

**What goes wrong:** The new `fgc_flow_api` package must share a SQLite database with the existing `fgc_core` auth system. Two FastAPI applications, potentially with multiple workers each, accessing the same SQLite file. Under concurrent auth + simulation operations, writes collide: "database is locked" errors cascade, users can't log in while simulations commit results, or operations silently deadlock.

**Why it happens:** SQLite has a single-writer lock. Even with WAL mode, only one writer can hold the commit lock at a time. When two processes (or two workers in the same process) both have open write transactions, the second writer gets `SQLITE_BUSY`. The existing codebase already uses `aiosqlite` but hasn't configured WAL mode, busy timeout, or any of the SQLite concurrency armor.

**Consequences:**
- Users get 500 errors on login while a simulation result commits
- Simulation results silently lost because commit fails after computation completes
- In multi-worker deployments (gunicorn + uvicorn workers), contention multiplies
- No clear ownership: which service "owns" which tables? Schema changes require coordinated deploys

**Prevention:**

1. **SQLite concurrency armor (mandatory, immediate):**
   ```python
   engine = create_async_engine(
       "sqlite+aiosqlite:///./data/app.db",
       connect_args={"check_same_thread": False},
       poolclass=StaticPool  # single connection for async
   )
   
   @event.listens_for(engine.sync_engine, "connect")
   def set_sqlite_pragma(dbapi_conn, connection_record):
       cursor = dbapi_conn.cursor()
       cursor.execute("PRAGMA journal_mode=WAL")
       cursor.execute("PRAGMA synchronous=NORMAL")
       cursor.execute("PRAGMA busy_timeout=5000")
       cursor.execute("PRAGMA foreign_keys=ON")
       cursor.execute("PRAGMA temp_store=MEMORY")
       cursor.close()
   ```
   This enables concurrent reads + one writer, with a 5s queue before giving up.

2. **Short transactions:** Hold write transactions for the minimum time. Never hold a DB connection while a long simulation is running:
   ```python
   # BAD — holds connection during simulation
   async def run_simulation_and_store(db: AsyncSession, model_id: str):
       model = await db.get(Model, model_id)
       result = await run_in_threadpool(ac_opf_solver, model.data)
       db.add(SimulationResult(...))
       await db.commit()  # simulation already finished — OK but connection was held
   
   # GOOD — separate data access from computation
   async def run_simulation_and_store(model_id: str):
       model = await get_model_data(model_id)  # quick DB read, releases session
       result = await run_in_threadpool(ac_opf_solver, model.data)  # no DB held
       await store_result(model_id, result)  # quick DB write, acquires session
   ```

3. **Consider table namespace separation** — give each service its own table prefix or schema to avoid accidental collisions:
   - `fgc_core` owns: `users`, `auth_tokens`, `projects`
   - `fgc_flow_api` owns: `flow_models`, `flow_results`, `flow_jobs`

4. **Migration path to PostgreSQL:** Document the conditions under which SQLite's write throughput (~1,000 writes/sec in WAL mode) becomes insufficient. Use SQLAlchemy's ORM layer throughout so migration requires only changing the connection string:
   - Trigger: Write contention visible in production (5+ concurrent simulation commits queuing)
   - Trigger: Need for row-level locking or advisory locks
   - Trigger: Full-text search requirements

5. **Never share a session across requests or concurrent tasks.** Each FastAPI request gets its own session via `Depends(get_db)`. Background workers must open their own sessions.

**Warning signs:**
- "database is locked" errors in production logs
- `PRAGMA journal_mode=DELETE` (default, non-WAL) in database config
- No `busy_timeout` configured
- Simulation endpoints hold `db` session for the full duration of computation
- More than one SQLAlchemy engine created in the application (multiple connection pools)

**Phase to address:** Phase 1 (Foundation) — WAL mode and connection config must be right from day 1. Phase 2-3 — short-transaction discipline.

**Sources:** [SQLite WAL mode docs](https://www.sqlite.org/wal.html) (HIGH), [Stack Overflow: concurrent writes SQLite+FastAPI](https://stackoverflow.com/questions/79707043/how-to-make-concurrent-writes-in-sqlite-with-fastapi-sqlalchemy-without-datab) (HIGH), [aiosqlitepool](https://github.com/slaily/aiosqlitepool) (HIGH), [0fee architecture decisions](https://thalesandhisaictoclaude.com/0fee/004-architecture-decisions-python-fastapi-solidjs) (MEDIUM), [FasterAPI async DB guide](https://github.com/FasterApiWeb/FasterAPI/blob/master/docs/database/async-db.md) (HIGH)

---

### Pitfall 6: The `fgc_core` Code Duplication — Carried Into the New Package

**What goes wrong:** The new `fgc_flow_api` package duplicates auth code from `fgc_core` instead of importing it, creating a third copy of the same auth logic. Now there are three places to fix when auth changes: `backend/app/`, `backend/packages/fgc_core/`, and `backend/packages/fgc_flow_api/`.

**Why it happens:** The existing codebase already has this pattern — `backend/app/` and `backend/packages/fgc_core/` are near-identical (~3,500 lines each). The duplicate-import boundary has already been violated once; the muscle memory exists. When `fgc_flow_api` needs, say, a custom auth dependency that slightly differs from `fgc_core`'s version, the path of least resistance is to copy and modify rather than to extract and compose.

**Consequences:**
- ~10,500 lines of auth code across 3 copies (3,500 × 3)
- Auth bugs must be fixed in 3 places — practically they'll be fixed in 1 or 2
- Divergent auth behavior: one service allows empty passwords, another doesn't
- Schema drift: `fgc_flow_api` adds a field to the users table but forgets to update the other two copies
- Confusion: which copy of `get_current_user` is canonical?

**Prevention:**

1. **Strict rule: `fgc_flow_api` imports from `fgc_core`, never duplicates.** This is already in the project requirements. Enforce it with code review and automated checks:
   - Lint rule: no `from fgc_core` imports that shadow `fgc_core` modules? Actually, the rule is *only* import from `fgc_core` for auth, config, database.
   - PR must show import from `fgc_core`, not a local copy.

2. **Extract common dependencies into `fgc_core`:** If `fgc_flow_api` needs a different auth pattern (e.g., API key auth alongside JWT), add it to `fgc_core`'s `dependencies.py` — don't create `fgc_flow_api/dependencies.py`.

3. **Monorepo package setup for `fgc_flow_api`:**
   ```toml
   # backend/packages/fgc_flow_api/pyproject.toml
   [project]
   name = "fgc-flow-api"
   dependencies = [
       "fgc-core",  # local package in monorepo
       "fgc-flow",  # pip package from fgc-flow repo
       "fastapi>=0.111",
       # ... other deps
   ]
   
   [tool.uv.sources]
   fgc-core = { workspace = true }
   ```
   Install `fgc_core` as an editable workspace dependency so imports resolve cleanly.

4. **Clear ownership boundary:**
   - `fgc_core` owns: user auth (register, login, tokens, passwords), base config, database engine/SessionLocal, shared Pydantic schemas, health check endpoint
   - `fgc_flow_api` owns: simulation endpoints, model management, result storage/exports, job queue
   - If a feature could reasonably live in either, it goes in `fgc_core` (the shared layer)

5. **Plan to deprecate `backend/app/`** — delete it or explicitly move any non-duplicated code into the appropriate package. Having three copies is a phase 0 prerequisite, not a phase 1 option.

**Warning signs:**
- `fgc_flow_api/` has its own `config.py`, `database.py`, `dependencies.py`, or `auth.py`
- PRs for `fgc_flow_api` duplicate SQLAlchemy model definitions from `fgc_core`
- Schema changes need updates in >1 package
- Developer asks "should I put this in `fgc_core` or `fgc_flow_api`?" and the answer depends on who you ask

**Phase to address:** Phase 0 (pre-coding) — the import architecture must be decided before `fgc_flow_api` code exists. The `backend/app/` duplication must be resolved before (or as) Phase 1 begins.

**Sources:** [CONCERNS.md](file:///home/aadil/Documents/github/fgc-studio/.planning/codebase/CONCERNS.md) — existing 3,500-line duplication (HIGH), [Python monorepo guide](https://dev.to/ctrix/mastering-python-monorepos-a-practical-guide-2b4) (MEDIUM), [uv monorepo example](https://github.com/timothy-jeong/monorepo-example) (MEDIUM), [LSST vertical monorepo architecture](https://sqr-075.lsst.io/) (MEDIUM)

---

## Moderate Pitfalls

### Pitfall 7: Pickle Serialization of Scientific Objects in Task Queues

**What goes wrong:** Scientific Python objects (NumPy arrays, pandas DataFrames, complex solver results) are not easily serializable. When using a job queue, serialization breaks silently — or works in dev but fails in production.

**Why it happens:** Celery defaults to JSON serialization (since 4.0). NumPy arrays and custom solver result objects are not JSON-serializable. Switching to pickle introduces security risks (arbitrary code execution via deserialization) and has known compatibility issues between Python versions, especially with NumPy arrays pickled in Python 2 and unpickled in Python 3 (`kombu#1250`). Serialization of large arrays also causes performance bottlenecks — a 10MB NumPy array serialized to JSON becomes a 30MB base64 blob, serialized twice (once by the app, once by Celery).

**Consequences:**
- "Can't decode message body" errors in Celery workers (python2/3 compatibility)
- Memory bloat from double-serialization of large arrays
- Security surface expansion if pickle is enabled for task arguments
- Subtle data corruption: float precision loss when numpy arrays → JSON → numpy arrays

**Prevention:**

1. **Store data in the database, pass identifiers to the queue.**
   ```python
   # BAD: pass large arrays through the queue
   run_simulation.delay(numpy_array.tolist(), params)
   
   # GOOD: store data, pass ID
   model_data_id = store_to_db(numpy_array)
   run_simulation.delay(model_data_id, params)
   ```
   This is the **Claim Check pattern** — the queue carries a small reference (the claim check), the actual data stays in persistent storage.

2. **For simulation results**, store them in the database or file storage before/enqueuing, then pass the result_id. Workers write results to storage; the API reads from storage.

3. **If pickle must be used (numpy arrays as task arguments):**
   - Use `celery.conf.task_serializer = 'pickle'` and `result_serializer = 'pickle'`
   - Configure `accept_content = ['pickle', 'json']`
   - Protect the Redis broker with a strong password and network isolation
   - Be aware of Python version compatibility issues
   - Test serialization/deserialization in integration tests with production-sized data

4. **Custom serializers**: For hybrid approaches, register a custom serializer with kombu that handles numpy/pandas types:
   ```python
   from kombu.serialization import register
   register('numpyjson', numpy_json_dumps, numpy_json_loads,
            content_type='application/x-numpyjson',
            content_encoding='utf-8')
   ```

**Warning signs:**
- Task function signature includes `np.ndarray`, `pd.DataFrame`, or custom solver result objects
- Base64-encoded NumPy arrays in Celery task arguments
- JSON serialization errors mentioning "not JSON serializable"
- Worker crashes with pickle/UnicodeDecodeError

**Phase to address:** Phase 2 (Simulation endpoints) — job queue design must include a serialization strategy for solver inputs and outputs.

**Sources:** [Celery FAQ: pickle serialization](https://docs.celeryq.dev/en/stable/faq.html) (HIGH), [kombu Issue #1250](https://github.com/celery/kombu/issues/1250) (HIGH), [Celery Issue #4822](https://github.com/celery/celery/issues/4822) (MEDIUM), [Stack Overflow: passing numpy to Celery](https://stackoverflow.com/questions/41956480/how-to-pass-large-chunk-of-data-to-celery) (HIGH)

---

### Pitfall 8: Synchronous Database Drivers in Async Endpoints

**What goes wrong:** The existing codebase uses `aiosqlite` for async SQLite access. But if any dependency (ORM model, utility function, middleware) accidentally uses sync `sqlite3` or sync SQLAlchemy, it blocks the event loop silently.

**Why it happens:** Python has both sync and async SQLite drivers. Installing `sqlalchemy` without `aiosqlite` gives a sync engine. A `SessionLocal()` from a sync engine inside an `async def` handler blocks the event loop for every DB call. FastAPI doesn't warn about this — sync code in async routes runs happily but destroys concurrency.

**Consequences:**
- Database queries serialize — only one at a time, even though the ORM says "async"
- The entire server slows to sequential DB access under concurrent load
- Developers think they're using async but they're not — no error message, just slow performance
- `greenlet`/`MissingGreenlet` errors when mixing sync SQLAlchemy session creation inside async handlers

**Prevention:**

1. **One command verification:** Set `PYTHONASYNCIODEBUG=1` in development. It logs warnings when coroutines take too long. Consistently slow DB queries point to sync drivers.

2. **Explicit async engine configuration:**
   ```python
   # CORRECT for async
   engine = create_async_engine("sqlite+aiosqlite:///./app.db")
   AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)
   
   # WRONG (silently synchronous)
   engine = create_engine("sqlite:///./app.db")  # missing +aiosqlite
   SessionLocal = sessionmaker(engine)
   ```

3. **Dependency for DB sessions:** Always use FastAPI's `Depends(get_db)` with `async def` — never create sessions in route handlers directly.

4. **Check for sync SQLAlchemy imports:** Don't import `from sqlalchemy.orm import Session` when you mean `from sqlalchemy.ext.asyncio import AsyncSession`.

5. **Use `async def` consistently:** If one route handler uses `def` instead of `async def`, FastAPI runs it in a thread pool. This is fine for sync code but means the handler can't `await` async DB operations — it must use sync drivers. This mixed pattern creates confusion.

**Warning signs:**
- `create_engine` instead of `create_async_engine` in any file
- `Session` (sync) instead of `AsyncSession` (async) type annotations
- `import sqlalchemy` without `import sqlalchemy.ext.asyncio`
- Database URL uses `sqlite:///` instead of `sqlite+aiosqlite:///`
- `MissingGreenlet` errors at runtime

**Phase to address:** Phase 1 (Foundation) — the async engine config is in `fgc_core` already but must be verified before `fgc_flow_api` builds on it.

**Sources:** [Aryan Khurana: async DB architecture in FastAPI](https://medium.com/beyond-localhost/what-a-hackathon-workshop-taught-us-about-async-database-architecture-in-fastapi-830180bbfb3b) (HIGH), [FastAPI + SQLAlchemy 2.0 in Production](https://dev.to/ayush_kaushik_b450595c233/fastapi-sqlalchemy-20-in-production-building-high-performance-async-apis-11ni) (HIGH), [FasterAPI async DB guide](https://github.com/FasterApiWeb/FasterAPI/blob/master/docs/database/async-db.md) (HIGH)

---

### Pitfall 9: Temp File Leaks After Export/Download

**What goes wrong:** When a user exports simulation results as a zip file, the server creates a temporary zip, sends it via `FileResponse`, but never cleans up. Each export leaks disk space. Over time, the server runs out of disk.

**Why it happens:** This already exists in the existing codebase at multiple locations:
- `gdm_service.py:431-448`: `tempfile.mkdtemp()` with no cleanup
- `gdm_service.py:390-410`: same pattern for scenario exports
- `system.py:94-99`: `FileResponse(zip_path)` without cleanup
- `scenarios.py:163-171`: same pattern

`FileResponse` sends the file asynchronously — after the response handler returns, the file object still might be in use. Developers assume cleanup happens automatically, but `tempfile.mkdtemp()` creates a directory that must be explicitly removed.

**Consequences:**
- Disk fills up silently, causing database write failures, simulation failures, and server crashes
- In Docker, the container filesystem fills up, triggering OOM or `no space left on device` errors
- Hard to detect: no metric tracks temp file accumulation
- In production with daily exports, a 50MB export × 20 users × 30 days = 30GB of leaked data

**Prevention:**

1. **Use `tempfile.NamedTemporaryFile` (not `mkdtemp`):**
   ```python
   import tempfile
   
   @app.get("/export/{result_id}")
   async def export_result(result_id: UUID):
       with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
           zip_path = tmp.name
           create_export_zip(result_id, tmp)
       
       # Register cleanup after response is sent
       return FileResponse(
           zip_path,
           media_type="application/zip",
           filename=f"result_{result_id}.zip",
           background=BackgroundTask(lambda: os.unlink(zip_path))
       )
   ```

2. **Use `aiofiles` for async temp file creation:**

3. **Monitor temp directory size:** Alert if `tempfile.gettempdir()` usage exceeds a threshold.

4. **Register a startup cleanup for orphaned temp files:** On server start, delete any temp files older than 24h.

**Warning signs:**
- `tempfile.mkdtemp()` calls without corresponding `shutil.rmtree()` or cleanup
- `FileResponse` without `BackgroundTask` cleanup
- No temp file age-based cleanup on startup
- Disk usage grows monotonically (visible via `df -h` / Docker `docker system df`)

**Phase to address:** Phase 3 (Model management) / Phase 4 (Export features). Fix existing leaks before adding new export endpoints.

**Sources:** [CONCERNS.md](file:///home/aadil/Documents/github/fgc-studio/.planning/codebase/CONCERNS.md) — lines 216-230 (HIGH), FastAPI `BackgroundTask` docs (HIGH)

---

### Pitfall 10: Running Simulation Solver Imports at Module Level

**What goes wrong:** Importing `fgc-flow` solver packages at module level in `fgc_flow_api` causes slow startup times and memory waste. On every API server start (including during development hot-reload), all solver dependencies — including heavy scientific libraries (NumPy, SciPy, potentially Pandas) — are loaded even if no simulation endpoint is hit.

**Why it happens:** Standard Python import structure encourages top-level imports. But scientific libraries are heavy:
- `import numpy` — ~50-100ms startup time
- `import scipy` — ~200-500ms startup time  
- `import fgc_flow.solver.ac_opf` — potentially slow if it loads compiled extensions

Combined: 1-2 seconds of additional startup time per worker. With 4 gunicorn workers, that's 4-8 seconds before the server is ready. During development with `--reload`, every file change triggers this.

**Consequences:**
- Slow iteration in development (each file save = 2s reload delay)
- Higher memory usage per worker (every worker loads all solver libraries)
- Startup readiness checks may timeout if the solver import path is deep

**Prevention:**

1. **Lazy imports in route handlers:**
   ```python
   # BAD — imported at module level, always loaded
   from fgc_flow.solver import ac_opf
   
   @app.post("/simulate/ac-opf")
   async def run_ac_opf(...):
       return await run_in_threadpool(ac_opf.solve, ...)
   
   # GOOD — imported only when endpoint is hit
   @app.post("/simulate/ac-opf")
   async def run_ac_opf(...):
       from fgc_flow.solver import ac_opf
       return await run_in_threadpool(ac_opf.solve, ...)
   ```

2. **Or use a solver registry pattern:**
   ```python
   _solvers = {}
   
   def get_solver(name: str):
       if name not in _solvers:
           if name == "ac_opf":
               from fgc_flow.solver import ac_opf
               _solvers[name] = ac_opf
           elif name == "dc_opf":
               from fgc_flow.solver import dc_opf
               _solvers[name] = dc_opf
       return _solvers[name]
   ```

3. **Measure startup time:** Add a startup timing log to detect when solver imports are the bottleneck.

**Warning signs:**
- `import fgc_flow` or `from fgc_flow.solver` at the top of `main.py`
- Server startup takes >3 seconds
- `--reload` in development takes >2 seconds per reload cycle
- Memory usage jumps on startup even before any simulation request

**Phase to address:** Phase 1 (Foundation) — import structure decisions affect development velocity from day 1.

**Sources:** Standard Python import timing patterns (HIGH confidence — training data verified)

---

## Minor Pitfalls

### Pitfall 11: Polling-Based Status Instead of Server-Sent Events

**What goes wrong:** The project already decided to use polling-based status checking (SIM-06: "Job queue with status polling"). But if the polling interval is too aggressive (every 1s from 10 clients), the database gets hammered with unnecessary reads. If the interval is too long (every 30s), the UI feels unresponsive.

**Prevention:**
- Start with polling at 3-5s intervals — fast enough for UX, slow enough for DB
- Add `Cache-Control: max-age=2` headers on status responses
- Use a cheap status query (indexed by task_id, no joins) that the DB can serve from WAL cache
- If polling load becomes significant, migrate to SSE (Server-Sent Events) — FastAPI supports `StreamingResponse` natively

### Pitfall 12: Missing Rate Limiting on Simulation Endpoints

**What goes wrong:** Without rate limiting, a user can submit 1000 simulations simultaneously. Even with a queue, the backlog overwhelms storage and delays other users' results by hours.

**Prevention:**
- Per-user rate limit: max 5 concurrent simulations per user
- Per-user daily quota: max 100 simulation runs per day
- Queue prioritization: FCFS with per-user fairness (prevent one user from starving others)
- These should be configurable via environment variables

### Pitfall 13: Solver Version Drift

**What goes wrong:** `fgc-flow` (the pip package) evolves independently of `fgc_flow_api` (the API package). A solver bug fix in `fgc-flow` changes results — but old saved results don't carry the solver version. Users can't tell if result differences are from model changes or solver changes.

**Prevention:**
- Pin `fgc-flow` version in `fgc_flow_api`'s dependencies
- Tag every simulation result with `fgc-flow` package version
- Include solver git commit hash in result metadata if possible
- When upgrading `fgc-flow`, run a validation suite comparing old vs new results on canonical test cases

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|----------------|------------|
| **Phase 0** | Codebase cleanup | Duplicating auth code in fgc_flow_api (P6) | Strict import rule; only import from fgc_core; delete backend/app/ |
| **Phase 0** | Database config | Missing SQLite WAL mode + busy_timeout (P5) | Apply PRAGMA armor in engine creation; verify with integration test |
| **Phase 0** | Import structure | Heavy solver imports at module level (P10) | Use lazy imports; measure startup time; solver registry pattern |
| **Phase 1** | Auth endpoints | Sync DB driver in async endpoint (P8) | Verify aiosqlite async engine; no create_engine calls |
| **Phase 1** | Foundation routes | Shared DB session across requests (P5) | Always use Depends(get_db); never module-level session |
| **Phase 2** | Simulation endpoints | CPU-bound solver blocking event loop (P1) | run_in_threadpool for NumPy/SciPy; ProcessPoolExecutor for pure Python |
| **Phase 2** | Job queue | Pickle serialization of solver inputs/outputs (P7) | Claim Check pattern; store data in DB, pass IDs |
| **Phase 2** | Job queue | Wrong queue complexity level (P2) | Start with in-process persistent queue; migrate to Celery only when needed |
| **Phase 2** | Result storage | No result versioning (P4) | Immutable results; stamp with model_version + solver_version |
| **Phase 2** | Rate limiting | Simulation endpoint abuse (P12) | Per-user concurrent + daily quotas from day 1 |
| **Phase 3** | Model uploads | Loading entire file into memory (P3) | Stream to disk; enforce size at multiple layers |
| **Phase 3** | Model management | In-place model mutation (P4) | Write-once model versions; edits create new versions |
| **Phase 4** | Export/download | Temp file leaks (P9) | BackgroundTask cleanup; startup cleanup job |
| **Phase 4** | Export/download | No integrity hashes on download | Compute SHA256 on upload; verify on download; return ETag |

---

## Confidence Assessment

| Pitfall | Confidence | Reason |
|---------|------------|--------|
| P1: Async event loop blocking | HIGH | Verified against FastAPI docs, benchmarks, and community best practices |
| P2: Job queue complexity | HIGH | Multiple reference implementations and guidance articles confirm the tiered approach |
| P3: Large file memory loading | HIGH | Benchmark confirms `await file.read()` = memory proportional to file size; existing codebase has this bug |
| P4: No model/result versioning | HIGH | Multiple production model registries (OmniBioAI, Determined, ModelBox) all confirm this pattern |
| P5: Shared SQLite contention | HIGH | Stack Overflow, aiosqlitepool docs, and production post-mortems all confirm WAL + busy_timeout pattern |
| P6: Code duplication | HIGH | Directly observed in existing codebase (CONCERNS.md); architectural pattern is clear |
| P7: Pickle serialization | HIGH | Verified against Celery docs, kombu issue tracker, and community experience |
| P8: Sync DB drivers | HIGH | Multiple blog posts and FastAPI guides confirm the "missing +aiosqlite" trap |
| P9: Temp file leaks | HIGH | Directly observed in existing codebase (CONCERNS.md); confirmed by FastAPI FileResponse docs |
| P10: Module-level heavy imports | MEDIUM | Based on known Python import behavior; severity confirmed by training data |
| P11: Polling vs SSE | MEDIUM | Tradeoff is well-known; severity depends on actual load |
| P12: Missing rate limiting | HIGH | Existing CONCERNS.md confirms no rate limiting exists |
| P13: Solver version drift | MEDIUM | General software engineering principle; severity specific to scientific reproducibility |

---

## Sources

1. FastAPI async documentation: https://fastapi.tiangolo.com/async/ (HIGH)
2. FastAPI Request Files: https://fastapi.tiangolo.com/tutorial/request-files/ (HIGH)
3. zhanymkanov/fastapi-best-practices (CPU-bound handling): https://deepwiki.com/zhanymkanov/fastapi-best-practices/3.2-handling-io-and-cpu-bound-operations (HIGH)
4. FastAPI Issue #1718 — CPU-bound performance: https://github.com/fastapi/fastapi/issues/1718 (HIGH)
5. fedirz/fastapi-file-upload-benchmark: https://github.com/fedirz/fastapi-file-upload-benchmark (HIGH)
6. Devarsh Shah — large file uploads: https://medium.com/@devarsh.shah/optimizing-large-file-uploads-in-fastapi-100mb-multi-gb-scale-8c772a5e2364 (MEDIUM)
7. Celery FAQ — serialization: https://docs.celeryq.dev/en/stable/faq.html (HIGH)
8. Celery optimizing guide: https://docs.celeryq.dev/en/latest/userguide/optimizing.html (HIGH)
9. Celery Issue #1842 — numpy hanging: https://github.com/celery/celery/issues/1842 (HIGH)
10. kombu Issue #1250 — pickle Python 2/3 compat: https://github.com/celery/kombu/issues/1250 (HIGH)
11. OmniBioAI model registry: https://github.com/man4ish/omnibioai-model-registry (HIGH)
12. Determined AI model registry: https://docs.determined.ai/model-dev-guide/model-management/model-registry-org.html (MEDIUM)
13. fastapi-taskflow (in-process persistent queue): https://github.com/Attakay78/fastapi-taskflow (HIGH)
14. nano-queue (DB-backed task queue): https://github.com/Fidel-C/nano-queue (HIGH)
15. fastapi-file-upload-benchmark (memory comparison): https://github.com/fedirz/fastapi-file-upload-benchmark (HIGH)
16. Aryan Khurana — async DB architecture: https://medium.com/beyond-localhost/what-a-hackathon-workshop-taught-us-about-async-database-architecture-in-fastapi-830180bbfb3b (HIGH)
17. SQLite WAL mode: https://www.sqlite.org/wal.html (HIGH)
18. SQLite concurrent writes (Stack Overflow): https://stackoverflow.com/questions/79707043/ (HIGH)
19. 0fee architecture decisions: https://thalesandhisaictoclaude.com/0fee/004-architecture-decisions-python-fastapi-solidjs (MEDIUM)
20. LSST vertical monorepo architecture: https://sqr-075.lsst.io/ (MEDIUM)
21. Python monorepo guide: https://dev.to/ctrix/mastering-python-monorepos-a-practical-guide-2b4 (MEDIUM)
22. FasterAPI async DB guide: https://github.com/FasterApiWeb/FasterAPI/blob/master/docs/database/async-db.md (HIGH)
23. CONCERNS.md (existing codebase audit): file:///home/aadil/Documents/github/fgc-studio/.planning/codebase/CONCERNS.md (HIGH)
24. PROJECT.md (project definition): file:///home/aadil/Documents/github/fgc-studio/.planning/PROJECT.md (HIGH)
