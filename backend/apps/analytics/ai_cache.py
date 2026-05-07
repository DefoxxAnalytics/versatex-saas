"""
AI Insights Caching Layer.

Provides Redis-based caching for AI-enhanced insights to reduce API costs
and improve response times.

Cache Strategy:
- Key: org_id + hash of insight signatures
- TTL: 1 hour default, configurable via AI_INSIGHTS_CACHE_TTL
- Invalidation: On transaction upload, manual refresh
"""

import hashlib
import json
import logging
from typing import Optional

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class AIInsightsCache:
    """
    Caching layer for AI-enhanced insights.

    Reduces external AI API costs by caching enhancement results.
    Cache is invalidated when underlying data changes (uploads, deletes).
    """

    CACHE_PREFIX = "ai_insights"
    DEFAULT_TTL = 3600  # 1 hour
    STATS_TTL = 86400  # 24 hours for stats counters

    @classmethod
    def _get_ttl(cls) -> int:
        """Get cache TTL from settings or use default."""
        return getattr(settings, "AI_INSIGHTS_CACHE_TTL", cls.DEFAULT_TTL)

    @classmethod
    def _generate_cache_key(cls, organization_id: int, insights: list) -> str:
        """
        Generate deterministic cache key from insights data.

        Uses a hash of insight signatures (type, title, savings) to create
        a unique key that changes when the underlying data changes.

        Args:
            organization_id: Organization's primary key
            insights: List of insight dictionaries

        Returns:
            Cache key string in format: ai_insights:{org_id}:{content_hash}
        """
        insight_signatures = [
            f"{i['type']}:{i['title']}:{i.get('potential_savings', 0)}"
            for i in sorted(insights, key=lambda x: x["id"])
        ]
        content_hash = hashlib.sha256(
            json.dumps(insight_signatures).encode()
        ).hexdigest()[:16]

        return f"{cls.CACHE_PREFIX}:{organization_id}:{content_hash}"

    @classmethod
    def _get_org_pattern_key(cls, organization_id: int) -> str:
        """Get the pattern key for tracking org's cache entries."""
        return f"{cls.CACHE_PREFIX}:org_keys:{organization_id}"

    @classmethod
    def get_cached_enhancement(
        cls, organization_id: int, insights: list
    ) -> Optional[dict]:
        """
        Retrieve cached AI enhancement if available.

        Args:
            organization_id: Organization's primary key
            insights: List of base insights to match against

        Returns:
            Cached enhancement dict or None if not found
        """
        cache_key = cls._generate_cache_key(organization_id, insights)
        cached = cache.get(cache_key)

        if cached:
            logger.info(f"AI insights cache HIT for org {organization_id}")
            cls._increment_stat(organization_id, "hits")
            return cached

        logger.info(f"AI insights cache MISS for org {organization_id}")
        cls._increment_stat(organization_id, "misses")
        return None

    @classmethod
    def cache_enhancement(
        cls, organization_id: int, insights: list, enhancement: dict, ttl: int = None
    ) -> None:
        """
        Store AI enhancement in cache.

        Args:
            organization_id: Organization's primary key
            insights: List of base insights (used for key generation)
            enhancement: AI enhancement response to cache
            ttl: Optional custom TTL in seconds
        """
        cache_key = cls._generate_cache_key(organization_id, insights)
        effective_ttl = ttl or cls._get_ttl()

        cache.set(cache_key, enhancement, effective_ttl)

        cls._track_org_key(organization_id, cache_key)

        logger.info(
            f"AI insights cached for org {organization_id}, "
            f"key={cache_key}, TTL={effective_ttl}s"
        )

    @classmethod
    def _track_org_key(cls, organization_id: int, cache_key: str) -> None:
        """Track cache keys by organization for invalidation.

        v3.1 Phase 2 (AN-H5): tries to use the Redis SADD primitive (atomic
        set-add) when the backend exposes it; falls back to a documented
        best-effort list write otherwise. The race the read-modify-write
        path can lose is:
          - Two concurrent cache_enhancement calls both ``cache.get(pattern_key)``
            and see the same list ``[k1, k2]``.
          - First writer appends ``k3`` and ``cache.set([k1, k2, k3])``.
          - Second writer appends ``k4`` and ``cache.set([k1, k2, k4])``.
          - ``k3`` is silently dropped from the tracking set.
        Impact is bounded: the dropped key still has its own TTL (1 hour
        by default) and naturally expires; ``invalidate_org_cache`` may
        miss a single stale entry for at most that TTL window. AI insights
        are non-authoritative and stale-window-tolerant, so SADD is a
        belt-and-suspenders, not a correctness requirement.
        """
        pattern_key = cls._get_org_pattern_key(organization_id)
        ttl = cls._get_ttl() * 2

        # Best path: Redis-backed SADD (atomic). django-redis exposes the
        # raw client via cache.client.get_client() / cache.client. We probe
        # defensively because locmem and database backends don't have it.
        try:
            client = getattr(cache, "client", None)
            if client is not None and hasattr(client, "sadd"):
                # django-redis exposes sadd directly on the client wrapper.
                client.sadd(pattern_key, cache_key)
                client.expire(pattern_key, ttl)
                return
        except Exception:
            # Fall through to the list-based path below.
            pass

        # Fallback: best-effort list write. See docstring for race details.
        existing_keys = cache.get(pattern_key) or []
        if cache_key not in existing_keys:
            existing_keys.append(cache_key)
            cache.set(pattern_key, existing_keys, ttl)

    @classmethod
    def invalidate_org_cache(cls, organization_id: int) -> int:
        """
        Invalidate all AI insights cache entries for an organization.

        Called when underlying data changes (uploads, deletes).

        Args:
            organization_id: Organization's primary key

        Returns:
            Number of cache entries invalidated
        """
        pattern_key = cls._get_org_pattern_key(organization_id)

        # v3.1 Phase 2 (AN-H5): read tracking via SADD's smembers (Redis
        # path) when available, list-based otherwise — symmetric with the
        # _track_org_key write path.
        cached_keys = []
        try:
            client = getattr(cache, "client", None)
            if client is not None and hasattr(client, "smembers"):
                members = client.smembers(pattern_key) or set()
                cached_keys = [
                    m.decode() if isinstance(m, bytes) else m for m in members
                ]
        except Exception:
            cached_keys = []
        if not cached_keys:
            cached_keys = cache.get(pattern_key) or []

        invalidated = 0
        for key in cached_keys:
            if cache.delete(key):
                invalidated += 1

        cache.delete(pattern_key)
        cache.delete(f"{cls.CACHE_PREFIX}:stats:{organization_id}:hits")
        cache.delete(f"{cls.CACHE_PREFIX}:stats:{organization_id}:misses")

        logger.info(
            f"AI insights cache invalidated for org {organization_id}, "
            f"{invalidated} entries cleared"
        )
        return invalidated

    @classmethod
    def _increment_stat(
        cls, organization_id: int, stat_name: str, delta: int = 1
    ) -> None:
        """
        Atomically increment a cache statistics counter.

        Uses cache.add + cache.incr to avoid the lost-update race that the
        prior cache.get -> cache.set pattern exhibited under concurrent AI
        requests (two readers see N, both write N+1, real value should be
        N+2). cache.add only sets the key if it does not exist, and
        cache.incr is atomic in Django's redis and locmem backends.

        ValueError is raised by cache.incr when the key has expired between
        the add() and incr() calls. That race is extremely rare (sub-ms
        window vs. 24-hour TTL) and the count is best-effort, so we drop
        the increment rather than reseed.
        """
        stat_key = f"{cls.CACHE_PREFIX}:stats:{organization_id}:{stat_name}"
        try:
            if not cache.add(stat_key, delta, cls.STATS_TTL):
                try:
                    cache.incr(stat_key, delta)
                except ValueError:
                    pass
        except Exception:
            pass  # Stats are best-effort

    @classmethod
    def get_cache_stats(cls, organization_id: int) -> dict:
        """
        Get cache statistics for monitoring.

        Args:
            organization_id: Organization's primary key

        Returns:
            Dict with hits, misses, and hit_rate
        """
        hits = cache.get(f"{cls.CACHE_PREFIX}:stats:{organization_id}:hits") or 0
        misses = cache.get(f"{cls.CACHE_PREFIX}:stats:{organization_id}:misses") or 0
        total = hits + misses

        return {
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / total * 100, 1) if total > 0 else 0,
            "total_requests": total,
        }

    @classmethod
    def warm_cache(
        cls, organization_id: int, insights: list, enhancement: dict
    ) -> None:
        """
        Pre-warm cache with enhancement data.

        Useful for background processing or scheduled tasks.

        Args:
            organization_id: Organization's primary key
            insights: List of base insights
            enhancement: AI enhancement to cache
        """
        cls.cache_enhancement(organization_id, insights, enhancement)
        logger.info(f"Cache warmed for org {organization_id}")
