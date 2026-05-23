# Feature Landscape: Power Flow / Grid Simulation REST API

**Domain:** Power flow analysis REST API backend
**Researched:** 2026-05-22
**Overall confidence:** HIGH

## Overview

The feature landscape is drawn from three sources:
1. **Existing `fgc-flow` library** — AC OPF, DC OPF, LinDistFlow, Y-bus builder, SQLite export, MCP server (11 tools)
2. **Existing `fgc-studio` backend** — auth, projects, scenarios, system, equipment, network routers
3. **Industry APIs** — OpenDSS wrappers, GridAPPS-D, PyDSS, LF Power Grid Model, Siemens PSS/E, ETAP, PowerWorld

---

## Table Stakes (must-have or users leave)

Features that any credible power flow API must expose. Missing these = product feels incomplete.

### Simulation Endpoints

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| 1 | **Run AC OPF** (`POST /simulations/ac-opf`) | Medium | Primary solver — nonlinear, handles voltage/reactive power. Core use case. Already exists in fgc-flow as `optimize_ac_power_flow`. |
| 2 | **Run DC OPF** (`POST /simulations/dc-opf`) | Medium | Linear approximation for active-power-only studies. Standard companion to AC. Exists as `solve_dc_opf`. |
| 3 | **Run LinDistFlow** (`POST /simulations/lindistflow`) | Medium | Radial distribution approximation. Exists as `solve_lindistflow`. |
| 4 | **Configure solver parameters per run** | Low | Voltage bounds, max iterations, convergence tolerance, load/solar/battery scale factors. Already exists in fgc-flow function signatures. |
| 5 | **Return simulation result synchronously** | Low | Small models (<500 buses) solve in <1s. Should return inline for fast feedback. Standard REST pattern. |
| 6 | **Return convergence status** | Low | `success: bool`, `message: str`, `iterations: int`. Already in all result dataclasses. |

### Model Management

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| 7 | **Upload a distribution system model** (`POST /models/upload`) | Medium | Users need to push GDM JSON models. Existing fgc-studio has project upload; must extend for distribution models. |
| 8 | **List uploaded models** (`GET /models`) | Low | Standard CRUD. Filter by user, date, name. |
| 9 | **Inspect a model's metadata** (`GET /models/{id}`) | Low | Return bus count, branch count, voltage levels, source bus. |
| 10 | **Download original model file** (`GET /models/{id}/download`) | Low | Round-trip fidelity. Users need to retrieve what they uploaded. |
| 11 | **Delete a model** (`DELETE /models/{id}`) | Low | Standard CRUD. Cascade to simulations. |

### Auth & User Management

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| 12 | **Register / Login** | Low (reuse fgc_core) | Shared user DB with fgc-studio. Already in fgc_core. |
| 13 | **JWT token auth** | Low (reuse fgc_core) | Access + refresh tokens, OAuth2PasswordBearer. Existing pattern. |
| 14 | **Protect all simulation/model endpoints** | Low | Every endpoint behind `get_current_user`. |

### Job & Async Basics

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| 15 | **Submit long-running simulation as job** (`POST /jobs`) | Medium | Required for models >2000 buses where solve time exceeds typical HTTP timeout (30s). |
| 16 | **Poll job status** (`GET /jobs/{id}`) | Low | Return `pending/running/completed/failed` with timestamps. |
| 17 | **List user's jobs** (`GET /jobs`) | Low | Standard. Filter by status, date range. |

### Export Basics

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| 18 | **Download results as JSON** (`GET /results/{id}`) | Low | Most universal format. Every API tool can consume JSON. |
| 19 | **Download results as CSV** (`GET /results/{id}/export/csv`) | Low | Standard for spreadsheet analysis. |
| 20 | **Trigger SQLite export** (`POST /results/{id}/export/sqlite`) | Medium | Needed for large results. fgc-flow already has `export_all_results_to_sqlite`. |

### API Usability

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| 21 | **OpenAPI / Swagger docs** | Low | FastAPI auto-generates. Non-negotiable for developer adoption. |
| 22 | **Standard error format** | Low | Consistent `{ "detail": "...", "code": "...", "status": 400 }` everywhere. |
| 23 | **Pagination on list endpoints** | Low | `?offset=0&limit=100`. Standard REST. |

---

## Differentiators (competitive advantage)

Features that go beyond "yet another solver wrapper." These create real value.

### Solver Comparison & Batch

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| D1 | **Compare all solvers on one model** (`POST /simulations/compare`) | Medium | Run AC OPF + DC OPF + LinDistFlow in a single request, return side-by-side comparison. The MCP server already has `opf_compare_solvers`. No other public API wraps this. **Key differentiator.** |
| D2 | **Batch model sweep** (`POST /simulations/batch`) | High | Run the same solver config against N uploaded models. Compare results across feeders. Useful for utilities validating a control strategy across their entire territory. |
| D3 | **Batch parameter sweep** (`POST /simulations/sweep`) | High | Vary one parameter (load scale, solar penetration) across a range and run solver each time. Generate sensitivity curves. |

### Rich Results & Analysis

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| D4 | **Result snapshots at model-level granularity** | Medium | Return bus voltages, branch flows, power injections as JSON — not just summary numbers. fgc-flow already computes all of this (`voltage`, `power_injection`, `p_flow_w`). Most APIs only return summary. |
| D5 | **Voltage violation report** | Low | Scan result for buses outside `[0.95, 1.05]` pu and return a structured violation list. Simple post-processing on existing data. |
| D6 | **Line overload report** | Low | Check branch flows against ratings. |
| D7 | **Result diff between solvers** | Medium | Compare AC vs LinDistFlow voltage profiles and return RMSE, max error, error locations. Which buses diverge most? |

### Model Introspection

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| D8 | **Y-bus matrix inspection** (`GET /models/{id}/ybus`) | Low | fgc-flow already has `calculate_ybus`. Expose sparsity pattern, nonzero count, optional preview. No other power flow API does this. |
| D9 | **Model summary statistics** (`GET /models/{id}/stats`) | Low | Bus count, branch count by type, total load kW/kvar, total solar kW, voltage level distribution. |
| D10 | **Model version history** (`GET /models/{id}/versions`) | Medium | Track uploads of same model name. Users iterate on models; versions let them compare old vs new. |

### Export Power Features

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| D11 | **Export multiple result formats in one call** | Medium | Request JSON + CSV + SQLite in a single POST; API stages all and returns download links. |
| D12 | **Export comparison results** | Medium | Export the comparison table (D1) as a structured report. |
| D13 | **Result inline vs. download choice** | Low | `?format=json` returns inline, `?format=csv` triggers download. User choice per request. |

### Developer Experience

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| D14 | **cURL / Postman collection in docs** | Low | One-time effort to provide ready-to-run examples. Lowers adoption friction. |
| D15 | **Run examples with built-in IEEE test feeders** | Low | Preload IEEE 13, 34, 37, 123-bus models so users can test without uploading. |
| D16 | **API key access** (alternative to JWT) | Low | For programmatic clients (CI/CD, scripts). Simple bearer token tied to user account. |

### Async / Job Enhancements

| # | Feature | Complexity | Rationale |
|---|---------|------------|-----------|
| D17 | **Webhook on job completion** | Medium | `POST /jobs/{id}/webhook` — API calls back a user-specified URL when job finishes. Eliminates polling. |
| D18 | **Job result retention policy** | Low | Configurable TTL per user; auto-cleanup expired results. |
| D19 | **Cancel running job** (`POST /jobs/{id}/cancel`) | Medium | Signal the background worker to abort. Hard to implement cleanly with subprocess-based simulators, but valuable. |

---

## Anti-Features (deliberately NOT building)

| # | What | Why Avoid | Instead Do |
|---|------|-----------|------------|
| A1 | **Real-time simulation streaming** | fg-flow solvers are steady-state, not dynamic. Real-time would require a fundamentally different engine (e.g., OpenDSS dynamics mode, GridLAB-D). Out of scope per PROJECT.md. | Batch/async is sufficient for v1. Add as a separate `fgc-dynamic` package later if needed. |
| A2 | **WebSocket push for job completion** | Adds complexity — client must maintain persistent connection, server needs WS infrastructure. | Polling-based status (`GET /jobs/{id}`) works fine. Add webhook (D17) before WebSocket. |
| A3 | **Multi-user real-time collaboration** | Requires operational transforms, conflict resolution, presence awareness. Not valuable for simulation API. | Each user has their own models and runs. No shared editing. |
| A4 | **Full CIM/CGMES import/export** | CIM is a massive standard (IEC 61968/61970). Would require a separate import pipeline. fgc-flow works with GDM JSON natively. | Accept GDM JSON only. If CIM support is needed, build a `fgc-cim-bridge` as a separate project. |
| A5 | **Graphical topology viewer** | Frontend concern. This is a backend API package. | Return structured topology data (`GET /models/{id}/topology`); let frontend render. |
| A6 | **Time-series / quasi-static simulation** | Requires sequential solve loops with load shape profiles. fgc-flow doesn't have this. Out of scope. | Snapshot power flow only. Time-series is a different product. |
| A7 | **Short-circuit / fault analysis** | Requires a different solver (fault current calculation). fgc-flow is OPF-focused. | Y-bus endpoint (D8) provides foundation if someone wants to build fault analysis on top. |
| A8 | **Dynamic simulation / transient stability** | Entirely different engine. fgc-flow is steady-state. | Not in scope. Refer to commercial tools (PSS/E, PowerWorld) for this. |
| A9 | **Market simulation / economic dispatch** | Outside distribution OPF scope. Grid-scale economic dispatch is a separate domain. | DC OPF gives locational marginal prices as a byproduct — can be exposed without building a market simulator. |

---

## Feature Dependencies

```
Auth (AUTH-01/02/03)
  └── Everything (no feature works without auth)

Model Management (MOD-01/02/03)
  └── Upload (POST /models/upload)
  │     └── List (GET /models)
  │     └── Inspect (GET /models/{id})
  │     └── Download (GET /models/{id}/download)
  │     └── Delete (DELETE /models/{id})
  │     └── Y-bus (GET /models/{id}/ybus) [D8]
  │     └── Stats (GET /models/{id}/stats) [D9]
  │     └── Versions (GET /models/{id}/versions) [D10]
  │
  └── Simulation Endpoints (all require an uploaded model)
        └── Run AC OPF (POST /simulations/ac-opf)
        └── Run DC OPF (POST /simulations/dc-opf)
        └── Run LinDistFlow (POST /simulations/lindistflow)
        │     └── Compare solvers (POST /simulations/compare) [D1]
        │     └── Batch sweep (POST /simulations/batch) [D2]
        │     └── Parameter sweep (POST /simulations/sweep) [D3]
        │
        └── Results
              └── Get result (GET /results/{id})
              │     └── Voltage violation report [D5]
              │     └── Line overload report [D6]
              │     └── Solver diff report [D7]
              │
              └── Export (all require completed result)
                    └── JSON (GET /results/{id}/export/json)
                    └── CSV (GET /results/{id}/export/csv)
                    └── SQLite (POST /results/{id}/export/sqlite)

Job Queue
  └── Submit job (POST /jobs)
  │     └── Depends on: simulation endpoints
  │
  └── Poll status (GET /jobs/{id})
  └── List jobs (GET /jobs)
  └── Cancel job (POST /jobs/{id}/cancel) [D19]
  └── Set webhook (POST /jobs/{id}/webhook) [D17]
```

**Key dependency insight:** The job queue is orthogonal to the simulation logic — same simulation code runs in both sync (inline) and async (job) modes. Wrap the solver call in a conditional: if runtime estimate > threshold, auto-promote to async.

---

## What Already Exists in fgc-flow

| fgc-flow Function | REST Endpoint Mapping | Status |
|-------------------|----------------------|--------|
| `optimize_ac_power_flow` | `POST /simulations/ac-opf` | Library exists; needs REST wrapper |
| `solve_dc_opf` | `POST /simulations/dc-opf` | Library exists; needs REST wrapper |
| `solve_lindistflow` | `POST /simulations/lindistflow` | Library exists; needs REST wrapper |
| `calculate_ybus` | `GET /models/{id}/ybus` [D8] | Library exists; needs REST wrapper |
| `export_all_results_to_sqlite` | `POST /results/{id}/export/sqlite` | Library exists; needs REST wrapper |
| `opf_compare_solvers` (MCP) | `POST /simulations/compare` [D1] | Partially in MCP; needs REST mirror |
| `build_nodal_power_specs_from_components` | Internal to solver endpoints | Already used by solver functions |

---

## What Must Be Built from Scratch

| Feature | Why No Existing Code |
|---------|---------------------|
| Model upload / storage / versioning | fgc-flow works with local file paths; REST API needs DB-backed storage |
| Job queue with status polling | fgc-flow is synchronous; no async infrastructure |
| Auth integration (JWT per request) | fgc-flow has no auth; depends on fgc_core |
| Result storage and retrieval | fgc-flow returns Python objects; need persistence layer |
| CSV export | fgc-flow only has SQLite export |
| Voltage/overload violation report | Not in fgc-flow; simple post-processing |
| Webhook on completion | Infrastructure concern, not in fgc-flow |
| IEEE test feeder seeding | Data + seed script; not in fgc-flow |

---

## Complexity Summary for Roadmap

| Phase | Features | Complexity | Reason |
|-------|----------|------------|--------|
| **Phase 1: Core Simulation** | 1–6 (AC, DC, LinDistFlow, sync results) | Medium | Thin REST wrapper over existing fgc-flow solvers; auth from fgc_core |
| **Phase 2: Model Management** | 7–11 (upload, list, inspect, download, delete) | Medium | DB schema design; file storage; GDM JSON parsing |
| **Phase 3: Async & Results** | 15–20 (job queue, polling, JSON/CSV/SQLite export) | Medium-High | Background task infrastructure; result persistence; export pipelines |
| **Phase 4: Differentiators** | D1–D19 (compare, batch, violations, webhooks, Y-bus, stats) | Medium | Mostly reuse existing fgc-flow logic; some new endpoints |

---

## Sources

- fgc-flow source code (`~/Documents/github/fgc-flow/src/fgc_flow/`) — HIGH confidence
- fgc-flow MCP tool reference (`docs/mcp/tool_reference.md`) — HIGH confidence
- fgc-studio backend routers (`backend/app/routers/`) — HIGH confidence
- PROJECT.md requirements — HIGH confidence
- OpenDSS DEG Simulation API Wrapper (`github.com/iris-eldo/OpenDSS_DEG_Simulation_API_Wrapper`) — MEDIUM confidence (single project, small community)
- PyDSS REST API capabilities (`github.com/NREL/PyDSS`) — MEDIUM confidence (docs mention RESTful API)
- GridAPPS-D platform architecture (`gridappsd.readthedocs.io`) — MEDIUM confidence (architecture docs, not specific API surface)
- Siemens PSS/E 2000+ API surface (`siemens.com/pss-software/psse`) — LOW confidence (marketing page, not detailed)
- LF Power Grid Model features (`lfenergy.org/projects/power-grid-model`) — MEDIUM confidence (project docs)
- AWS generator interconnection study with job queue (`aws.amazon.com/blogs/industries/`) — MEDIUM confidence (relevant pattern, different domain)
- Cameo Simulation Toolkit REST API (`docs.nomagic.com`) — LOW confidence (different domain, same async simulation pattern)
