from __future__ import annotations

from types import SimpleNamespace

from fgc_flow_api.services import MAX_RETRIES, build_cache_key, schedule_retry, should_retry


def test_cache_key_is_canonical():
    a = build_cache_key("v1", {"b": 2, "a": 1})
    b = build_cache_key("v1", {"a": 1, "b": 2})
    assert a == b


def test_retry_caps_at_three():
    job = SimpleNamespace(retry_count=2)
    assert should_retry(job) is True
    job.retry_count = MAX_RETRIES
    assert should_retry(job) is False


def test_retry_schedule_exists_before_cap():
    job = SimpleNamespace(retry_count=1)
    assert schedule_retry(job) is not None
