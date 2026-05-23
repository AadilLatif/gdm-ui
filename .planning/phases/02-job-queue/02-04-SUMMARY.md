# Plan 02-04 Summary: Retry + Cache Wiring

## Objective

Added deterministic cache-keying and fixed retry policy wiring for the job queue.

## Deliverables

- `services/job_cache.py` with canonical SHA-256 cache keys and SQLite lookups
- `services/job_retry.py` with fixed 3-attempt retry policy
- `services/__init__.py` exports cache/retry helpers
- `main.py` includes the jobs router
- `tests/test_job_cache_retry.py` locks the behavior

## Verification

- `pytest tests/test_job_cache_retry.py -q` passes ✓
- Cache keys are canonical for sorted params ✓
- Retry stops after three attempts ✓
- Jobs router is mounted in the app ✓

## Next

Phase 2 verification and phase handoff
