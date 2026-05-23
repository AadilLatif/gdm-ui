<!-- refreshed: 2026-05-22 -->
# Architecture

**Analysis Date:** 2026-05-22

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3 SPA)                                │
│  ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐               │
│  │LoginView   │ │ModelLoader│ │Warehouse │ │NetworkView │               │
│  │RegisterView│ │View       │ │View      │ │ScenariosView│              │
│  └─────┬──────┘ └─────┬────┘ └─────┬────┘ └──────┬─────┘               │
│        │              │            │             │                      │
│        └──────────────┴──────┬─────┴─────────────┘                      │
│                              │                                          │
│                    ┌─────────▼─────────┐                                │
│                    │   Pinia Stores     │                                │
│                    │  (auth, project)   │                                │
│                    └─────────┬─────────┘                                │
│                              │                                          │
│                    ┌─────────▼─────────┐                                │
│                    │  API Client (Axios)│                                │
│                    │  + interceptor     │                                │
│                    └─────────┬─────────┘                                │
└──────────────────────────────┼──────────────────────────────────────────┘
                               │ HTTP (JSON)
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                                      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │  Router Layer  (controllers)                                  │       │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌────────┐  │       │
│  │  │auth  │ │users │ │proj- │ │equip-  │ │net-  │ │scen-   │  │       │
│  │  │      │ │      │ │ects  │ │ment    │ │work  │ │arios   │  │       │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └───┬────┘ └──┬───┘ └───┬────┘  │       │
│  │     │        │        │         │         │         │        │       │
│  │     └────────┴────────┴─────────┴─────────┴─────────┘        │       │
│  │                          │                                   │       │
│  │             ┌────────────▼────────────┐                      │       │
│  │             │  Dependencies Layer      │                      │       │
│  │             │  (auth guard, db session)│                      │       │
│  │             └────────────┬────────────┘                      │       │
│  └──────────────────────────┼───────────────────────────────────┘       │
│                             │                                           │
│  ┌──────────────────────────▼───────────────────────────────────┐       │
│  │  Service Layer                                                 │       │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐    │       │
│  │  │AuthService   │  │FileService   │  │GDMService (singleton)│    │       │
│  │  │(JWT, bcrypt) │  │(zip extract) │  │(in-memory systems)  │    │       │
│  │  └─────────────┘  └──────────────┘  └───────────────────┘    │       │
│  └──────────────────────────┬───────────────────────────────────┘       │
│                             │                                           │
│  ┌──────────────────────────▼───────────────────────────────────┐       │
│  │  Data Layer                                                   │       │
│  │  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐  │       │
│  │  │Models (ORM)   │  │Schemas (Pydantic)│  │Database (SQLite)│  │       │
│  │  │User, Project  │  │Request/Response │  │SQLAlchemy async │  │       │
│  │  └──────────────┘  └────────────────┘  └──────────────────┘  │       │
│  └──────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI App | App lifecycle, CORS, router mounting | `backend/packages/fgc_core/fgc_core/main.py` |
| Auth Router | Register, login, refresh, get-me endpoints | `backend/packages/fgc_core/fgc_core/routers/auth.py` |
| Users Router | Admin CRUD for users | `backend/packages/fgc_core/fgc_core/routers/users.py` |
| Projects Router | Upload, list, select, copy, delete projects | `backend/packages/fgc_core/fgc_core/routers/projects.py` |
| Equipment Router | Browse, CRUD for categorized GDM equipment | `backend/packages/fgc_core/fgc_core/routers/equipment.py` |
| Network Router | Topology graph, bus list | `backend/packages/fgc_core/fgc_core/routers/network.py` |
| Scenarios Router | Upload, create, timeline, download, save-as-project | `backend/packages/fgc_core/fgc_core/routers/scenarios.py` |
| System Router | Summary, components, export, download | `backend/packages/fgc_core/fgc_core/routers/system.py` |
| AuthService | JWT creation/validation, bcrypt hashing | `backend/packages/fgc_core/fgc_core/services/auth_service.py` |
| FileService | Zip extraction, validation, file copy/delete | `backend/packages/fgc_core/fgc_core/services/file_service.py` |
| GDMService | In-memory DistributionSystem loading, queries, CRUD, scenarios | `backend/packages/fgc_core/fgc_core/services/gdm_service.py` |
| Dependencies | Auth guards (`get_current_user`, `get_admin_user`), DB session | `backend/packages/fgc_core/fgc_core/dependencies.py` |
| Database Config | Async SQLAlchemy engine, session factory, init | `backend/packages/fgc_core/fgc_core/database.py` |
| App Config | Pydantic Settings (env-based config) | `backend/packages/fgc_core/fgc_core/config.py` |
| Vue App | Root component, toast system | `frontend/src/App.vue` |
| App Layout | Sidebar nav, project badge, user section | `frontend/src/layouts/AppLayout.vue` |
| Auth Store | Pinia store: login, register, logout, token persistence | `frontend/src/stores/auth.ts` |
| Project Store | Pinia store: projects CRUD, active selection | `frontend/src/stores/project.ts` |
| API Client | Axios instance, interceptors, typed API functions | `frontend/src/api/client.ts` |
| Router | Vue Router with auth guards | `frontend/src/router/index.ts` |

## Pattern Overview

**Overall:** Layered monolith with a two-backend-target layout (workspace package + standalone app module), served via FastAPI. The backend is essentially a "translation layer" between the filesystem/GDM domain model and the frontend JSON API. The GDMService singleton holds the authoritative runtime state.

**Key Characteristics:**
- **Routers are thin controllers** — they validate auth, extract params, delegate to services, and return responses
- **Services hold business logic** — `GDMService` is the most complex, managing in-memory DistributionSystem objects
- **SQLite + SQLAlchemy async** for persistence (users, projects metadata)
- **The GDM domain model** (`DistributionSystem`) is loaded into memory from uploaded JSON via `gdm_service` singleton — this is NOT persisted to SQLite
- **Two parallel backend implementations** (`fgc_core` package and `app` module) that are code-duplicated
- **JWT token auth** with access + refresh token rotation, stored in localStorage on the frontend
- **Frontend uses Pinia stores** as a cache/state layer between views and API

## Layers

**Router Layer:**
- Purpose: HTTP controllers that handle request/response mapping, validation, auth
- Location: `backend/packages/fgc_core/fgc_core/routers/`
- Contains: 7 router modules (auth, users, projects, equipment, network, scenarios, system)
- Depends on: Dependencies layer for auth guards and DB sessions, Services layer for business logic
- Used by: FastAPI app (`main.py`)

**Dependencies Layer:**
- Purpose: FastAPI dependency injection — auth guards, DB session provision
- Location: `backend/packages/fgc_core/fgc_core/dependencies.py`
- Contains: `get_current_user`, `get_admin_user`, `get_db`
- Depends on: Models, AuthService, Database
- Used by: All routers

**Service Layer:**
- Purpose: Business logic — JWT, file handling, GDM domain operations
- Location: `backend/packages/fgc_core/fgc_core/services/`
- Contains: `auth_service.py`, `file_service.py`, `gdm_service.py`
- Depends on: Config, Models, external libs (bcrypt, jose, gdm, infrasys)
- Used by: Router layer

**Data Layer:**
- Purpose: ORM models, Pydantic schemas, DB engine
- Location: `backend/packages/fgc_core/fgc_core/models/`, `schemas/`, `database.py`
- Contains: `User`, `Project` models; auth, user, project schemas; async SQLite engine
- Depends on: SQLAlchemy, Pydantic, aiosqlite
- Used by: Services, Routers, Dependencies

**Frontend API Layer:**
- Purpose: Axios-based HTTP client with token refresh interceptor
- Location: `frontend/src/api/client.ts`
- Contains: Typed API functions for all backend endpoints
- Depends on: Axios, localStorage tokens
- Used by: Pinia stores

**Frontend State Layer:**
- Purpose: Pinia stores for auth and projects state
- Location: `frontend/src/stores/`
- Contains: `auth.ts`, `project.ts`
- Depends on: API client
- Used by: Views, Layout, Router

**Frontend View Layer:**
- Purpose: Vue 3 single-file components (template + script)
- Location: `frontend/src/views/`
- Contains: 5 views (Login, Register, ModelLoader, Warehouse, Network, Scenarios)
- Depends on: Stores, API client directly (in NetworkView), Leaflet, schemas

## Data Flow

### Primary Request Path (e.g., Equipment List)

1. User navigates to Warehouse view → `WarehouseView.vue` calls `equipmentApi.list(category)`
2. Axios interceptor attaches `Authorization: Bearer <access_token>` from localStorage
3. FastAPI router `equipment.py` → `list_equipment()` validates token via `Depends(get_current_user)`
4. Router calls `_get_active_project_id()` to get the current active project
5. Router delegates to `gdm_service.get_components_by_type(pid, type_name)`
6. `GDMService` queries the in-memory `DistributionSystem` object for matching components
7. Response flows back: serialized component dicts → FastAPI JSON → Axios → View renders

### Auth Flow (Login)

1. User submits credentials in `LoginView.vue`
2. `useAuthStore().login()` calls `authApi.login({username, password})`
3. FastAPI `auth.py#login()` verifies bcrypt hash → generates JWT access token (60min) + refresh token (7 days)
4. Auth Store stores tokens in `localStorage`, then calls `fetchUser()` → `GET /api/auth/me`
5. Router's `beforeEach` guard checks `auth.isAuthenticated` before allowing protected routes
6. On 401 response, Axios interceptor attempts token refresh via `/api/auth/refresh`
7. If refresh fails, tokens are cleared and user is redirected to `/login`

### Project Upload Flow

1. User drops/selects a `.zip` file in `ModelLoaderView.vue`
2. `useProjectStore().uploadProject()` sends multipart POST to `/api/projects/upload`
3. FastAPI `projects.py#upload_model()` reads file content (max 500MB)
4. `FileService.handle_zip_upload()` extracts zip to `{upload_dir}/{user_id}/{uuid4}/`
5. Validates zip safety (rejects path traversal), finds shallowest `.json` file
6. Creates `Project` DB record with `file_path` pointing to extracted JSON
7. Returns `ProjectResponse` to frontend

### Active Project / System Loading Flow

1. User clicks a project card → `selectProject(id)` called
2. POST `/api/projects/{id}/select` → sets `is_active=True` on all user projects (only one active)
3. Router calls `gdm_service.load_system(project_id, file_path)` → `DistributionSystem.from_json(path)`
4. System is cached in `GDMService._systems[project_id]`
5. Subsequent equipment/network/scenario requests auto-load if missing (`_ensure_loaded` / `_get_active_project_id`)

### Scenario Flow

1. User uploads scenario zip → `scenarios.py#upload_scenario()` extracts and loads via `gdm_service.load_scenario_catalog()`
2. Scenario catalog `DistributionSystem` is stored in `GDMService._scenario_catalogs[project_id][filename]`
3. Timeline retrieval: `GET /api/scenarios/timeline?filename=&scenario_name=` → resolves TrackedChange additions/deletions/edits
4. Scenario creation from network ops: tracked operations POSTed to `/api/scenarios/create` → `GDMService.create_scenario_from_ops()`
5. Apply scenario: `GDMService.apply_scenario()` → `apply_updates_to_system()` returns updated copy
6. Export: scenario applied → system serialized to JSON → zipped for download or saved as new project

**State Management:**
- Backend: GDMService singleton holds two in-memory dicts — `_systems` (base systems by project ID) and `_scenario_catalogs` (scenario systems by project ID + filename)
- Frontend: Pinia stores (`auth`, `project`) cache auth state and project list; views fetch data on mount
- Tokens: localStorage-based with Axios interceptor for automatic refresh

## Key Abstractions

**GDMService (Singleton):**
- Purpose: Manages loaded GDM `DistributionSystem` objects in memory, provides query/CRUD/scenario operations
- Location: `backend/packages/fgc_core/fgc_core/services/gdm_service.py`
- Pattern: Global singleton module instance (`gdm_service = GDMService()`)
- State: `_systems: dict[str, DistributionSystem]`, `_scenario_catalogs: dict[str, dict[str, DistributionSystem]]`
- Key methods: `load_system()`, `get_summary()`, `get_topology()`, `get_components_by_type()`, `add_component()`, `update_component()`, `delete_component()`, `create_scenario_from_ops()`, `apply_scenario()`, `export_scenario_zip()`

**Database Session (AsyncSession):**
- Purpose: Provides SQLAlchemy async session per request via FastAPI dependency
- Location: `backend/packages/fgc_core/fgc_core/database.py`
- Pattern: `async_sessionmaker` with `get_db()` generator dependency
- DB: SQLite via aiosqlite

**Auth Guards (FastAPI Dependencies):**
- Purpose: Protect routes with auth and role checks
- Location: `backend/packages/fgc_core/fgc_core/dependencies.py`
- `get_current_user`: Validates JWT bearer token, fetches User from DB
- `get_admin_user`: Decorates `get_current_user` with `is_admin` check

**API Client (Axios):**
- Purpose: Centralized HTTP client with typed API methods and interceptors
- Location: `frontend/src/api/client.ts`
- Pattern: Axios instance with request interceptor (attach token) and response interceptor (handle 401 → refresh)

**Schema Definitions (Frontend):**
- Purpose: Define field-level schemas for GDM equipment types (used by Warehouse forms and Network component forms)
- Location: `frontend/src/types/schemas.ts`
- Pattern: `Record<string, Schema>` where each Schema has type, unit, enum, validation constraints

## Entry Points

**Backend Server:**
- Location: `backend/run.py` → `uvicorn.run("fgc_core.main:app", ...)`
- Triggers: `python run.py` or `start.sh`
- Responsibilities: Start uvicorn server, mount FastAPI app

**FastAPI App:**
- Location: `backend/packages/fgc_core/fgc_core/main.py`
- Lifecycle: `lifespan` context manager → `init_db()` (create tables) → `_seed_admin()` (create default admin)
- Responsibilities: CORS middleware, mount 7 routers, health endpoint

**Vue App:**
- Location: `frontend/src/main.ts`
- Triggers: Vite dev server (npm run dev)
- Responsibilities: Create Vue app, install Pinia + Router, init auth before mount

**Assets/Config Entry:**
- Location: `start.sh`
- Responsibilities: Set `GDM_UPLOAD_DIR` and `GDM_DATABASE_URL` environment variables, start both backend and frontend processes

## Architectural Constraints

- **Threading:** Single-threaded async event loop (FastAPI + SQLAlchemy async + aiosqlite)
- **Global state:** `GDMService` singleton (`backend/packages/fgc_core/fgc_core/services/gdm_service.py:554`) — holds in-memory DistributionSystem objects; lost on server restart unless reloaded
- **Circular imports:** None detected — imports are one-directional: routers → dependencies → services → models/schemas
- **Backend duplication:** `backend/app/` and `backend/packages/fgc_core/fgc_core/` are near-identical copies. The `app/` module was likely the original location, then extracted into the `fgc_core` package.
- **No migration system:** Tables are created via `Base.metadata.create_all` on startup (`database.py:init_db()`), no Alembic or migration tooling
- **CORS:** Hard-coded origins in config (`config.py:27`)

## Anti-Patterns

### Duplicated Backend Code

**What happens:** Two nearly identical implementations exist at `backend/app/` and `backend/packages/fgc_core/fgc_core/`. Both have the same routers, services, models, schemas, database config. The `run.py` imports from `fgc_core.main`, while `app/` appears unused by the active startup path.

**Why it's wrong:** Violates DRY — any change must be made twice, and the `app/` directory is dead code that will drift.

**Do this instead:** Remove `backend/app/` once the `fgc_core` package is confirmed stable, or make `app/` a symbolic link/alias. See `backend/packages/fgc_core/fgc_core/` for the active code.

### Global Singleton State

**What happens:** `GDMService()` is instantiated as a module-level singleton at `gdm_service.py:554`. All routers import and use this single instance. It holds mutable dicts (`_systems`, `_scenario_catalogs`) that persist across requests.

**Why it's wrong:** State is lost on server restart. In a multi-worker production deployment (e.g., multiple uvicorn workers), each worker has its own singleton → inconsistent state. Not testable in isolation without resetting the singleton.

**Do this instead:** Consider a service registry or dependency injection for the GDMService. For multi-worker scenarios, use a shared cache (Redis) or at minimum sticky sessions.

### Schema Definitions Duplicated in Frontend

**What happens:** Equipment field schemas (`SCHEMAS`) are hard-coded in `frontend/src/types/schemas.ts` (~460 lines) mirroring the GDM library's Pydantic model structure.

**Why it's wrong:** Any change to GDM equipment models requires manual frontend schema updates to match. No single source of truth.

**Do this instead:** Generate frontend schemas from the Python GDM models, or add a backend endpoint that reflects the schema for each equipment type.

### No Migration Tooling

**What happens:** Database schema is created via `Base.metadata.create_all` on every startup. There is no migration system.

**Why it's wrong:** Schema changes (new columns, table alterations) require manual SQL or will be lost on recreate. Production DB upgrades are risky.

**Do this instead:** Use Alembic for SQLAlchemy migrations.

## Error Handling

**Strategy:** FastAPI HTTP exceptions with status codes and detail messages. Routers wrap service calls in try/except blocks and raise `HTTPException`.

**Patterns:**
- Auth errors: `401 Unauthorized` (invalid token), `403 Forbidden` (non-admin accessing admin routes), `409 Conflict` (duplicate email/username on register)
- Project errors: `404 Not Found` (unknown project), `422 Unprocessable Entity` (GDM load failure), `413 Request Entity Too Large` (file >500MB)
- Equipment errors: `400 Bad Request` (unknown type, validation), `404 Not Found` (UUID not found)

## Cross-Cutting Concerns

**Logging:** No structured logging detected. Relies on FastAPI/uvicorn default logging. Debug mode controlled by `settings.debug` (SQLAlchemy echo).

**Validation:** Dual validation — Pydantic schemas at the API boundary (request/response), GDM library Pydantic validation for domain objects, manual zip safety checks in `FileService`.

**Authentication:** JWT bearer tokens (OAuth2PasswordBearer scheme). Two dependency guards: `get_current_user` (any authenticated), `get_admin_user` (admin only). Frontend Axios interceptor handles token refresh on 401.

---

*Architecture analysis: 2026-05-22*
