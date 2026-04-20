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

    @classmethod
    def _get_ttl(cls) -> int:
        """Get cache TTL from settings or use default."""
        return getattr(settings, 'AI_INSIGHTS_CACHE_TTL', cls.DEFAULT_TTL)

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
            for i in sorted(insights, key=lambda x: x['id'])
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
        cls,
        organization_id: int,
        insights: list
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
        cls,
        organization_id: int,
        insights: list,
        enhancement: dict,
        ttl: int = None
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
        """Track cache keys by organization for invalidation."""
        pattern_key = cls._get_org_pattern_key(organization_id)
        existing_keys = cache.get(pattern_key) or []

        if cache_key not in existing_keys:
            existing_keys.append(cache_key)
            cache.set(pattern_key, existing_keys, cls._get_ttl() * 2)

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
    def _increment_stat(cls, organization_id: int, stat_name: str) -> None:
        """Increment cache statistics counter."""
        stat_key = f"{cls.CACHE_PREFIX}:stats:{organization_id}:{stat_name}"
        try:
            current = cache.get(stat_key) or 0
            cache.set(stat_key, current + 1, 86400)  # 24 hour TTL for stats
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
            "total_requests": total
        }

    @classmethod
    def warm_cache(
        cls,
        organization_id: int,
        insights: list,
        enhancement: dict
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
