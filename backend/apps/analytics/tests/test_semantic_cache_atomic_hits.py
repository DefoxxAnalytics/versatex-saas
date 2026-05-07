"""Atomic SemanticCache.hit_count counter (v3 Phase 3 Task 3.7).

The prior ``self.hit_count += 1; self.save(update_fields=['hit_count'])`` in
``apps.analytics.models.SemanticCache.increment_hit_count`` was the ORM
analog of the ``cache.get -> cache.set`` lost-update race that v3 Phase 1
Task 1.6 fixed in ai_cache.py: two concurrent ``SemanticCacheService.lookup``
calls hitting the same cached entry would each read N from Python memory,
both write N+1, undercounting hits.

The fix uses ``F('hit_count') + 1`` inside ``UPDATE``, pushing the
increment into the database where row-level locking serializes concurrent
updates. These tests:

1. Verify functional correctness: 50 sequential increments produce 50.
2. Verify the in-memory ``self.hit_count`` reflects the new value (the
   service code immediately consumes the entry, so callers must see fresh
   state).
3. Drift-guard: regex-grep the model source to prevent reintroduction of
   the racy ``self.hit_count += 1; self.save()`` pattern.
4. Verify the fix uses ``F()`` expressions (positive assertion).

Note: Postgres-level concurrency cannot be exercised on the SQLite test
DB (CI Postgres exercises the row-level locking semantics in production).
The drift-guard regex catches any future regression at static-analysis
time, which is what matters for preventing the bug from shipping.
"""

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

import pytest
from django.utils import timezone

from apps.analytics.models import SemanticCache


@pytest.fixture
def cache_entry(db, organization):
    """Create a SemanticCache entry with hit_count=0."""
    return SemanticCache.objects.create(
        organization=organization,
        request_type="enhance",
        query_text="test query",
        query_hash="a" * 64,
        response_json={"result": "cached"},
        expires_at=timezone.now() + timedelta(hours=1),
    )


@pytest.mark.django_db
def test_increment_hit_count_advances_by_one(cache_entry):
    """Single increment moves hit_count from 0 -> 1."""
    assert cache_entry.hit_count == 0
    cache_entry.increment_hit_count()
    assert cache_entry.hit_count == 1


@pytest.mark.django_db
def test_increment_hit_count_refreshes_in_memory_value(cache_entry):
    """After increment, the in-memory instance MUST reflect the DB value.

    SemanticCacheService.lookup calls increment_hit_count() then immediately
    returns ``entry.response_json`` — but downstream callers reading
    ``entry.hit_count`` (e.g., logging, metrics) must see the fresh count,
    not a stale 0.
    """
    cache_entry.increment_hit_count()
    cache_entry.increment_hit_count()
    cache_entry.increment_hit_count()

    assert cache_entry.hit_count == 3, (
        "increment_hit_count must refresh self.hit_count from the DB so "
        "callers observe the new value without a manual refresh_from_db()."
    )


@pytest.mark.django_db
def test_50_sequential_increments_produce_50(cache_entry):
    """50 sequential calls produce hit_count=50.

    The prior ``self.hit_count += 1; self.save()`` pattern was correct
    sequentially — the bug only manifested under concurrent ORM access.
    This test guards against an over-zealous "fix" that breaks the
    sequential happy path (e.g., F() expression that doesn't refresh).
    """
    for _ in range(50):
        cache_entry.increment_hit_count()

    cache_entry.refresh_from_db()
    assert cache_entry.hit_count == 50


@pytest.mark.django_db
def test_increment_hit_count_does_not_clobber_other_fields(cache_entry):
    """The ``UPDATE ... SET hit_count = hit_count + 1`` must not touch
    other columns. If a concurrent process modifies ``response_json``
    between our load and increment, that modification must survive.
    """
    SemanticCache.objects.filter(pk=cache_entry.pk).update(
        response_json={"updated_by_other_process": True}
    )

    cache_entry.increment_hit_count()

    cache_entry.refresh_from_db()
    assert cache_entry.response_json == {"updated_by_other_process": True}, (
        "increment_hit_count must scope its UPDATE to hit_count only, "
        "preserving concurrent modifications to other columns."
    )
    assert cache_entry.hit_count == 1


def test_drift_guard_no_read_modify_write_increment_in_models():
    """Regression guard: prevent re-introduction of the lost-update pattern.

    The ``self.hit_count += N; self.save(update_fields=['hit_count'])``
    shape MUST NOT reappear in models.py for SemanticCache. If a future
    refactor reintroduces it, this test fails before the bug ships.
    """
    models_file = Path(__file__).resolve().parents[1] / "models.py"
    assert models_file.exists(), f"models.py not found at {models_file}"
    source = models_file.read_text(encoding="utf-8")

    racy_idiom = re.compile(
        r"self\.hit_count\s*\+=\s*\d+\s*\n\s*self\.save\(",
        re.MULTILINE,
    )
    assert not racy_idiom.search(source), (
        "Drift-guard tripped: models.py contains the racy "
        "``self.hit_count += N; self.save(...)`` read-modify-write idiom "
        "that v3 Phase 3 Task 3.7 removed. Use ``F('hit_count') + N`` "
        "inside an ``UPDATE`` instead."
    )

    assert "F('hit_count')" in source, (
        "Atomic increment primitive missing: models.py must use "
        "``F('hit_count') + ...`` for concurrent-safe hit counting."
    )

    assert "from django.db.models import F" in source, (
        "F() must be imported at module scope so the increment expression "
        "resolves correctly."
    )
