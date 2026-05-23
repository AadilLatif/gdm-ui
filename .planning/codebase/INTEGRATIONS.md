# External Integrations

**Analysis Date:** 2026-05-22

## APIs & External Services

**Domain Modeling (GDM / grid-data-models):**
- **grid-data-models** (local checkout at `/home/aadil/Documents/github/grid-data-models/`)
  - SDK/Client: Installed as editable pip package (`pip install -e`)
  - Interface: Python module `gdm` — used for `DistributionSystem`, `DistributionBus`, equipment types, quantities with `pint` units, and `TrackedChange` scenario management
  - Critical files: `backend/packages/fgc_core/fgc_core/services/gdm_service.py` (primary consumer), `backend/packages/fgc_core/fgc_core/routers/projects.py`, `backend/packages/fgc_core/fgc_core/routers/system.py`, `backend/packages/fgc_core/fgc_core/routers/equipment.py`, `backend/packages/fgc_core/fgc_core/routers/network.py`, `backend/packages/fgc_core/fgc_core/routers/scenarios.py`
  - Usage: Loads system models from JSON, queries components, builds topology graphs, tracks scenario changes, serializes/deserializes distribution network models
  - Quantity system: Uses `pint` `UnitRegistry` via `gdm.quantities.ureg`

**infrasys (Infrastructure System):**
  - Version: 1.1.2
  - Interface: Python package — `infrasys.base_quantity.BaseQuantity`, `infrasys.Component`
  - Used by GDM as its base framework for component management and quantity handling

## Data Storage

**Databases:**
- **SQLite** (via aiosqlite async driver)
  - Connection: `sqlite+aiosqlite:///{path_to_db}` — configured via `GDM_DATABASE_URL` env var
  - Default locations:
    - `backend/app/config.py`: `sqlite+aiosqlite:///{base_dir / 'gdm_studio.db'}` (legacy app)
    - `backend/packages/fgc_core/fgc_core/config.py`: `sqlite+aiosqlite:///home/aadil/Documents/gfc_files/database/gdm_studio.db` (core package — moved to dedicated data directory)
  - Client: SQLAlchemy 2.0 async engine with `async_sessionmaker`
  - Schema: `users` and `projects` tables only (2 tables)
  - No migrations framework — uses `Base.metadata.create_all()` on startup
  - No pooling (SQLite limitation) — single-file database

**File Storage:**
- **Local filesystem only**
  - Upload directory: Configured via `GDM_UPLOAD_DIR` env var
  - Default: `/home/aadil/Documents/gfc_files/uploads/`
  - Structure: `{upload_dir}/{user_id}/{uuid4()}/upload.zip` -> extracted to same directory
  - Zip-based: Users upload `.zip` files containing GDM JSON model + optional `time_series/` folder
  - 500MB max upload size enforced in routers
  - No cloud storage (S3, GCS, etc.) integration

**Caching:**
- None detected. The `GDMService` keeps systems in memory as Python objects in `self._systems` and `self._scenario_catalogs` dicts (in-memory only, no TTL or eviction)

## Authentication & Identity

**Auth Provider:**
- **Custom JWT-based authentication** (no external provider)
  - Implementation: `backend/packages/fgc_core/fgc_core/services/auth_service.py`
  - Token type: JWT (HS256) via `python-jose`
  - Access token: 60 min expiry, stores `{"sub": user.id, "type": "access"}`
  - Refresh token: 7 days expiry, stores `{"sub": user.id, "type": "refresh"}`
  - Password hashing: bcrypt with salts
  - Token transport: Bearer token in `Authorization` header
  - Token refresh: Automatic in frontend via Axios response interceptor (`frontend/src/api/client.ts` lines 28-54)
  - Default admin: seeded on first startup (`admin/admin` with `username=settings.admin_username`, `password=settings.admin_password`)
  - Auth endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/me`

**No support for:**
- OAuth2 social login (Google, GitHub, etc.)
- SSO / SAML
- MFA / 2FA
- Session-based auth

## Monitoring & Observability

**Error Tracking:**
- None detected. No Sentry, Datadog, or similar integrations

**Logging:**
- FastAPI/uvicorn default logging only
- SQLAlchemy echo mode via `settings.debug` flag (off by default)
- No structured logging, no log aggregation

**Health Check:**
- Single endpoint: `GET /api/health` returns `{"status": "ok"}`

## CI/CD & Deployment

**Hosting:**
- No production hosting configured. Development-only setup

**CI Pipeline:**
- No CI config found (no `.github/workflows/`, no Docker, no docker-compose)

**Deployment:**
- Manual: `start.sh` script launches both backend (uvicorn) and frontend (Vite dev server) concurrently
- Backend: `uvicorn fgc_core.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend: `npm run dev` (Vite dev server on port 5173)
- Backend can also be started standalone via `python run.py`

## Environment Configuration

**Required env vars (`GDM_` prefix):**
- `GDM_DATABASE_URL` — SQLite connection string (e.g., `sqlite+aiosqlite:///path/to/gdm_studio.db`)
- `GDM_UPLOAD_DIR` — Filesystem path for uploaded zip storage
- `GDM_SECRET_KEY` — JWT signing key (auto-generated random by default if not set)
- `GDM_CORS_ORIGINS` — Allowed CORS origins (default: `["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]`)

**Optional env vars:**
- `GDM_DEBUG` — Enable debug mode
- `GDM_APP_NAME` — Application display name
- `GDM_ALGORITHM` — JWT algorithm (default: HS256)
- `GDM_ACCESS_TOKEN_EXPIRE_MINUTES` — Access token TTL (default: 60)
- `GDM_REFRESH_TOKEN_EXPIRE_DAYS` — Refresh token TTL (default: 7)
- `GDM_ADMIN_USERNAME` — Default admin username (default: admin)
- `GDM_ADMIN_PASSWORD` — Default admin password (default: admin)

**Frontend env vars (`VITE_` prefix):**
- `VITE_API_URL` — Backend API base URL (default: `http://localhost:8000`)

**Secrets location:**
- No secret management system. JWT key generated in-memory via `secrets.token_urlsafe(32)` if `GDM_SECRET_KEY` not set
- `.env` file can be placed at project root (referenced in config via `env_file: "../.env"`) — listed in `.gitignore`

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected. No webhook delivery system

## External Map Tiles

**Map Service:**
- **OpenStreetMap** (via Leaflet default tiles)
  - Usage: Network topology visualization in `NetworkView.vue` and `ScenariosView.vue`
  - No API key required (uses built-in Leaflet tile layer)
  - No custom tile server configured

---

*Integration audit: 2026-05-22*
