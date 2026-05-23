# Codebase Structure

**Analysis Date:** 2026-05-22

## Directory Layout

```
fgc-studio/
├── backend/
│   ├── app/                              # [DUPLICATE] Standalone backend module (unused)
│   ├── packages/
│   │   └── fgc_core/                     # Core backend package (active)
│   │       ├── fgc_core/                 # Package source
│   │       ├── tests/                    # Pytest tests
│   │       ├── pyproject.toml            # Package definition
│   │       └── uploads/                  # Uploaded model files
│   ├── run.py                           # Server entrypoint
│   ├── pyproject.toml                   # UV workspace definition
│   ├── requirements.txt
│   └── uv.lock
├── frontend/
│   ├── src/
│   │   ├── api/                         # Axios client + typed API methods
│   │   ├── composables/                 # Vue composables (useToast)
│   │   ├── layouts/                     # Layout components (AppLayout)
│   │   ├── router/                      # Vue Router config
│   │   ├── stores/                      # Pinia stores (auth, project)
│   │   ├── styles/                      # CSS files (main, power-icons)
│   │   ├── types/                       # TypeScript interfaces + schemas
│   │   ├── views/                       # Page components (6 views)
│   │   ├── App.vue                      # Root component
│   │   └── main.ts                      # Vue app bootstrap
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   └── tsconfig*.json
├── start.sh                             # Dev server startup script
├── uploads/                             # Project-level uploads directory
└── .planning/
    └── codebase/                        # Codebase analysis documents
```

## Directory Purposes

**`backend/packages/fgc_core/fgc_core/` (Active Backend):**
- Purpose: Core backend package — FastAPI application, business logic, data access
- Contains: Routers, Services, Models, Schemas, Config, Database setup
- Key files:
  - `main.py`: FastAPI app creation, CORS, lifespan, router mounting
  - `config.py`: Pydantic Settings with env prefix `GDM_`
  - `database.py`: Async SQLAlchemy engine + session factory
  - `dependencies.py`: Auth guard Dependencies (`get_current_user`, `get_admin_user`)
  - `routers/`: 7 router modules (auth, users, projects, equipment, network, scenarios, system)
  - `services/`: 3 services (auth_service, file_service, gdm_service)
  - `models/`: 2 ORM models (User, Project)
  - `schemas/`: 3 schema modules (auth, user, project)

**`backend/app/` (Duplicate/Unused Backend):**
- Purpose: Original standalone backend module (now mirrored in `fgc_core`)
- Contains: Same structure as `fgc_core` — identical router/service/model files
- Status: NOT used by `run.py` startup script. Duplicate code.

**`frontend/src/api/`:**
- Purpose: Centralized HTTP client
- Contains: `client.ts` — Axios instance with request auth interceptor and 401 refresh interceptor, typed API endpoint functions
- Named exports: `authApi`, `projectsApi`, `systemApi`, `equipmentApi`, `networkApi`, `scenariosApi`

**`frontend/src/stores/`:**
- Purpose: Pinia state management
- Contains:
  - `auth.ts`: User auth state, login/register/logout actions, token management
  - `project.ts`: Projects list, active project selection, summary caching

**`frontend/src/views/`:**
- Purpose: Full-page Vue components (one per route)
- Contains:
  - `LoginView.vue` — Login form
  - `RegisterView.vue` — Registration form
  - `ModelLoaderView.vue` — Project upload, list, select, delete, copy (265 lines)
  - `WarehouseView.vue` — Equipment browser with categories, search, CRUD forms (688 lines)
  - `NetworkView.vue` — Leaflet-based network topology map with drag-drop component palette, scenario mode (985 lines)
  - `ScenariosView.vue` — Scenario timeline visualization with Leaflet map (951 lines)

**`frontend/src/types/`:**
- Purpose: TypeScript type definitions
- Contains:
  - `api.ts`: API response/request interfaces (User, Project, Token, SystemSummary, Topology, etc.)
  - `schemas.ts`: GDM equipment field schemas, icon mappings, category definitions, enum values (461 lines)

## Key File Locations

**Entry Points:**
- `backend/run.py`: Server startup — runs `uvicorn` with `fgc_core.main:app`
- `frontend/src/main.ts`: Vue app bootstrap — creates app, installs Pinia + Router, initializes auth
- `start.sh`: Dev environment startup — sets env vars, starts backend and frontend

**Configuration:**
- `backend/packages/fgc_core/fgc_core/config.py`: All backend settings (DB URL, JWT secret, CORS origins, upload dir) with `GDM_` env prefix
- `frontend/vite.config.ts`: Vite plugin config (Vue only)
- `frontend/package.json`: Scripts, dependencies (Vue, Pinia, Router, Axios, Leaflet)
- `backend/pyproject.toml`: UV workspace definition + Ruff linter config
- `backend/packages/fgc_core/pyproject.toml`: Package deps (FastAPI, SQLAlchemy, Pydantic, JOSE, bcrypt)

**Core Logic:**
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py`: GDM domain operations — load/extract/query/CRUD/scenario management (554 lines, largest file)
- `backend/packages/fgc_core/fgc_core/routers/equipment.py`: Equipment CRUD with category groupings
- `backend/packages/fgc_core/fgc_core/routers/scenarios.py`: Scenario upload, creation, timeline, export
- `backend/packages/fgc_core/fgc_core/routers/projects.py`: Project management (upload, select, copy, delete)
- `frontend/src/api/client.ts`: All API endpoint definitions + Axios interceptors
- `frontend/src/types/schemas.ts`: Equipment schema definitions for frontend forms

**Database:**
- `backend/packages/fgc_core/fgc_core/database.py`: Async SQLite engine + session
- `backend/packages/fgc_core/fgc_core/models/user.py`: User ORM (id, email, username, hashed_password, is_active, is_admin)
- `backend/packages/fgc_core/fgc_core/models/project.py`: Project ORM (id, name, description, file_path, is_active, owner_id)
- `backend/packages/fgc_core/gdm_studio.db`: SQLite database file

**Testing:**
- `backend/packages/fgc_core/tests/`: Pytest tests (config, schemas, dependencies, file_service, auth_service)
- `backend/packages/fgc_core/tests/conftest.py`: Test fixtures

## Naming Conventions

**Files:**
- Python: `snake_case.py` — e.g., `auth_service.py`, `file_service.py`, `gdm_service.py`
- Vue: `PascalCase.vue` — e.g., `LoginView.vue`, `ModelLoaderView.vue`, `NetworkView.vue`
- TypeScript: `camelCase.ts` — e.g., `client.ts`, `api.ts`, `schemas.ts`
- Config files: Standard names — `pyproject.toml`, `vite.config.ts`, `package.json`

**Directories:**
- Backend: Plural nouns — `routers/`, `services/`, `models/`, `schemas/`
- Frontend: Singular nouns — `api/`, `router/`, `stores/`, `views/`, `styles/`, `types/`, `composables/`

**Python Functions:**
- `snake_case` — e.g., `get_current_user`, `hash_password`, `handle_zip_upload`, `_get_active_project_id`

**Python Classes:**
- `PascalCase` — e.g., `User`, `Project`, `Settings`, `GDMService`, `TokenResponse`, `LoginRequest`

**TypeScript/Vue:**
- Functions: `camelCase` — e.g., `fetchUser`, `handleLogin`, `loadTopology`, `fitBounds`
- Interfaces: `PascalCase` — e.g., `User`, `Project`, `TokenResponse`, `SystemSummary`
- Components: `PascalCase` — e.g., `AppLayout`, `LoginView`
- Pinia stores: `camelCase` with `use` prefix — `useAuthStore`, `useProjectStore`

**API Route Prefixes:**
- `/api/auth/*`, `/api/users/*`, `/api/projects/*`, `/api/system/*`, `/api/equipment/*`, `/api/network/*`, `/api/scenarios/*`

## Where to Add New Code

**New Feature (Backend):**
- New router: `backend/packages/fgc_core/fgc_core/routers/{feature}.py`
- New service: `backend/packages/fgc_core/fgc_core/services/{feature}_service.py`
- New model: `backend/packages/fgc_core/fgc_core/models/{feature}.py`
- New schema: `backend/packages/fgc_core/fgc_core/schemas/{feature}.py`
- Register router in: `backend/packages/fgc_core/fgc_core/main.py`

**New Feature (Frontend):**
- New view: `frontend/src/views/{Feature}View.vue`
- New store: `frontend/src/stores/{feature}.ts`
- New API methods: `frontend/src/api/client.ts` (add to existing export objects or create new)
- New route: `frontend/src/router/index.ts`
- New types: `frontend/src/types/api.ts`

**New Component/Module:**
- Shared backend utility: `backend/packages/fgc_core/fgc_core/`
- Shared frontend component: `frontend/src/components/` (directory does not exist yet, create if needed)
- Shared composable: `frontend/src/composables/{name}.ts`

**New Tests:**
- Backend: `backend/packages/fgc_core/tests/test_{feature}.py`
- Frontend: No test framework detected

**Configuration:**
- Backend env var: Add `GDM_*` entry to `config.py` Settings class and `start.sh` if needed
- Frontend env var: Add `VITE_*` entry, accessed via `import.meta.env`

## Special Directories

**`uploads/`:**
- Purpose: Stores uploaded project zip files, extracted model JSON files, scenario files
- Structure: `{upload_dir}/{user_id}/{uuid4}/` per upload
- Generated: Yes
- Committed: No (contents are user data)

**`backend/packages/fgc_core/uploads/`:**
- Purpose: Legacy upload directory for the package-local run
- Generated: Yes
- Committed: No

**`.planning/`:**
- Purpose: Planning and codebase analysis documents
- Contains: `codebase/` with architecture and convention docs
- Generated: Yes (by GSD tools)
- Committed: Yes

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No

**`node_modules/`:**
- Purpose: npm dependencies
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-05-22*
