# Plan 01-02 Summary: Database Setup

## Objective

Set up the async SQLAlchemy database layer with WAL armor on both the shared auth DB (fgc_core) and the separate jobs DB (fgc_flow_api).

## Deliverables

- **database.py** — `JobsBase` declarative base, `jobs_engine` with WAL armor, `get_jobs_db` dependency, `init_jobs_db` lifecycle
- **models/__init__.py** — re-exports `User` from `fgc_core.models.user`
- **fgc_core/database.py** — added WAL PRAGMAs (journal_mode=WAL, busy_timeout=5000, synchronous=NORMAL, foreign_keys=ON) via event listener

## Verification

- `jobs_engine`, `JobsBase`, `get_jobs_db`, `init_jobs_db` all importable ✓
- `User` importable from `fgc_flow_api.models` ✓
- fgc_core's database.py has `from sqlalchemy import event` + 4 PRAGMAs ✓
- Jobs DB config uses `jobs_database_url` (separate from shared auth DB) ✓

## Next

Plan 01-03: Auth integration — zero-duplication auth endpoints importing from fgc_core
