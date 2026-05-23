# Technology Stack

**Analysis Date:** 2026-05-22

## Languages

**Primary:**
- Python >=3.12 — Backend API, core domain logic (`backend/packages/fgc_core/`, `backend/app/`, `backend/run.py`)
- TypeScript ~6.0 — Frontend application (`frontend/src/`)
- Vue 3 SFC (Single-File Components) — `.vue` files combining HTML template, `<script setup lang="ts">`, and scoped CSS

**Secondary:**
- CSS3 — Custom styling (`frontend/src/styles/main.css`, `frontend/src/styles/power-icons.css`)
- HTML5 — App shell (`frontend/index.html`)

## Runtime

**Environment:**
- Python 3.12+ runtime for backend
- Node.js (via Vite dev server) for frontend dev/build

**Package Managers:**
- **uv** (workspace manager) — `backend/pyproject.toml` defines workspace with members `["packages/*"]` — `backend/uv.lock` present
- **npm** — Frontend dependencies via `frontend/package-lock.json`

**Lockfiles:**
- `backend/uv.lock` — present, committed
- `frontend/package-lock.json` — present, committed

## Frameworks

**Core Backend:**
- **FastAPI** >=0.115.0 — Async Python web framework (`backend/packages/fgc_core/pyproject.toml`)
  - Version installed: 0.115.6
  - CORS middleware configured for Vue dev server origins
  - Async lifespan handler for DB init and admin seeding
- **SQLAlchemy** >=2.0 — Async ORM with aiosqlite driver (`backend/packages/fgc_core/fgc_core/database.py`)
  - Version installed: 2.0.36
  - `AsyncSession` + `async_sessionmaker` pattern used throughout
  - `DeclarativeBase` for model definitions
- **Pydantic** >=2.0 with **pydantic-settings** >=2.0 — Validation and config
  - Version installed: 2.13.4 (pydantic)

**Core Frontend:**
- **Vue 3** ^3.5.34 — Composition API with `<script setup>` throughout
- **Pinia** ^3.0.4 — State management stores (`frontend/src/stores/auth.ts`, `frontend/src/stores/project.ts`)
- **Vue Router** ^4.6.4 — Client-side routing with navigation guards (`frontend/src/router/index.ts`)
- **Axios** ^1.16.1 — HTTP client with interceptors for token management (`frontend/src/api/client.ts`)

**Mapping:**
- **Leaflet** ^1.9.4 — Interactive network topology map (`frontend/src/views/NetworkView.vue`, `frontend/src/views/ScenariosView.vue`)

**Testing:**
- **pytest** >=8.0 — Backend test runner (`backend/packages/fgc_core/tests/`)
- **pytest-asyncio** >=0.24.0 — Async test support
- Unittest mock used in test fixtures

**Build/Dev:**
- **Vite** ^8.0.12 — Frontend dev server and build tool (`frontend/vite.config.ts`)
- **vue-tsc** ^3.2.8 — TypeScript type-checker for Vue SFCs
- **@vitejs/plugin-vue** ^6.0.6 — Vite Vue plugin
- **ruff** >=0.11.0 — Backend linter/formatter (`backend/pyproject.toml`)

**Linting Configuration (ruff):**
- Rules: `["E", "F", "I", "UP", "B", "C4", "SIM"]`
- Ignored: `["E501", "B008", "C901", "B904", "SIM105"]`
- Per-file: `"__init__.py"` ignores `"F401"`

## Key Dependencies

### Backend (core — `fgc_core`)

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | >=0.115.0 | Web framework |
| `uvicorn[standard]` | >=0.32.0 | ASGI server |
| `sqlalchemy` | >=2.0 | ORM |
| `aiosqlite` | >=0.20.0 | Async SQLite driver |
| `pydantic` | >=2.0 | Data validation |
| `pydantic-settings` | >=2.0 | Settings management |
| `python-jose[cryptography]` | >=3.3.0 | JWT encode/decode |
| `bcrypt` | >=4.0 | Password hashing |
| `python-multipart` | >=0.0.12 | File upload parsing |
| `email-validator` | >=2.0 | Email validation |
| `greenlet` | >=3.0 | SQLAlchemy async requirement |
| `gdm` / `grid-data-models` | local checkout | Distribution system modeling framework |
| `infrasys` | 1.1.2 | Infrastructure system (GDM dependency) |

**GDM/grid-data-models note:** The `gdm` package is installed via editable local checkout (`pip install -e` from `grid-data-models/`). Required for `DistributionSystem`, equipment/component models, quantity types, and tracked change support.

### Frontend (production)

| Package | Version | Purpose |
|---------|---------|---------|
| `vue` | ^3.5.34 | UI framework |
| `pinia` | ^3.0.4 | State management |
| `vue-router` | ^4.6.4 | Routing |
| `axios` | ^1.16.1 | HTTP client |
| `leaflet` | ^1.9.4 | Map visualization |
| `remixicon` | ^4.9.1 | Icon set |

## Configuration

**Environment:**
- **Backend:** `pydantic-settings` with `GDM_` prefix via `model_config = {"env_prefix": "GDM_", "env_file": "../.env"}`
  - Environment variables: `GDM_APP_NAME`, `GDM_DEBUG`, `GDM_DATABASE_URL`, `GDM_SECRET_KEY`, `GDM_ALGORITHM`, `GDM_ACCESS_TOKEN_EXPIRE_MINUTES`, `GDM_REFRESH_TOKEN_EXPIRE_DAYS`, `GDM_ADMIN_USERNAME`, `GDM_ADMIN_PASSWORD`, `GDM_CORS_ORIGINS`, `GDM_UPLOAD_DIR`
- **Frontend:** Vite env vars via `import.meta.env.VITE_API_URL` — defaults to `http://localhost:8000`
- **Startup script** (`start.sh`): sets `GDM_UPLOAD_DIR` and `GDM_DATABASE_URL` as environment variables

**Configuration Files:**
- `backend/pyproject.toml` — UV workspace + Ruff config
- `backend/packages/fgc_core/pyproject.toml` — Package definition + dependencies
- `backend/requirements.txt` — Loose requirements (GDM local checkout noted)
- `frontend/vite.config.ts` — Vite config
- `frontend/tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json` — TypeScript config

**Platform Requirements:**

**Development:**
- Python >=3.12 with pip/uv
- Node.js + npm (for Vite dev server)
- GDM package (`grid-data-models`) installed as editable checkout in `backend/.venv/`
- Backend runs on port 8000, frontend on port 5173

**Production:**
- Not explicitly configured (no Dockerfile, no docker-compose, no deployment scripts found)
- Currently designed for localhost development only
- SQLite storage (not suitable for multi-user production at scale)

---

*Stack analysis: 2026-05-22*
