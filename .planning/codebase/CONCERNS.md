# Codebase Concerns

**Analysis Date:** 2026-05-22

## Tech Debt

### Massive Code Duplication Between `backend/app/` and `backend/packages/fgc_core/`

**Issue:** The `backend/app/` and `backend/packages/fgc_core/` directories contain near-identical copies of the same application — both have `main.py`, `dependencies.py`, `config.py`, `database.py`, and complete sets of routers (`auth.py`, `projects.py`, `equipment.py`, `network.py`, `scenarios.py`, `system.py`, `users.py`), services (`auth_service.py`, `file_service.py`, `gdm_service.py`), models (`user.py`, `project.py`), and schemas (`auth.py`, `user.py`, `project.py`). This is a full structural duplication.

**Files:**
- `backend/app/` (24 Python files, ~3,500 lines)
- `backend/packages/fgc_core/` (30 Python files, ~3,500 lines)
- `backend/run.py` line 7 — only runs `fgc_core.main:app`, meaning `backend/app/` is dead code or the "app" is dead code

**Impact:** 
- Any bug fix or feature change must be applied in two places
- Over time the copies will diverge, leading to inconsistent behavior
- ~3,500 lines of dead/unused code wasting maintenance effort
- Confusing for new developers — unclear which copy is canonical
- `backend/app/config.py` reads env file from `"../.env"` while `backend/packages/fgc_core/fgc_core/config.py` reads from `base_dir / ".env"` — these will produce different paths

**Fix approach:** Delete one copy. Choose one as the canonical application and remove the other. Consolidate configuration paths.

### Global Singleton State in `gdm_service.py`

**Issue:** `GDMService` is instantiated as a module-level singleton (`gdm_service = GDMService()`) at `backend/packages/fgc_core/fgc_core/services/gdm_service.py` line 554. All loaded GDM distribution systems are stored in an in-memory dict (`self._systems`) keyed by project ID, with an additional dict for scenario catalogs (`self._scenario_catalogs`).

**Files:**
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py` lines 80-84, 554

**Impact:**
- Systems are lost on server restart — no persistence
- Doesn't work with multiple server processes or workers
- No memory eviction policy — a user with many projects consumes unbounded memory
- Scenario catalogs are loaded into memory but never persisted to database
- `get_system()` raises `KeyError` (a non-HTTP exception) that routers catch with bare `except KeyError` to lazy-load — this is fragile error handling

**Fix approach:** Add a database-backed cache with LRU eviction, or at minimum serialize active systems to disk. Replace `KeyError` handling with an explicit `has_system()` method.

### Hardcoded Paths in Config

**Issue:** `backend/packages/fgc_core/fgc_core/config.py` lines 33-36 hardcode absolute filesystem paths:

```python
if settings.upload_dir is None:
    settings.upload_dir = Path("/home/aadil/Documents/gfc_files/uploads")
if settings.database_url is None:
    settings.database_url = f"sqlite+aiosqlite:///home/aadil/Documents/gfc_files/database/gdm_studio.db"
```

These paths contain a specific developer's home directory (`/home/aadil/Documents/gfc_files/`).

**Files:**
- `backend/packages/fgc_core/fgc_core/config.py` lines 33-36
- `backend/packages/fgc_core/fgc_core/database.py` lines 6-7 (path manipulation of database_url)

**Impact:**
- Application will fail on any other machine unless the exact same directory structure exists
- Production deployment is impossible without changes
- If `GDM_` env vars are not set, the app silently uses these hardcoded paths
- `backend/app/config.py` does NOT have this issue (uses relative paths), which creates path divergence between the two copies

**Fix approach:** Remove these fallbacks. Use relative paths, environment-variable-only configuration, or a configurable data directory with a sensible relative default (e.g., `./data/`).

### Database Migrations Missing

**Issue:** Both `backend/packages/fgc_core/fgc_core/database.py` line 28-30 and `backend/app/database.py` line 22-24 use `Base.metadata.create_all` on every startup. There is no migration system (Alembic or similar).

**Files:**
- `backend/packages/fgc_core/fgc_core/database.py` lines 28-30
- `backend/app/database.py` lines 22-24

**Impact:**
- Schema changes require manual SQL intervention or dropping and recreating the database
- Cannot evolve the schema in production without data loss
- Adding new tables or columns is risky

**Fix approach:** Add Alembic for schema migrations. Disable `create_all` in production.

### No Input Validation on Empty Passwords

**Issue:** The registration endpoint in `backend/packages/fgc_core/fgc_core/routers/auth.py` passes through empty passwords (the schema allows `password: str` with no `min_length`). The frontend has `minlength="6"` in HTML but this is client-side only.

**Files:**
- `backend/packages/fgc_core/fgc_core/schemas/auth.py` line 7: `password: str` (no min_length)
- `backend/packages/fgc_core/fgc_core/routers/auth.py` lines 26-42
- `frontend/src/views/RegisterView.vue` line 24: `minlength="6"` (client-side only)

**Impact:**
- Empty or single-character passwords can be registered via API
- Weak passwords are accepted
- `test_schemas.py` line 33-39 explicitly tests that empty passwords are accepted — this was intentional

**Fix approach:** Add `min_length=8` (or at least `min_length=6`) to `RegisterRequest.password` in the Pydantic schema. Remove or update the test that verifies empty passwords are allowed.

## Security Considerations

### Hardcoded Default Admin Credentials

**Issue:** Both config files hardcode default admin credentials that get seeded on first startup:

```python
admin_username: str = "admin"
admin_password: str = "admin"
```

**Files:**
- `backend/packages/fgc_core/fgc_core/config.py` lines 23-24
- `backend/app/config.py` lines 22-23
- `backend/packages/fgc_core/fgc_core/main.py` lines 26-44 (`_seed_admin()`)

**Impact:**
- If `GDM_ADMIN_USERNAME` and `GDM_ADMIN_PASSWORD` env vars are not set, the default credentials are "admin/admin"
- Anyone who knows default credentials can access the system
- On first startup, the admin user is created automatically with these credentials
- The seed function uses `settings.admin_password` plaintext, which is then immediately hashed — but the plaintext lives in the default config

**Fix approach:** Remove the default values so deployment fails if not configured. Require `GDM_ADMIN_USERNAME` and `GDM_ADMIN_PASSWORD` env vars. Log a warning on first startup saying default admin exists and must be changed.

### JWT Secret Key Regenerated on Every Restart

**Issue:** Both config files define `secret_key: str = secrets.token_urlsafe(32)` as a default. This means unless `GDM_SECRET_KEY` is set in the environment, a new random key is generated every time the application starts.

**Files:**
- `backend/packages/fgc_core/fgc_core/config.py` line 17
- `backend/app/config.py` line 17

**Impact:**
- All existing JWT tokens are invalidated on every restart
- Users are forced to re-login every deployment
- If a load balancer restarts worker processes, sessions are lost

**Fix approach:** Make `secret_key` required (remove default). Add a startup check that crashes with a clear error if `GDM_SECRET_KEY` is missing. Use `Field(validation_alias=...)` with no default.

### Tokens Stored in `localStorage`

**Issue:** The frontend stores `access_token` and `refresh_token` in `localStorage` via `frontend/src/stores/auth.ts`.

**Files:**
- `frontend/src/stores/auth.ts` lines 15-16: `localStorage.setItem('access_token', data.access_token)`
- `frontend/src/api/client.ts` lines 20, 34, 41-42
- `frontend/src/stores/auth.ts` lines 35-36: `localStorage.removeItem('access_token')`

**Impact:**
- `localStorage` is accessible to any JavaScript running on the same origin — XSS vulnerability
- Cannot mark tokens as `HttpOnly` (they are read-accessible via JS)
- Refresh tokens with 7-day expiry stored in `localStorage` extends the attack surface

**Fix approach:** Use `HttpOnly` cookies for the refresh token with a `/api/auth/refresh` endpoint that sets the cookie server-side. Keep the access token in memory with periodic refresh.

### Use of `python-jose` Library

**Issue:** The JWT implementation uses `python-jose[cryptography]` (`jose` package), which has historically had security vulnerabilities and is considered largely unmaintained. The recommended alternative is `PyJWT`.

**Files:**
- `backend/packages/fgc_core/fgc_core/services/auth_service.py` line 5
- `backend/app/services/auth_service.py` line 4
- `backend/requirements.txt` line 6
- `backend/packages/fgc_core/pyproject.toml` line 12

**Impact:**
- Potential unpatched vulnerabilities in the JWT library
- `jose` uses `cryptography` under the hood, but the wrapper layer may have issues
- Token decoding failures are silently caught (bare `except JWTError`) — debugging is hard

**Fix approach:** Migrate to `PyJWT` library. Remove the bare `except JWTError: return None` pattern — log the failure details.

### OAuth2PasswordBearer Allows Unauthenticated Token URL Opens

**Issue:** `OAuth2PasswordBearer(tokenUrl="/api/auth/login")` creates a dependency that when the user is not authenticated, the browser opens a login dialog on some clients. The tokenUrl is configured in dependencies but the actual login endpoint is a POST that returns JSON.

**Files:**
- `backend/packages/fgc_core/fgc_core/dependencies.py` line 9
- `backend/app/dependencies.py` line 10

**Impact:**
- Swagger UI auto-opens the token URL which is a POST endpoint — not actually usable for Swagger auth flows
- The `WWW-Authenticate: Bearer` header sent on 401 may trigger browser HTTP auth dialogs

**Fix approach:** Use a custom `HTTPBearer` scheme or configure `OAuth2PasswordBearer` with `auto_error=False` and handle 401 manually.

## Performance Bottlenecks

### Entire File Content Loaded Into Memory

**Issue:** File upload handlers call `await file.read()` which loads the entire uploaded file into memory before processing. With a max upload size of 500MB, a single request can allocate 500MB of RAM.

**Files:**
- `backend/packages/fgc_core/fgc_core/routers/projects.py` line 32: `content = await file.read()`
- `backend/packages/fgc_core/fgc_core/routers/scenarios.py` line 57: `content = await file.read()`

**Impact:**
- A single large upload can exhaust available memory
- No streaming — must buffer the entire file before checking validity
- Multiple concurrent large uploads will compound memory usage

**Fix approach:** Stream the upload to disk first, then process. Use `UploadFile` methods like `file.file` to read in chunks, or write to a temp file immediately.

### No Caching for Expensive Computations

**Issue:** Topology, component listings, and system summaries are recomputed from scratch on every API call. `get_topology()` iterates all components and builds a graph each time.

**Files:**
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py` lines 103-118 (get_summary iterates all components)
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py` lines 140-163 (get_topology builds graph)
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py` lines 120-127 (get_components_by_type iterates all)

**Impact:**
- Systems with many components will have slow API responses
- No invalidation strategy means every request pays full computation cost
- Component CRUD operations (`add_component`, `update_component`, `delete_component`) don't invalidate any cache

**Fix approach:** Add a simple in-memory cache with TTL or version counter. Invalidate on component mutations.

### Temporary Zip Files Not Cleaned Up After Download

**Issue:** `export_system_zip()` and `export_scenario_zip()` create zip files in temp directories. The FileResponse sends the file, but the temp directory is never cleaned up after the response completes.

**Files:**
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py` lines 431-448: `tempfile.mkdtemp()` but no cleanup
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py` lines 390-410: same pattern for scenarios
- `backend/packages/fgc_core/fgc_core/routers/system.py` line 94-99: FileResponse(zip_path) without cleanup
- `backend/packages/fgc_core/fgc_core/routers/scenarios.py` lines 163-171: same pattern

**Impact:**
- Disk space leak with repeated exports
- Temp directories accumulate on the server

**Fix approach:** Use `tempfile.NamedTemporaryFile` with `delete_on_close=False` and register a background cleanup task, or use a `BackgroundTask` in FastAPI to remove the file after the response is sent.

### Large Frontend Components

**Issue:** Several frontend `.vue` files are very large:

| File | Lines |
|------|-------|
| `frontend/src/views/NetworkView.vue` | 985 |
| `frontend/src/views/ScenariosView.vue` | 951 |
| `frontend/src/views/WarehouseView.vue` | 688 |
| `frontend/src/types/schemas.ts` | 461 |

**Files:**
- `frontend/src/views/NetworkView.vue`
- `frontend/src/views/ScenariosView.vue`
- `frontend/src/views/WarehouseView.vue`
- `frontend/src/types/schemas.ts`

**Impact:**
- Poor maintainability — hard to reason about the component as a whole
- Merge conflicts are likely when multiple developers work on these files
- No component decomposition — map logic, panels, forms, and dialogs are all in one file

**Fix approach:** Decompose into smaller components (e.g., `NetworkMap.vue`, `NetworkPanel.vue`, `ComponentPalette.vue`). Split schema definitions into per-type files.

## Fragile Areas

### `gdm_service.py` — Single 554-Line File with Complex Logic

**Issue:** `backend/packages/fgc_core/fgc_core/services/gdm_service.py` is a single file containing:
- Type registry building
- Quantity coercion logic
- Complete CRUD operations
- Scenario management (apply, export, save-as-project)
- Topology computation
- Serialization
- Reference resolution (string-to-component mapping)

**Files:**
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py` (554 lines)

**Why fragile:**
- `_resolve_references()` has complex logic for resolving component references with multiple fallback paths — silent failures on lookup errors (bare `pass` on exception)
- `apply_scenario()` and related methods operate on deep copies of systems — memory-intensive
- Large broad `except Exception` blocks in routers calling gdm_service methods
- No tests for CRUD operations, scenario management, topology, or quantity coercion
- `TYPE_REGISTRY` is built at import time and cached globally — won't pick up new types without restart

**Safe modification:** Add tests before modifying. Split into smaller service files (e.g., `scenario_service.py`, `equipment_service.py`, `topology_service.py`). Replace bare `except` blocks with specific exception handling.

### Router Files Duplicate Active-Project Logic

**Issue:** Every router (`system.py`, `equipment.py`, `network.py`, `scenarios.py`) has a duplicated `_get_active_project_id()` or `_get_active_project()` helper with exactly the same logic — query DB for active project, lazy-load system if not in memory, return project/ID.

**Files:**
- `backend/packages/fgc_core/fgc_core/routers/system.py` lines 16-23 (`_get_active_project`)
- `backend/packages/fgc_core/fgc_core/routers/system.py` lines 26-36 (`_ensure_loaded` — different pattern)
- `backend/packages/fgc_core/fgc_core/routers/equipment.py` lines 37-48 (`_get_active_project_id`)
- `backend/packages/fgc_core/fgc_core/routers/network.py` lines 15-26 (`_get_active_project_id`)
- `backend/packages/fgc_core/fgc_core/routers/scenarios.py` lines 23-34 (`_get_active_project_id`)

**Why fragile:**
- 4 different implementations of the same logic
- Inconsistent lazy-load: `system.py` has a separate `_ensure_loaded()` function while others inline the logic
- If the active-project resolution logic changes (e.g., database schema changes), all 4 locations must be updated

**Safe modification:** Extract into a single dependency in `dependencies.py`.

### Schema Definitions Duplicated Frontend-to-Backend

**Issue:** Equipment schema field definitions (`SCHEMAS`, `COMPONENT_SCHEMAS`) are defined in 461 lines of TypeScript (`frontend/src/types/schemas.ts`) with field types, units, descriptions, and constraints. These are a partial duplicate of the GDM Python models and are manually maintained.

**Files:**
- `frontend/src/types/schemas.ts` (461 lines)
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py` — `TYPE_REGISTRY` and `_coerce_quantities()`

**Why fragile:**
- Adding a new equipment type requires updating both the Python GDM models and the frontend schemas
- Field types and units can easily diverge between frontend and backend
- No automated verification that frontend schemas match backend models
- 34 equipment/component types defined in TypeScript must match GDM Python classes

**Safe modification:** Generate frontend schemas from the Python GDM model metadata at build time, or add integration tests that verify frontend schemas match backend model fields.

### Silent Token Decode Failure

**Issue:** `decode_token()` in auth_service silently catches `JWTError` and returns `None`. The caller in `dependencies.py` treats `None` as "invalid token" and returns 401. Any JWT decode failure (expired, malformed, wrong algorithm, tampered) produces the exact same response with no logging.

**Files:**
- `backend/packages/fgc_core/fgc_core/services/auth_service.py` lines 30-34
- `backend/app/services/auth_service.py` lines 31-35

**Impact:**
- Impossible to debug token issues in production — is it expired? Wrong key? Malformed?
- Attackers probing the auth endpoint get no useful error information (good for security, bad for debugging)
- But legitimate users with expired tokens also get the same generic error

**Fix approach:** Log the specific JWTError reason at WARNING level, but still return generic 401 to the client.

## Test Coverage Gaps

### Zero Tests for `backend/app/` Module

**Issue:** All tests live in `backend/packages/fgc_core/tests/`. The `backend/app/` module has no tests at all.

**Files:**
- `backend/packages/fgc_core/tests/` — 6 test files
- `backend/app/` — 0 test files

**Risk:** If the `app/` copy ever gets used, nothing verifies it works. Even if it's dead code, there's no proof.

**Priority:** Low (since `app/` may be dead code)

### No Integration Tests for Database Operations

**Issue:** All tests use `MagicMock` and `patch` extensively. There are no tests that exercise the actual database, no test fixtures that create in-memory SQLite databases, and no test for router endpoints.

**Files:**
- `backend/packages/fgc_core/tests/test_auth_service.py` — mocks `settings`
- `backend/packages/fgc_core/tests/test_file_service.py` — mocks `settings`
- `backend/packages/fgc_core/tests/test_dependencies.py` — uses `MagicMock` for users
- `backend/packages/fgc_core/tests/test_schemas.py` — pure schema tests (no mocking needed)

**Risk:** Database layer, model relationships, and actual query behavior are untested. Critical paths like user creation, project CRUD, and authentication workflows have no database-level verification.

**Priority:** High

### No Tests for GDM Service Logic

**Issue:** `gdm_service.py` (554 lines, the most complex file in the codebase) has zero tests — no tests for `add_component`, `update_component`, `delete_component`, `get_topology`, `get_summary`, `load_scenario_catalog`, `create_scenario_from_ops`, quantity coercion, or reference resolution.

**Files:**
- `backend/packages/fgc_core/fgc_core/services/gdm_service.py` — 0 tests

**Risk:** Any change to this file is a blind refactor. The complex `_resolve_references()` and `_coerce_quantities()` methods could break silently since their exception handlers use bare `except: pass`.

**Priority:** High

### No Frontend Tests

**Issue:** There are no frontend test files, no test runner configuration, and no test scripts in `frontend/package.json`.

**Files:**
- `frontend/package.json` — only `dev`, `build`, `preview` scripts
- `frontend/` — no `*.test.*` or `*.spec.*` files

**Risk:** Frontend components (especially the 985-line `NetworkView.vue`) have no automated verification.

**Priority:** Medium

### Frontend Uses TypeScript `~6.0.2` — Very Aggressive Version

**Issue:** `frontend/package.json` line 24 specifies `"typescript": "~6.0.2"`. As of 2026, TypeScript 5.x is the latest stable major version. TypeScript 6.0 is a pre-release or very new major version with potential breaking changes.

**Files:**
- `frontend/package.json` line 24

**Risk:** Potential instability, lack of library type compatibility, or breaking changes.

**Priority:** Medium

## Missing Critical Features

### No Rate Limiting on Auth Endpoints

**Issue:** Login, register, and refresh endpoints have no rate limiting.

**Files:**
- `backend/packages/fgc_core/fgc_core/routers/auth.py` — login (line 46), register (line 26), refresh (line 61)

**Risk:** Brute-force password guessing against the login endpoint, registration spam, or token refresh abuse.

### No Request Logging Middleware

**Issue:** There is no request/response logging middleware. No structured logging.

**Risk:** Debugging production issues requires reproducing locally. Security incidents leave no audit trail.

### No Password Change or Reset Flow

**Issue:** Once registered, there is no way for a user to change their password or reset a forgotten password.

**Files:**
- `backend/packages/fgc_core/fgc_core/schemas/user.py` — `UserUpdate` has no password field
- `backend/packages/fgc_core/fgc_core/routers/users.py` — `update_user` doesn't handle password changes

**Priority:** Medium

### No Pagination on List Endpoints

**Issue:** All list endpoints return unbounded results:
- `GET /api/users/` — returns all users
- `GET /api/projects/` — returns all user's projects
- `GET /api/equipment/` — returns all matching components
- `GET /api/system/components` — returns all components

**Risk:** With enough data, these endpoints will consume excessive memory and produce slow responses.

---

*Concerns audit: 2026-05-22*
