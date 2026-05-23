# Testing Patterns

**Analysis Date:** 2026-05-22

## Test Framework

**Runner:**
- pytest >=8.0, configured in `backend/packages/fgc_core/pyproject.toml` (dev dependency)
- pytest-asyncio >=0.24.0 for async test support
- Config: No explicit `pytest.ini` or `pyproject.toml` [tool.pytest.ini_options] found — uses defaults

**Assertion Library:**
- Built-in `assert` statements (pytest-native assertions)
- `pytest.raises(ValidationError)` for Pydantic validation errors
- `pytest.raises(ValueError, match="...")` for value errors with message matching
- `pytest.raises(HTTPException)` for FastAPI HTTP errors

**Run Commands:**
```bash
# From backend/ directory:
# Run fgc_core package tests:
cd packages/fgc_core && pytest

# Run all tests in workspace:
cd packages/fgc_core && pytest -v

# Run specific test file:
cd packages/fgc_core && pytest tests/test_auth_service.py

# Run specific test class:
cd packages/fgc_core && pytest tests/test_auth_service.py -k "TestHashPassword"

# Watch mode: not configured
# Coverage: not configured (no pytest-cov dependency)
```

**Test discovery:**
- pytest auto-discovers `tests/` directory in `packages/fgc_core/`
- Test files matched by `test_*.py` pattern
- Test functions matched by `test_*` prefix
- Test classes matched by `Test*` prefix

## Test File Organization

**Location:**
- Tests are **not** co-located with source. They live in a separate `tests/` directory at the package root:
  ```
  backend/packages/fgc_core/tests/
  ├── __init__.py
  ├── conftest.py
  ├── test_auth_service.py
  ├── test_config.py
  ├── test_dependencies.py
  ├── test_file_service.py
  └── test_schemas.py
  ```

**Naming:**
- Test files: `test_{module_name}.py` — maps to the module under test:
  - `test_auth_service.py` → `fgc_core/services/auth_service.py`
  - `test_file_service.py` → `fgc_core/services/file_service.py`
  - `test_schemas.py` → `fgc_core/schemas/{auth,user,project}.py`
  - `test_config.py` → `fgc_core/config.py`
  - `test_dependencies.py` → `fgc_core/dependencies.py`

**Structure:**
- `conftest.py` at `tests/conftest.py` for shared fixtures
- `__init__.py` at `tests/__init__.py` (empty, marks as package)

**No frontend tests exist:**
- `frontend/` has no test files, no test framework configured, and no `vitest`, `jest`, or `cypress` dependencies in `package.json`

## Test Structure

**Suite Organization:**
- Tests are organized in **classes** (not standalone functions):
```python
# tests/test_auth_service.py
class TestHashPassword:
    def test_hash_password_returns_string(self):
        result = hash_password("testpassword123")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_password_different_each_time(self):
        hash1 = hash_password("password")
        hash2 = hash_password("password")
        assert hash1 != hash2
```

**Patterns:**
- **Setup:** No per-class or per-module setup/teardown. Fixtures from `conftest.py` are passed as function parameters.
- **Teardown:** Not used. `tmp_path` fixture (built-in) handles cleanup automatically.
- **Assertion:** Single concern per test method. Tests follow the pattern of one logical assertion, sometimes with multiple `assert` statements for related properties.
- **Naming:** `test_{behavior_or_condition}` — descriptive of the scenario being tested.

```python
# Naming examples:
def test_hash_password_returns_string(self)
def test_verify_password_correct(self)
def test_verify_password_incorrect(self)
def test_decode_invalid_token(self)
def test_decode_expired_token(self)
def test_zip_with_traversal_path_rejected(self)
def test_zip_without_json_raises_error(self)
def test_all_optional_fields(self)
def test_default_token_type(self)
```

## Mocking

**Framework:** `unittest.mock` from the standard library (no `pytest-mock` dependency).

**Patterns:**
```python
from unittest.mock import patch, MagicMock, AsyncMock

# Patching module-level settings
@patch("fgc_core.services.auth_service.settings")
def test_create_access_token_returns_string(self, mock_settings):
    mock_settings.secret_key = "test-secret"
    mock_settings.algorithm = "HS256"
    mock_settings.access_token_expire_minutes = 60
    result = create_access_token({"sub": "user123"})
    assert isinstance(result, str)

# Mocking user objects with MagicMock
def test_admin_user_passes_check(self):
    admin_user = MagicMock()
    admin_user.is_admin = True
    # ... test admin check

# Fixture-based mock objects (conftest.py)
@pytest.fixture
def mock_user():
    from unittest.mock import MagicMock
    user = MagicMock()
    user.id = "test-user-id-123"
    # ...
    return user
```

**What to Mock:**
- `settings`: All service-level unit tests that touch config patch `fgc_core.{module}.settings` (the module-level singleton)
- External dependencies: `MagicMock` for user/project objects instead of using the database
- Filesystem: `tmp_path` fixture used instead of mocking path operations

**What NOT to Mock:**
- Pydantic model validation: tested directly without mocking
- Internal functions (e.g., `decode_token` in dependencies tests): called directly
- The `gdm_service` singleton: no unit tests exist for `gdm_service.py` or its dependents

## Fixtures and Factories

**Test Data:**
- Shared fixtures in `tests/conftest.py`:
```python
@pytest.fixture
def sample_zip_content():
    import io
    import zipfile
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test_system.json", '{"name": "Test System", ...}')
    buffer.seek(0)
    return buffer.read()

@pytest.fixture
def mock_user():
    from unittest.mock import MagicMock
    user = MagicMock()
    user.id = "test-user-id-123"
    user.email = "test@example.com"
    user.username = "testuser"
    user.is_active = True
    user.is_admin = False
    return user

@pytest.fixture
def mock_admin_user():
    # Similar to mock_user but is_admin=True
```

**Location:**
- `tests/conftest.py` — single file for all shared fixtures
- Inline data constructed per-test using literals or type() for mock objects

## Coverage

**Requirements:** Not enforced. No `pytest-cov` dependency in `pyproject.toml`. No coverage configuration.

**View Coverage:**
```bash
# Would need to install pytest-cov first:
# pip install pytest-cov
# pytest --cov=fgc_core
```
Coverage is not part of the current workflow.

## Test Types

**Unit Tests:**
- Scope: Individual functions and classes in isolation
- What's covered:
  - `auth_service.py`: `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`
  - `config.py`: `Settings` class default values, custom values, path handling
  - `file_service.py`: `handle_zip_upload`, `delete_project_files`, `copy_project_files`
  - `dependencies.py`: Token decode logic, admin user check
  - `schemas/*.py`: Pydantic model construction, validation, optional fields, `model_validate`
- What's NOT covered by unit tests:
  - `gdm_service.py` (GDMService class — no tests at all)
  - `database.py` (init_db, get_db)
  - Router endpoints (`routers/*.py`)
  - `main.py` (app factory, lifespan, health check)

**Integration Tests:**
- Not used. No database integration tests, no HTTP client tests (no `httpx` or `TestClient` usage).

**E2E Tests:**
- Not used.

## Common Patterns

**Async Testing:**
```python
# No async fixtures or async tests used yet
# For testing async dependencies like get_admin_user:
import asyncio

def test_admin_user_passes_check(self):
    admin_user = MagicMock()
    admin_user.is_admin = True

    from fgc_core.dependencies import get_admin_user

    async def run_test():
        result = await get_admin_user(admin_user)
        return result

    result = asyncio.get_event_loop().run_until_complete(run_test())
    assert result.is_admin is True
```
Note: Despite `pytest-asyncio` being a dependency, no tests use `@pytest.mark.asyncio`. Async functions are tested by manually running the event loop with `asyncio.get_event_loop().run_until_complete()`.

**Error Testing:**
```python
# For expected exceptions:
with pytest.raises(ValueError, match="not a valid zip"):
    handle_zip_upload(b"not a zip file", "test.zip", "user123")

# For Pydantic ValidationError:
with pytest.raises(ValidationError):
    LoginRequest(password="password123")

# For HTTPException:
with pytest.raises(HTTPException) as exc_info:
    await get_admin_user(regular_user)
assert exc_info.status_code == 403
```

**Model Validation Testing:**
```python
# Testing model_validate with mock objects (duck-typing)
def test_user_response_from_attributes(self):
    mock_user = type("MockUser", (), {
        "id": "user-456",
        "email": "admin@example.com",
        # ...
    })()
    resp = UserResponse.model_validate(mock_user)
    assert resp.id == "user-456"
```

## Test Gaps Summary

| Area | Test Status |
|------|-------------|
| `auth_service.py` | Well tested — all functions covered |
| `config.py` | Well tested — Settings class covered |
| `file_service.py` | Well tested — all three functions covered |
| `dependencies.py` | Partially tested — `get_admin_user` covered, `get_current_user` not tested |
| `schemas/*.py` | Well tested — all request/response models covered |
| `gdm_service.py` | **No tests** (554 lines of critical logic) |
| `database.py` | **No tests** |
| `routers/*.py` | **No tests** (no TestClient usage) |
| `main.py` | **No tests** |
| Frontend `.ts`/`.vue` | **No tests** (no test framework installed) |

---

*Testing analysis: 2026-05-22*
