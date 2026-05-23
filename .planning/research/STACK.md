# Technology Stack

**Project:** FGC Flow API
**Researched:** 2026-05-22

## Status Legend
- ✅ **Recommended** — Use this; has clear advantages over alternatives
- ⚠️ **Conditional** — Use only under specific circumstances
- ❌ **Not recommended** — Actively avoid for this project

---

## Core Framework (Already Decided)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **FastAPI** | ≥0.115 | Web framework | Async-native, auto OpenAPI, Pydantic v2 integration, high performance |
| **SQLAlchemy** | ≥2.0 (async) | ORM / database | Existing in fgc_core; async sessions, modern 2.0 style |
| **aiosqlite** | ≥0.20 | Async SQLite driver | Existing in fgc_core; needed for SQLAlchemy async with SQLite |
| **Pydantic** | ≥2.0 | Validation / schemas | Built into FastAPI; v2 is significantly faster than v1 |
| **bcrypt** | ≥4.1 | Password hashing | Existing in fgc_core; standard for Python password hashing |
| **python-jose** | ≥3.3 | JWT tokens | Existing in fgc_core; access + refresh token support |

**Verdict:** No changes needed. These are locked in by fgc_core compatibility.

---

## Job Queue / Async Task Management

### ✅ Recommended: DB-Backed Task Queue (v1 — Use SQLAlchemy Directly)

**What:** A `Job` model in the existing SQLite database with status tracking, results storage, and a lightweight background worker that polls for pending jobs.

**Why this over Celery / ARQ / Taskiq / Dramatiq for v1:**

| Factor | DB-Backed (recommended) | Celery | ARQ | Taskiq |
|--------|------------------------|--------|-----|--------|
| New infrastructure needed | **None** | Redis + broker | Redis | Redis (or broker) |
| Worker process needed | No (in-process) | Yes | Yes | Yes |
| Complicates dev setup | **No** | Yes (Redis) | Yes (Redis) | Yes (Redis) |
| Persistence | ACID (SQLite) | Configurable | Configurable | Broker-dependant |
| Async-native | ✅ Yes | ❌ No (workarounds) | ✅ Yes | ✅ Yes |
| Complex workflows | ❌ No | ✅ Yes | ❌ No | ⚠️ Partial |
| Maintenance status | N/A | ✅ Mature | ⚠️ Maintenance mode (#510) | ✅ Active (v0.12.3, May 2026) |
| Learning curve | Trivial | High | Low | Medium |

**Implementation pattern:**

```python
# models/job.py
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum, Float
from sqlalchemy.dialects.sqlite import JSON

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class Job(Base):
    __tablename__ = "simulation_jobs"
    
    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False)  # "ac_opf", "dc_opf", "lindistflow"
    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING, index=True)
    params = Column(JSON, nullable=False)       # solver parameters
    result = Column(JSON, nullable=True)         # serialized result
    error = Column(Text, nullable=True)          # error traceback
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
```

```python
# job_runner.py — Background worker in lifespan
import asyncio
from sqlalchemy import select, update
from fgc_flow_api.models.job import Job, JobStatus

async def poll_jobs(app_state):
    """Background coroutine: polls for PENDING jobs and executes them."""
    while True:
        async with app_state.db_session() as session:
            result = await session.execute(
                select(Job).where(Job.status == JobStatus.PENDING)
                .order_by(Job.created_at)
                .limit(1)
            )
            job = result.scalar_one_or_none()
            if job:
                await _execute_job(session, job)
        await asyncio.sleep(2)  # poll interval
```

**When to upgrade to a proper task queue:**
- You need multiple worker processes across different machines
- Job throughput exceeds ~50 concurrent jobs
- You need scheduled/cron jobs (periodic cleanup, report generation)
- The team wants dedicated worker processes for operational isolation

### ⚠️ Upgrade Path: Taskiq + Redis

**When you outgrow the DB-backed approach:**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Taskiq** | ^0.12 | Async task queue | Actively maintained, asyncio-native, FastAPI integration (`taskiq-fastapi`) |
| **redis-py** | ^5.0 | Redis client | Required by Taskiq's Redis broker |

**Why not ARQ:** ARQ is in maintenance-only mode (samuelcolvin/arq#510, as of Feb 2026). Taskiq has similar simplicity but active development, FastAPI dependency injection support, and multiple broker backends.

**Why not Celery:** Synchronous architecture fights FastAPI's async model. Requires significant setup (broker, result backend, Flower monitoring). Only justified for complex task DAGs (chains, chords) which this project doesn't need.

### ❌ Avoid

| Library | Reason |
|---------|--------|
| **Celery** | Overkill; sync/async impedance mismatch; ops complexity |
| **RQ** | Sync-only; not asyncio-native; uses `fork()` which has issues |
| **Dramatiq** | Great library but optimized for RabbitMQ; adds ops burden |
| **ARQ** | Maintenance mode — not a good foundation for new projects |
| **FlashQ** | Very new (March 2026, 9 stars); unproven |
| **nano-queue** | Thread-based (not async); single-process only |

---

## Result Caching

### ✅ Recommended: Parameter-Hash Result Caching (DB-Backed)

**What:** Store simulation results keyed by a deterministic hash of input parameters. Cache hit = skip re-execution.

**Why:** Power flow simulations are deterministic for the same inputs. If a user submits the exact same model + solver params, they should get instant results from cache.

**Implementation:**

```python
# models/result_cache.py
import hashlib, json
from sqlalchemy import Column, String, Text, DateTime, LargeBinary

class CachedResult(Base):
    __tablename__ = "simulation_cache"
    
    input_hash = Column(String(64), primary_key=True)  # SHA-256
    job_type = Column(String(50), nullable=False, index=True)
    params = Column(Text, nullable=False)               # JSON for inspection
    result = Column(LargeBinary, nullable=False)         # Pickled / msgpack result
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @staticmethod
    def make_hash(job_type: str, params: dict) -> str:
        """Deterministic hash across all input parameters."""
        normalized = json.dumps(params, sort_keys=True, default=str)
        raw = f"{job_type}:{normalized}"
        return hashlib.sha256(raw.encode()).hexdigest()
```

**Cache policy:** 
- Keep results **indefinitely** (power flow results are deterministic for given inputs)
- Invalidation: when the underlying model/GDM file changes (increment a model version counter)
- TTL is not appropriate here — the cache is content-addressed, not time-based

### ❌ Avoid

| Approach | Reason |
|---------|--------|
| **Redis** | Unnecessary for v1; adds ops dependency; DB cache is sufficient for this workload |
| **functools.lru_cache** | In-memory only; lost on restart; doesn't persist across API calls |
| **cashews / cachekit / yokedcache** | Overkill; designed for HTTP response caching, not simulation result caching |
| **`entropic` library** | Purpose-built for simulation caching but adds a dependency; the DB approach is simpler and more transparent |

---

## API Documentation

### ✅ Recommendation: Built-In FastAPI OpenAPI (Sufficient for v1)

FastAPI auto-generates OpenAPI 3.1 from Pydantic models. Use it well rather than adding third-party doc tools.

| Feature | What to do | Why |
|---------|-----------|-----|
| **Swagger UI** | Keep default at `/docs` | Interactive testing; familiar to all API consumers |
| **ReDoc** | Keep default at `/redoc` | Better for reading/reference; three-panel layout |
| **OpenAPI schema** | Export `/openapi.json` | Used for SDK generation, contract testing |
| **response_model** | Use on every endpoint | Locks response shape; enables auto-docs |
| **examples** | Add to Pydantic models | Makes Swagger UI "Try it out" useful immediately |
| **tags** | Group endpoints logically | `/docs` becomes navigable |
| **summary + description** | On every endpoint | Turns auto-docs into readable specification |

**Things to configure on the FastAPI app:**

```python
app = FastAPI(
    title="FGC Flow API",
    description="""
    REST API for power flow analysis. Run AC OPF, DC OPF, and LinDistFlow 
    simulations on distribution system models (GDM format).
    
    ## Authentication
    All simulation and model endpoints require a valid JWT token 
    obtained from the `/auth` endpoints.
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    # Security scheme auto-generated by OAuth2PasswordBearer
)
```

### ❌ Avoid

| Tool | Reason |
|------|--------|
| **Scalar** | Good but adds a dependency; built-in Swagger UI + ReDoc is sufficient for v1 |
| **Stoplight Elements** | Same as Scalar — unnecessary for v1 |
| **Separate OpenAPI YAML** | FastAPI generates from code; hand-maintained YAML drifts from implementation |
| **Spectal / Redocly CLI in CI** | Add in v2 if the API grows beyond 20 endpoints; not needed for initial launch |

---

## Testing

### ✅ Recommended Stack

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **pytest** | ≥8.0 | Test runner | De facto standard; auto-discovery; rich plugin ecosystem |
| **pytest-asyncio** | ≥0.24 | Async test support | Required to test async FastAPI endpoints and DB operations |
| **httpx** | ≥0.28 | HTTP client for tests | `AsyncClient` with ASGI transport tests the full stack without a server |
| **pytest-cov** | ≥5.0 | Coverage reporting | Track what's tested; enforce minimum coverage in CI |

**Implementation pattern:**

```python
# conftest.py
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from fgc_flow_api.main import app
from fgc_flow_api.db import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c
    
    app.dependency_overrides.clear()
```

**Types of tests to write:**

| Test type | What it covers | Tooling |
|-----------|---------------|---------|
| **Unit** | Solver logic, parameter validation, hash computation | pytest (no HTTP) |
| **API** | Endpoint contracts: status codes, response shapes, auth | `httpx.AsyncClient` + `pytest-asyncio` |
| **Integration** | Full flow: request → DB → response, job lifecycle | `httpx.AsyncClient` + overridden DB session |
| **Contract** | OpenAPI schema matches actual responses | Generate from `/openapi.json`, validate with `openapi-core` or snapshot tests |

### ❌ Avoid

| Tool | Reason |
|------|--------|
| **unittest** | Boilerplate-heavy; pytest is the modern standard in the FastAPI ecosystem |
| **TestClient (sync)** | Doesn't work in async tests; use `httpx.AsyncClient` with ASGI transport |
| **moto / responses** | For mocking external APIs; this project has no external HTTP calls |
| **locust** | Load testing; not needed for v1 |
| **tox** | Multi-version testing; adds complexity with marginal benefit for a single-package project |

---

## Authentication & Security

### ✅ Recommendation: Reuse fgc_core Auth (No Changes)

The fgc_core package already provides:
- `bcrypt` password hashing
- `python-jose` JWT (access + refresh tokens)
- `OAuth2PasswordBearer` dependency
- User database tables

**The fgc_flow_api package must NOT duplicate this.** Import auth dependencies from fgc_core.

```python
# Correct: import from fgc_core
from fgc_core.auth import get_current_user, create_access_token, oauth2_scheme

# WRONG: reimplement
# from bcrypt import hashpw  # NO
# from jose import jwt       # NO
```

---

## Recommended Development Dependencies

```toml
# pyproject.toml
[project]
name = "fgc-flow-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "pydantic>=2.0",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.20",
    "bcrypt>=4.1",
    "python-jose[cryptography]>=3.3",
    "fgc-flow",                              # power flow solvers
    "grid-data-models",                      # GDM (already in stack)
    "fgc-core",                              # existing auth/db (workspace dep)
]

[project.optional-dependencies]
# Taskiq integration (for when DB-backed queue needs upgrading)
taskiq = [
    "taskiq>=0.12",
    "taskiq-fastapi>=0.5",
    "redis>=5.0",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "httpx>=0.28",
]
```

---

## Complete Stack Overview

```
┌─────────────────────────────────────────────┐
│                  FastAPI                     │
│  Auto OpenAPI 3.1 / Swagger UI / ReDoc       │
├─────────────────────────────────────────────┤
│                                              │
│  fgc_flow_api (this package)                  │
│  ┌───────────────────────────────────────┐   │
│  │  Job Queue (SQLAlchemy Job model)      │   │
│  │  Result Cache (parameter-hash table)   │   │
│  │  Auth (imported from fgc_core)         │   │
│  │  Solver Dispatch (to fgc-flow)         │   │
│  └───────────────────────────────────────┘   │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│  fgc_core (shared package)                   │
│  ┌───────────────────────────────────────┐   │
│  │  Auth (bcrypt + JWT)                   │   │
│  │  Database (SQLAlchemy async + aiosqlite)│   │
│  │  Config (settings)                     │   │
│  └───────────────────────────────────────┘   │
│                                              │
│  fgc-flow (external pip package)              │
│  ┌───────────────────────────────────────┐   │
│  │  AC OPF Solver                        │   │
│  │  DC OPF Solver                        │   │
│  │  LinDistFlow Solver                    │   │
│  │  Model Export                          │   │
│  └───────────────────────────────────────┘   │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│  SQLite (single shared DB file)              │
│  ┌───────────────────────────────────────┐   │
│  │  users (from fgc_core)                │   │
│  │  models (GDM storage + versions)      │   │
│  │  simulation_jobs (queue)              │   │
│  │  simulation_cache (result cache)      │   │
│  └───────────────────────────────────────┘   │
│                                              │
└─────────────────────────────────────────────┘
```

---

## Key Rationale Summary

| Decision | Why |
|----------|-----|
| **DB-backed job queue, not Celery/ARQ/Taskiq** | Zero new infrastructure; SQLite is already in use; power flow workload is low-frequency (minutes between jobs) so a proper task queue provides negligible benefit over a polling loop |
| **Taskiq as upgrade path** | Only if/when you need Redis; actively maintained; asyncio-native; FastAPI DI integration |
| **DB-backed result cache, not Redis** | Content-addressed cache on deterministic inputs; no TTL needed; ACID guarantees |
| **Built-in API docs, not Scalar/Spectral** | Swagger UI + ReDoc shipped with FastAPI is complete for v1; add doc tooling when API grows beyond 20 endpoints |
| **httpx.AsyncClient for tests, not sync TestClient** | Async tests allow async DB assertions; same API as real HTTP calls |
| **No Celery, ever** | The project's workload (scientific computation, not web scraping/email) doesn't need task routing, chains, or Beat. The operational cost of Celery is not justified. |

---

## Sources

- **Context7 — FastAPI testing docs:** https://fastapi.tiangolo.com/tutorial/testing/ (HIGH confidence)
- **Context7 — FastAPI async testing:** https://fastapi.tiangolo.com/advanced/async-tests/ (HIGH confidence)
- **Context7 — FastAPI OpenAPI docs:** https://fastapi.tiangolo.com/reference/openapi/docs/ (HIGH confidence)
- **Taskiq GitHub (v0.12.3, May 2026):** https://github.com/taskiq-python/taskiq (MEDIUM confidence — actively maintained, 2.1K stars)
- **ARQ maintenance mode notice:** https://github.com/samuelcolvin/arq (HIGH confidence — repository states "maintenance only mode")
- **ARQ v0.28.0 release:** https://github.com/python-arq/arq/releases/tag/v0.28.0 (HIGH confidence)
- **FastAPI task queue comparison (KruN, Apr 2026):** https://krun.pro/fastapi-tasks-no-celery/ (MEDIUM confidence — agrees on ARQ for asyncio, Celery overkill)
- **Python task queue benchmarks (Steven Yue, 2024-2025):** https://stevenyue.com/blogs/exploring-python-task-queue-libraries-with-load-test (MEDIUM confidence — benchmarks show Taskiq fastest, ARQ middle)
- **Celery vs ARQ comparison (Leapcell, Sep 2025):** https://leapcell.io/blog/celery-versus-arq-choosing-the-right-task-queue-for-python-applications (MEDIUM confidence — aligns with recommendation)
- **SQLite-backed job queue article (DEV, May 2026):** https://dev.to/d_security/why-i-built-a-job-queue-with-sqlite-instead-of-redis-and-what-i-learned-4f05 (MEDIUM confidence — real-world experience confirms SQLite sufficient for low-throughput queues)
- **OpenAPI documentation guide (BytePane, Apr 2026):** https://bytepane.com/blog/openapi-swagger-guide/ (MEDIUM confidence — confirms Scalar as emerging but Swagger UI + ReDoc sufficient)
