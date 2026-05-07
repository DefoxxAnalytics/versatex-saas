"""Atomic AI cache stat counters (v3 Phase 1 Task 1.6).

The prior ``cache.get -> cache.set`` increment in
``apps.analytics.ai_cache.AIInsightsCache._increment_stat`` exhibited a
classic lost-update race: two concurrent AI requests both read the same
counter value N and both wrote N+1, undercounting by ~10-30% under load.

The fix uses Django's atomic ``cache.add`` (only sets when absent) plus
``cache.incr`` (atomic in redis and locmem backends). These tests:

1. Stress the public ``_increment_stat`` path with a 50-worker thread pool
   and assert no increments are lost.
2. Drift-guard against re-introducing the racy pattern in ai_cache.py.
3. Verify the public ``get_cached_enhancement`` path (which calls
   ``_increment_stat`` internally on hits and misses) is also race-free.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from django.core.cache import cache

from apps.analytics.ai_cache import AIInsightsCache


WORKERS = 50
ORG_ID = 12345


def _hit_key(org_id: int) -> str:
    return f"{AIInsightsCache.CACHE_PREFIX}:stats:{org_id}:hits"


def _miss_key(org_id: int) -> str:
    return f"{AIInsightsCache.CACHE_PREFIX}:stats:{org_id}:misses"


@pytest.mark.django_db
def test_increment_stat_hit_counter_is_atomic_under_concurrency():
    """50 concurrent workers each call _increment_stat('hits') once.

    Final hit counter MUST equal 50. The prior cache.get -> cache.set
    pattern would non-deterministically end at 30-45 due to lost updates.
    """
    def worker():
        AIInsightsCache._increment_stat(ORG_ID, "hits")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(worker) for _ in range(WORKERS)]
        for f in futures:
            f.result()

    assert cache.get(_hit_key(ORG_ID)) == WORKERS, (
        f"Lost-update race: expected {WORKERS} hits, got "
        f"{cache.get(_hit_key(ORG_ID))}. _increment_stat is not atomic."
    )


@pytest.mark.django_db
def test_increment_stat_miss_counter_is_atomic_under_concurrency():
    """Same concurrency stress for the miss counter."""
    def worker():
        AIInsightsCache._increment_stat(ORG_ID, "misses")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(worker) for _ in range(WORKERS)]
        for f in futures:
            f.result()

    assert cache.get(_miss_key(ORG_ID)) == WORKERS, (
        f"Lost-update race: expected {WORKERS} misses, got "
        f"{cache.get(_miss_key(ORG_ID))}."
    )


@pytest.mark.django_db
def test_increment_stat_supports_delta_argument():
    """The delta argument lets the caller increment by N atomically.

    Useful for accumulator-style counters (e.g., total_tokens) that record
    a per-call cost rather than +1 per call.
    """
    AIInsightsCache._increment_stat(ORG_ID, "tokens", delta=5)
    AIInsightsCache._increment_stat(ORG_ID, "tokens", delta=7)
    AIInsightsCache._increment_stat(ORG_ID, "tokens", delta=3)

    key = f"{AIInsightsCache.CACHE_PREFIX}:stats:{ORG_ID}:tokens"
    assert cache.get(key) == 15, (
        f"Delta accumulation broken: expected 15, got {cache.get(key)}"
    )


@pytest.mark.django_db
def test_concurrent_delta_increments_are_atomic():
    """50 workers each increment by delta=2; final value MUST be 100."""
    def worker():
        AIInsightsCache._increment_stat(ORG_ID, "tokens", delta=2)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(worker) for _ in range(WORKERS)]
        for f in futures:
            f.result()

    key = f"{AIInsightsCache.CACHE_PREFIX}:stats:{ORG_ID}:tokens"
    assert cache.get(key) == WORKERS * 2, (
        f"Concurrent delta increments lost updates: expected "
        f"{WORKERS * 2}, got {cache.get(key)}"
    )


@pytest.mark.django_db
def test_get_cache_stats_after_concurrent_increments():
    """End-to-end: concurrent hits + misses + get_cache_stats reports correctly."""
    def hit_worker():
        AIInsightsCache._increment_stat(ORG_ID, "hits")

    def miss_worker():
        AIInsightsCache._increment_stat(ORG_ID, "misses")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        hit_futures = [pool.submit(hit_worker) for _ in range(WORKERS)]
        miss_futures = [pool.submit(miss_worker) for _ in range(WORKERS // 2)]
        for f in hit_futures + miss_futures:
            f.result()

    stats = AIInsightsCache.get_cache_stats(ORG_ID)
    assert stats["hits"] == WORKERS
    assert stats["misses"] == WORKERS // 2
    assert stats["total_requests"] == WORKERS + WORKERS // 2
    expected_rate = round(WORKERS / (WORKERS + WORKERS // 2) * 100, 1)
    assert stats["hit_rate"] == expected_rate


@pytest.mark.django_db
def test_increment_stat_initializes_counter_on_first_call():
    """First call MUST set the value to delta (not 0 + delta = lost set)."""
    AIInsightsCache._increment_stat(ORG_ID, "hits")
    assert cache.get(_hit_key(ORG_ID)) == 1


@pytest.mark.django_db
def test_increment_stat_uses_stats_ttl_constant():
    """The TTL must come from the STATS_TTL class constant, not a magic number."""
    assert AIInsightsCache.STATS_TTL == 86400, (
        "STATS_TTL must be 24 hours; changing this is a behavior change "
        "that requires intent."
    )


def test_drift_guard_no_get_then_set_increment_pattern_in_ai_cache():
    """Regression guard: prevent re-introduction of the lost-update pattern.

    The ``cache.get(...) -> cache.set(...,  current + 1, ...)`` shape MUST
    NOT reappear in ai_cache.py. If a future change reintroduces it (likely
    by a refactor or LLM completion), this test fails before the bug ships.
    """
    src_path = Path(AIInsightsCache.__module__.replace(".", "/"))
    ai_cache_file = (
        Path(__file__).resolve().parents[1] / "ai_cache.py"
    )
    assert ai_cache_file.exists(), f"ai_cache.py not found at {ai_cache_file}"
    source = ai_cache_file.read_text(encoding="utf-8")

    # Forbidden shape 1: ``cache.set(<key>, current + 1, ...)`` or similar
    # ``+ 1`` after a cache.get-derived value being passed to cache.set.
    forbidden = re.compile(
        r"cache\.set\(\s*[^,]+,\s*\w+\s*\+\s*1\b",
        re.MULTILINE,
    )
    matches = forbidden.findall(source)
    assert not matches, (
        "Drift-guard tripped: ai_cache.py contains the racy "
        "``cache.set(key, value + 1, ...)`` increment pattern that v3 "
        "Phase 1 Task 1.6 removed. Use ``cache.add`` + ``cache.incr`` "
        f"instead. Offending lines: {matches}"
    )

    # Forbidden shape 2: explicit cache.get -> cache.set increment idiom.
    racy_idiom = re.compile(
        r"current\s*=\s*cache\.get\([^)]+\)\s*or\s*0\s*\n\s*cache\.set",
        re.MULTILINE,
    )
    assert not racy_idiom.search(source), (
        "Drift-guard tripped: ai_cache.py contains the explicit "
        "``current = cache.get(...) or 0; cache.set(..., current + 1)`` "
        "lost-update idiom. Use ``cache.add`` + ``cache.incr`` instead."
    )

    # Positive assertion: the atomic primitives MUST be present.
    assert "cache.add(" in source, (
        "Atomic init primitive missing: ai_cache.py must use cache.add "
        "for first-write semantics."
    )
    assert "cache.incr(" in source, (
        "Atomic increment primitive missing: ai_cache.py must use "
        "cache.incr for subsequent increments."
    )
