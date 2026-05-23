# FGC Flow API

## What This Is

A rich FastAPI backend package (`fgc_flow_api`) for the FGC-Flow power flow analysis library. Provides RESTful access to power flow simulation (AC OPF, DC OPF, LinDistFlow), distribution system model management, and result export capabilities — all with the same authentication system as the parent FGC Studio (bcrypt + JWT, shared user database). Lives in the fgc-studio workspace as `backend/packages/fgc_flow_api/`.

## Core Value

Users can run power flow simulations, manage models, and export results via a well-documented REST API — authenticated through the same credentials they already have for FGC Studio.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **AUTH-01**: User can register and login with email/password (reuses fgc_core auth)
- [ ] **AUTH-02**: Token-based auth (access + refresh tokens) identical to fgc_studio
- [ ] **AUTH-03**: Protected endpoints require valid JWT
- [ ] **SIM-01**: User can run AC OPF simulation via API
- [ ] **SIM-02**: User can run DC OPF simulation via API
- [ ] **SIM-03**: User can run LinDistFlow simulation via API
- [ ] **SIM-04**: User can configure solver parameters per run
- [ ] **SIM-05**: User can submit batch/comparison runs (all solvers)
- [ ] **SIM-06**: Job queue with status polling for async execution
- [ ] **MOD-01**: User can upload GDM distribution system models
- [ ] **MOD-02**: User can list and inspect uploaded models
- [ ] **MOD-03**: Models stored in database with version history
- [ ] **EXP-01**: User can trigger SQLite export of results
- [ ] **EXP-02**: User can download result files
- [ ] **EXP-03**: User can export results as CSV/JSON

### Out of Scope

- Real-time simulation streaming — batch/async is sufficient for v1
- WebSocket notifications for job completion — polling-based status is fine
- Frontend UI — this is a backend-only package; frontend integration comes later

## Context

- **Existing codebase**: fgc_studio at this workspace root has an fgc_core package (`backend/packages/fgc_core/`) with auth (bcrypt, JWT, SQLAlchemy async, SQLite) and a separate `backend/app/` with duplicated code
- **Existing fgc-flow**: Lives at `~/Documents/github/fgc-flow/` with CLI-based power flow solvers (AC OPF, DC OPF, LinDistFlow), model export, and an MCP server
- **Key concern from codebase map**: `backend/app/` and `backend/packages/fgc_core/` have near-identical code (~3,500 lines each) — the new package must NOT duplicate; it should import from fgc_core
- **The new package will**: Depend on `fgc_core` for auth/config/database, and depend on `fgc-flow` (the pip package) for simulation logic

## Constraints

- **Tech stack**: FastAPI, SQLAlchemy async, aiosqlite (same as fgc_core)
- **Auth**: Must share user database with fgc_core (same SQLite DB, same users table)
- **Auth patterns**: Must use bcrypt for passwords, python-jose for JWT (access + refresh tokens), OAuth2PasswordBearer for dependency injection
- **Location**: `backend/packages/fgc_flow_api/` in the fgc-studio workspace
- **Package name**: `fgc-flow-api`
- **Dependency on fgc_core**: Must import from fgc_core, not duplicate
- **Dependency on fgc-flow**: The `fgc-flow` pip package from `~/Documents/github/fgc-flow`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Standalone package depending on fgc_core | Avoid duplicating auth code; fgc_core already has auth/config/database | — Pending |
| Lives in fgc-studio workspace | Co-located with fgc_core for easy import and monorepo management | — Pending |
| SQLite shared DB with fgc_core | Simplest setup; consistent with existing pattern; users share auth | — Pending |
| Job queue for simulations | Power flow runs can be long; async prevents timeout | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-22 after initialization*
