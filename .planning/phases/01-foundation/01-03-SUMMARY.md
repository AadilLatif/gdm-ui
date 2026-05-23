# Plan 01-03 Summary: Auth Integration

## Objective

Wire up authentication for fgc_flow_api by importing and re-using fgc_core's auth system — no code duplication.

## Deliverables

- **dependencies.py** — re-exports `get_current_user`, `get_admin_user` from fgc_core
- **schemas/auth.py** — re-exports `RegisterRequest`, `LoginRequest`, `TokenResponse`, `RefreshRequest` from fgc_core
- **routers/auth.py** — 4 endpoints: register, login, refresh, get_me
- **routers/__init__.py** — exports `auth_router`
- **schemas/__init__.py** — exports all auth schemas

## Verification

- `get_current_user`, `get_admin_user` importable ✓
- `auth_router` has 4 routes (register, login, refresh, me) ✓
- Zero auth code duplication — no `import jose` or `import bcrypt` ✓
- All auth logic imported from fgc_core ✓

## Next

Plan 01-04: FastAPI app with lifespan, CORS, health check, global exception handlers
