# Coding Conventions

**Analysis Date:** 2026-05-22

## Backend (Python) — `backend/packages/fgc_core/` and `backend/app/`

### Naming Patterns

**Files:**
- snake_case for all Python files: `auth_service.py`, `file_service.py`, `gdm_service.py`, `test_auth_service.py`
- `__init__.py` for package barrels, either empty or with explicit re-exports

**Functions:**
- snake_case for all functions and methods: `hash_password()`, `create_access_token()`, `handle_zip_upload()`, `_get_active_project_id()`
- Async functions use `async def` with no special prefix/suffix convention (e.g., `async def register(...)`)
- Private/helper functions prefixed with underscore: `_seed_admin()`, `get_user_project()`, `_build_type_registry()`

**Variables:**
- snake_case: `access_token`, `project_dir`, `user_id`, `mock_settings`
- Module-level constants in UPPER_CASE: `MAX_UPLOAD_SIZE = 500 * 1024 * 1024`, `EQUIPMENT_CATEGORIES`, `TYPE_REGISTRY`

**Classes:**
- PascalCase for all classes:
  - Pydantic models: `Settings`, `RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`, `UserUpdate`, `ProjectResponse`, `ProjectUpdate`, `AddEquipmentRequest`, `UpdateEquipmentRequest`
  - SQLAlchemy models: `User`, `Project`
  - Service classes: `GDMService`
  - SQLAlchemy base: `Base`

**Types:**
- Python 3.12+ union syntax (`X | None` instead of `Optional[X]`): `def delete_project_files(file_path: str):`, `def decode_token(token: str) -> dict | None:`
- Pydantic v2 `model_config = {"from_attributes": True}` for ORM-bound response schemas
- SQLAlchemy Mapped types: `Mapped[str]`, `Mapped[bool]`, `Mapped[datetime]`

### Code Style

**Formatting:**
- Ruff (no separate formatter configured — Ruff handles both linting and formatting)
- Config: `backend/pyproject.toml` at workspace root
- `src = ["packages"]` in ruff config for `fgc_core/` package resolution

**Linting:**
- Tool: Ruff, configured in `backend/pyproject.toml`
- Enabled rulesets: `E` (pycodestyle), `F` (pyflakes), `I` (isort), `UP` (pyupgrade), `B` (flake8-bugbear), `C4` (flake8-comprehensions), `SIM` (flake8-simplify)
- Ignored rules: `E501` (line length — no enforced limit), `B008` (function call in default args), `C901` (cyclomatic complexity), `B904` (raise-within-except), `SIM105` (simplify context managers)
- Per-file ignores: `__init__.py` → `F401` (unused imports allowed in barrel files)
- Inline `# noqa: E712` used for boolean comparison against `True` literal: `Project.is_active == True  # noqa: E712`

```python
# Example inline suppression
select(Project).where(Project.owner_id == user.id, Project.is_active == True)  # noqa: E712
```

### Import Organization

**Order:**
1. Standard library: `from __future__ import annotations`, `import io`, `import json`, `from pathlib import Path`, `from uuid import uuid4`
2. Third-party: `import pytest`, `from fastapi import APIRouter`, `from sqlalchemy import select`, `import bcrypt`
3. First-party (app): `from fgc_core.config import settings`, `from app.database import get_db`

**Style:**
- Absolute imports always: `from fgc_core.services.auth_service import hash_password` — never relative
- Multi-line imports from same module grouped in parentheses:
  ```python
  from fgc_core.services.file_service import (
      copy_project_files,
      delete_project_files,
      handle_zip_upload,
  )
  ```

**Path Aliases:**
- None used. Imports use the full package path: `from fgc_core.models.user import User` or `from app.models.user import User`

### Error Handling

**Patterns:**
- FastAPI `HTTPException` raised with explicit status code and detail message:
  ```python
  raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
  ```
- Service-layer errors raised as `ValueError` with descriptive message, caught in router and converted to `HTTPException`:
  ```python
  try:
      project_dir, json_path = handle_zip_upload(content, file.filename, user.id)
  except ValueError as e:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
  ```
- Token decode failures return `None` rather than raising — caller checks for `None`:
  ```python
  def decode_token(token: str) -> dict | None:
      try:
          return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
      except JWTError:
          return None
  ```
- Generous broad exception catching for third-party operations:
  ```python
  except Exception as e:
      raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to load model: {e}")
  ```

### Logging

**Framework:** Not detected — no logging module usage. The codebase uses `print` or exceptions only. FastAPI's `echo=settings.debug` is the only debug mechanism (passed to SQLAlchemy engine).

### Comments

**When to Comment:**
- Module-level docstrings for service modules: `"""Service for handling file uploads (zip extraction, validation)."""`
- Function docstrings for complex operations (triple-quoted):
  ```python
  def handle_zip_upload(file_content: bytes, original_filename: str, user_id: str) -> tuple[str, str]:
      """Extract uploaded zip, find the GDM JSON file, and return (project_dir, json_path).

      Expected zip structure: contains a .json file and optionally a *_time_series/ directory.
      """
  ```
- Inline comments for security-sensitive operations: `# Security: reject entries with absolute paths or path traversal`
- Router function docstrings for non-obvious endpoints: `"""Set a project as the active model and load it into memory."""`
- Section comments for class-level method groups: `# ===== Scenario catalog management =====`, `# ===== CRUD operations =====`

**JSDoc/TSDoc:** Not used on the Python side. On the frontend TypeScript side, no JSDoc comments are used.

### Function Design

**Size:** Functions range from small single-purpose (helpers like `hash_password`, `verify_password`) to larger service methods (e.g., `get_scenario_timeline` at ~65 lines). Router functions are typically 10–30 lines.

**Parameters:** Maximum of ~5 positional parameters for complex service methods. Router functions accept 3-4 FastAPI `Depends` parameters.

**Return Values:**
- Service functions return plain types (`dict`, `str`, `tuple[str, str]`) or `None`
- Router functions return Pydantic models (via `response_model`) or plain dicts/strings
- Error states return `None` (e.g., `decode_token` returns `dict | None`)

### Module Design

**Exports:**
- Services expose top-level functions (not inside classes except `GDMService`)
- All functions/classes are public unless prefixed with `_`
- Barrel `__init__.py` files either empty or re-export model classes:
  ```python
  # fgc_core/models/__init__.py
  from fgc_core.models.project import Project
  from fgc_core.models.user import User
  ```

**Singleton Pattern:**
- Module-level singleton instances used for service classes and configuration:
  ```python
  # gdm_service.py
  gdm_service = GDMService()

  # config.py
  settings = Settings()

  # dependencies.py
  oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
  ```

### Router Conventions (FastAPI)

- Each resource area in its own `routers/{name}.py` file
- `router = APIRouter(prefix="/api/{resource}", tags=["{resource}"])` at module level
- All route handlers are `async def`
- Dependencies injected via `Depends()` in parameter list
- Response model specified via decorator `response_model=`
- Status codes explicitly set via `status_code=`
- Return type annotations used: `-> dict[str, Any]`, `-> list[dict[str, Any]]`

## Frontend (TypeScript/Vue) — `frontend/src/`

### Naming Patterns

**Files:**
- PascalCase for Vue components: `App.vue`, `LoginView.vue`, `AppLayout.vue`, `NetworkView.vue`
- camelCase for TS modules: `client.ts`, `useToast.ts`, `index.ts`
- kebab-case for CSS files: `main.css`, `power-icons.css`

**Functions:**
- camelCase: `fetchProjects()`, `handleLogin()`, `uploadProject()`, `selectProject()`

**Variables:**
- camelCase: `isAuthenticated`, `activeProject`, `loading`, `toasts`

**Types:**
- PascalCase for interfaces: `User`, `Project`, `LoginRequest`, `TokenResponse`, `Toast`
- PascalCase for type aliases: `EquipmentCategories`

### Code Style

**Formatting:** No ESLint or Prettier config detected. No formatting rules configured. Default Vite/Vue tooling.

### Import Organization

**Order:**
1. Vue/Pinia imports: `import { ref } from 'vue'`, `import { defineStore } from 'pinia'`
2. Third-party: `import axios from 'axios'`
3. Local modules (always relative): `import '../types/api'`, `import { useAuthStore } from '../stores/auth'`

**Path Aliases:** Not configured in vite.config.ts (no `resolve.alias`).

### Vue Component Conventions

- Composition API with `<script setup lang="ts">` (never Options API)
- Template + Script + Optional Style in single file components (`.vue`)
- Reactive state with `ref()` and `computed()`
- Store access via `useAuthStore()`, `useProjectStore()` (Pinia composition stores)
- Async handlers in `<script setup>` with try/catch/finally

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const username = ref('')
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  try {
    await auth.login(username.value, password.value)
  } catch (e: unknown) {
    error.value = 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>
```

### Error Handling (Frontend)

- try/catch with type assertion for Axios errors:
  ```typescript
  const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  ```
- stores use try/catch with silent fallback:
  ```typescript
  try {
    const { data } = await authApi.me()
    user.value = data
  } catch {
    user.value = null
  }
  ```

---

*Convention analysis: 2026-05-22*
